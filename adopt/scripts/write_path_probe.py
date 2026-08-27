"""Leg 0 of the encoded-ref probe: does the ad_attributions WRITE half work?

    write_path_probe.py                       # the whole check, against prod
    write_path_probe.py --since 2026-08-20T22:00:38Z
    write_path_probe.py --study ecd-diagnostic --study girl-effect
    write_path_probe.py --json                # machine-readable, for a runbook

The runbook that drives this is planning/encoded-ref-probe-runbook.md §L0, and
the specification is planning/encoded-ref-probe-plan.md §3 "Leg 0".

WHY THIS EXISTS
---------------
`ad_attributions` holds **zero rows**. Not zero rows *carrying a token* -- zero
rows, full stop. That single number is consistent with two states of the world
that no other observation distinguishes:

  (a) the write path is healthy and has simply had nothing to do. Rows are
      written only on ad **creates** (malaria.record_ad_attribution returns
      early on anything that is not `("ad", "create")` with provenance), and a
      steady-state study reconciles by *update*. A quiet period therefore
      produces exactly zero rows.

  (b) `record_ad_attribution` never fires -- provenance never reaches the
      instruction, or `GraphUpdater.execute` returns no created id, or the
      insert silently no-ops.

Every later leg of the probe assumes (a). Leg 3 in particular spends a human's
afternoon and creates a real ad on a live account on the premise that a row
will appear. If the truth is (b), leg 3 fails at step 1 for a reason leg 3 is
not built to diagnose.

HOW IT DECIDES
--------------
The database cannot answer this. adopt writes no per-instruction record: the
only trace of an ad create is a `logging.info` line in a cronjob pod that
Kubernetes keeps for three runs, and `adopt_reports` stores the optimiser's
budget report, not the instruction list. So the evidence has to come from the
one place that does keep an immutable timestamp for every ad ever created --
**Meta**.

    ads on Meta with created_time >= CUTOFF        (what adopt did)
      vs
    ad_attributions rows for those ad ids          (what adopt recorded)

CUTOFF is when adopt v0.1.78 -- the first tag containing
`record_ad_attribution` -- reached production. Ads created before it are
outside the contract and prove nothing either way.

Three outcomes, and the third is the interesting one:

  ads > 0, every ad has a row     -> the write path WORKS. Leg 0 answered yes.
  ads > 0, some ad has no row     -> the write path is BROKEN. Stop; fix before
                                     leg 1. This is the finding leg 0 exists for.
  ads == 0                        -> INDETERMINATE, and say so rather than
                                     inferring health from an empty table.
                                     Leg 0 is then answered by leg 3, whose ad
                                     create is the first one in the window.

SCOPING, AND THE CONFOUND IT REMOVES
------------------------------------
Ads are enumerated **per study campaign**, not per ad account. The ad account
that runs vlab's studies is the same one `ctwa_probe.py` creates probe ads on,
and probe ads are created by hand rather than by adopt -- they carry no
provenance and *correctly* have no `ad_attributions` row. Counting them would
report a broken write path on evidence of the probe working exactly as
designed. Campaign scoping excludes them by construction: adopt only ever
creates ads inside `recruitment.ad_campaign_name`.

SAFETY
------
Read-only, end to end. Graph API GETs, one `kubectl exec` for the token, and
SELECTs against cockroach. It creates nothing and modifies nothing.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from ctwa_probe import CRDB_NS, CRDB_POD, get_api  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("write_path_probe")

# When the write path reached production.
#
# adopt v0.1.78 is the first tag whose `adopt/adopt/malaria.py` contains
# `record_ad_attribution` (v0.1.77 does not). Its prod values bump is commit
# b94aafe3 "chore(prod): adopt v0.1.78, swoosh v0.1.10 (#245)", authored
# 2026-08-20 18:00:38 -0400, and helm release `vlab` revision 136 landed at
# 2026-08-20 18:00:59 local -- i.e. the deploy followed the commit by seconds.
#
# Taking the *commit* time rather than the helm time is deliberate: it is the
# earlier of the two, so the window is inclusive rather than exclusive. An ad
# created in the twenty-one seconds between them would be attributed to the old
# code and reported as a missing row -- a false alarm is the right direction to
# fail in for a check whose whole job is to notice a missing row.
DEFAULT_CUTOFF = "2026-08-20T22:00:38+00:00"
CUTOFF_PROVENANCE = (
    "adopt v0.1.78 prod values bump b94aafe3 (2026-08-20 18:00:38 -0400); "
    "helm release vlab rev 136 at 18:00:59"
)

GRAPH_PAGE_LIMIT = 500


# --------------------------------------------------------------- the database


def _crdb(sql: str, database: str) -> str:
    """One read-only statement against production cockroach, via the pod.

    Same access path `ctwa_probe.py` uses -- `kubectl exec` rather than a
    port-forward -- so this script has exactly one prerequisite (a kubectl
    context on vprod) and cannot be run against the wrong database by an
    environment variable someone forgot about.
    """
    return subprocess.run(
        ["kubectl", "exec", "-n", CRDB_NS, CRDB_POD, "--", "./cockroach", "sql",
         "--insecure", f"--database={database}", "--format=csv", "-e", sql],
        capture_output=True, text=True, check=True,
    ).stdout


def _json_rows(select: str, database: str = "vlab") -> List[Dict[str, Any]]:
    """Run `select` and hand back its rows as dicts.

    The result comes back through `json_agg` rather than cockroach's CSV
    formatter, because one of the columns below is an access token. CSV would
    have to be split on commas by a caller that cannot tell a field separator
    from a byte inside a secret, and a token that happened to contain one would
    be silently truncated into a token that fails against Meta for no visible
    reason. JSON is parsed, not split.
    """
    sql = f"SELECT coalesce(json_agg(t), '[]'::json) FROM ({select}) t"
    out = _crdb(sql, database).strip().splitlines()
    if len(out) < 2:
        return []
    # cockroach's csv formatter quotes the JSON blob; the payload is everything
    # after the header line, rejoined in case it was wrapped.
    blob = "\n".join(out[1:]).strip()
    if blob.startswith('"') and blob.endswith('"'):
        blob = blob[1:-1].replace('""', '"')
    return json.loads(blob)


def studies_with_campaigns(cutoff: datetime) -> List[Dict[str, Any]]:
    """Every study's ad account, campaign name and Graph token.

    Three things this gets right, each because getting it wrong produces a
    confidently wrong answer rather than an error:

    **Latest conf revision only.** `study_confs` is append-only -- editing a
    study writes a new row -- so a naive select returns one row per revision
    and, worse, returns *superseded* ad accounts. Girl Effect's older revision
    names account 1302577754049269 where its current one names
    1342820622846299; enumerating both sends us hunting a campaign that has not
    existed there for weeks, and the absence reads as a finding.

    **A token per study, resolved exactly as adopt resolves it** --
    `campaign_queries.get_user_info`, joining `credentials` on
    `(user_id, credentials_key)` and taking the newest. vlab runs studies across
    a dozen ad accounts owned by different researchers, and one token reaches
    almost none of them. Sweeping with a single token reports "campaign not
    found" for every study but one, which lands on INDETERMINATE -- the verdict
    that means "nothing was created" when it would actually mean "we could not
    look".

    **Studies with no usable credential are dropped here**, not silently
    treated as having no ads: they surface in `studies_unreachable` so the
    report says how much of the estate it could actually see.
    """
    select = """
    WITH latest AS (
      SELECT study_id, conf_type, conf,
             row_number() OVER (PARTITION BY study_id, conf_type
                                ORDER BY created DESC) AS rn
        FROM study_confs
       WHERE conf_type IN ('general', 'recruitment')
    )
    SELECT s.id                            AS study_id,
           s.slug                          AS slug,
           g.conf->>'ad_account'           AS ad_account,
           r.conf->>'ad_campaign_name'     AS campaign_name,
           (ss.start_date < now() AND ss.end_date > %CUTOFF%)
                                           AS recruiting_in_window,
           (SELECT c.details->>'access_token'
              FROM credentials c
             WHERE c.user_id = s.user_id
               AND c.key = g.conf->>'credentials_key'
             ORDER BY c.created DESC
             LIMIT 1)                      AS token
      FROM studies s
      JOIN latest g ON g.study_id = s.id AND g.conf_type = 'general'     AND g.rn = 1
      JOIN latest r ON r.study_id = s.id AND r.conf_type = 'recruitment' AND r.rn = 1
      LEFT JOIN study_state ss ON ss.id = s.id
     WHERE g.conf->>'ad_account' IS NOT NULL
       AND r.conf->>'ad_campaign_name' IS NOT NULL
    """
    # `recruiting_in_window` is what turns an unreadable ad account from a hole
    # in the evidence into a fact about it. adopt only touches studies where
    # `start_date < now < end_date` (recruitment_data.get_active_studies), so a
    # study whose recruitment ended before the cutoff cannot have created an ad
    # inside the window however unreadable its account is. Without this the
    # report says "24 studies excluded" and the reader has no way to know
    # whether that is a rounding error or the whole answer.
    return _json_rows(select.replace("%CUTOFF%", f"TIMESTAMPTZ '{cutoff.isoformat()}'"))


def attribution_rows() -> Dict[str, Dict[str, Any]]:
    """Every `ad_attributions` row, keyed by ad id.

    Loaded whole rather than queried per ad. The table has zero rows today and
    is bounded by the number of ads vlab has ever created, so one read is
    cheaper than N and -- more usefully -- lets the report state the total,
    which is the number the plan quotes.
    """
    rows = _json_rows(
        "SELECT ad_id, network, study_id, ref_token, created FROM ad_attributions"
    )
    return {r["ad_id"]: r for r in rows}


# ------------------------------------------------------------------- the ads


def campaign_for(account_id: str, name: str, api: FacebookAdsApi) -> Optional[Campaign]:
    account = AdAccount(f"act_{account_id}", api=api)
    found = account.get_campaigns(
        fields=["name", "created_time"],
        params={"filtering": [{"field": "name", "operator": "EQUAL", "value": name}],
                "limit": GRAPH_PAGE_LIMIT},
    )
    for c in found:
        return c
    return None


def ads_created_since(campaign: Campaign, cutoff: datetime) -> List[Dict[str, Any]]:
    """Ads in this campaign whose `created_time` is at or after the cutoff.

    Filtered client-side. Meta's `filtering` operators on `created_time` are
    documented inconsistently across edges, and a filter that silently matched
    nothing would produce the *indeterminate* verdict -- the one outcome this
    script must never reach by accident, because it reads as "no ads were
    created" when it means "we did not look properly".
    """
    out = []
    for ad in campaign.get_ads(
        fields=["id", "name", "adset_id", "created_time", "effective_status"],
        params={"limit": GRAPH_PAGE_LIMIT},
    ):
        d = ad.export_all_data()
        created = datetime.strptime(d["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        if created >= cutoff:
            out.append({**d, "created_dt": created})
    return sorted(out, key=lambda d: d["created_dt"])


# ------------------------------------------------------------------ the check


def check(cutoff: datetime, only: Optional[List[str]]) -> Dict[str, Any]:
    studies = studies_with_campaigns(cutoff)
    if only:
        studies = [s for s in studies if s["slug"] in only or s["study_id"] in only]
        if not studies:
            raise SystemExit(f"No study matched {only!r}")

    rows = attribution_rows()
    logger.info(f"ad_attributions holds {len(rows)} row(s) in total")
    logger.info(f"scanning {len(studies)} study campaign(s)\n")

    findings: List[Dict[str, Any]] = []
    unreachable: List[Dict[str, str]] = []
    no_campaign: List[str] = []
    scanned = 0

    # One API session per distinct token, not per study: several studies share
    # a researcher's credential and re-initialising the session per study buys
    # nothing but latency.
    apis: Dict[str, FacebookAdsApi] = {}

    for s in studies:
        token = s.get("token")
        if not token:
            unreachable.append({"slug": s["slug"], "ad_account": s["ad_account"],
                                "recruiting_in_window": bool(s.get("recruiting_in_window")),
                                "error": "no credential for this study's user"})
            continue

        api = apis.get(token) or apis.setdefault(token, get_api(token))

        try:
            campaign = campaign_for(s["ad_account"], s["campaign_name"], api)
        except Exception as e:  # noqa: BLE001 -- one dead account must not stop the sweep
            unreachable.append({"slug": s["slug"], "ad_account": s["ad_account"],
                                "recruiting_in_window": bool(s.get("recruiting_in_window")),
                                "error": _meta_error(e)})
            continue

        scanned += 1

        if campaign is None:
            # Not a finding. A study whose campaign has been deleted, or which
            # never published one, cannot have created an ad in the window.
            no_campaign.append(s["slug"])
            continue

        try:
            ads = ads_created_since(campaign, cutoff)
        except Exception as e:  # noqa: BLE001
            scanned -= 1
            unreachable.append({"slug": s["slug"], "ad_account": s["ad_account"],
                                "recruiting_in_window": bool(s.get("recruiting_in_window")),
                                "error": _meta_error(e)})
            continue

        if not ads:
            continue

        logger.info(f"  {s['slug']}: {len(ads)} ad(s) created since cutoff")
        for ad in ads:
            row = rows.get(ad["id"])
            findings.append({
                "study_id": s["study_id"],
                "slug": s["slug"],
                "campaign_name": s["campaign_name"],
                "ad_id": ad["id"],
                "ad_name": ad.get("name"),
                "created_time": ad["created_time"],
                "has_row": row is not None,
                "ref_token": (row or {}).get("ref_token"),
            })

    return {
        "cutoff": cutoff.isoformat(),
        "cutoff_provenance": CUTOFF_PROVENANCE,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "studies_total": len(studies),
        "studies_scanned": scanned,
        "studies_without_campaign": len(no_campaign),
        "studies_unreachable": unreachable,
        # The only unreadable studies that weaken the verdict: adopt touches a
        # study only while it is recruiting, so one that stopped before the
        # cutoff cannot have created an ad in the window whatever we can or
        # cannot see of its ad account.
        "blind_spots_that_matter": [u for u in unreachable
                                    if u.get("recruiting_in_window")],
        "ad_attributions_total_rows": len(rows),
        "ads_created_since_cutoff": len(findings),
        "ads_with_row": sum(1 for f in findings if f["has_row"]),
        "ads_without_row": [f for f in findings if not f["has_row"]],
        "findings": findings,
    }


def _meta_error(e: Exception) -> str:
    """Meta's message on one line.

    FacebookRequestError stringifies to a twelve-line block including the full
    request path, which turns a sweep over a hundred studies into pages of
    noise that hides the one line that matters -- and the noise is why the
    first run of this script printed its verdict under a wall of stack.
    """
    body = getattr(e, "_body", None) or {}
    msg = (body.get("error") or {}).get("message") if isinstance(body, dict) else None
    return (msg or str(e).replace("\n", " "))[:160]


def verdict(result: Dict[str, Any]) -> Tuple[str, str]:
    """(verdict, what it means for the rest of the probe)."""
    n = result["ads_created_since_cutoff"]
    missing = len(result["ads_without_row"])
    blind = len(result["studies_unreachable"])
    blind_live = result["blind_spots_that_matter"]

    coverage = (
        f"{result['studies_scanned']} of {result['studies_total']} study "
        f"campaigns were readable"
    )
    if blind and not blind_live:
        # The distinction the whole `recruiting_in_window` column exists for.
        coverage += (
            f"; the {blind} unreadable ones had all finished recruiting before "
            "the cutoff, so adopt would not have touched them and coverage of "
            "the window is complete"
        )
    elif blind_live:
        coverage += (
            f"; {blind} were unreadable and {len(blind_live)} of those "
            f"({', '.join(b['slug'] for b in blind_live)}) WERE recruiting in "
            "the window -- this is a genuine hole in the evidence, not a "
            "formality"
        )

    if n == 0:
        return ("INDETERMINATE", (
            f"{coverage}. Among those, no study created an ad on Meta since "
            "adopt v0.1.78 reached production, so the write path has had "
            "nothing to do and the empty table says nothing about its health. "
            "Do NOT read this as a pass. Leg 0 is answered by leg 3 instead, "
            "whose PAUSED ad is the first create in the window -- record the "
            "ad_attributions row (or its absence) as leg 0's result at that "
            "point."
        ))

    if missing:
        return ("BROKEN", (
            f"{missing} of {n} ad(s) created since the cutoff have no "
            "ad_attributions row. record_ad_attribution is not firing, or the "
            "provenance is not reaching the create instruction. STOP: legs 1-3 "
            "all assume the write half works, and leg 3 would fail at step 1 "
            "for a reason it is not built to diagnose."
        ))

    return ("WORKS", (
        f"All {n} ad(s) created since the cutoff have an ad_attributions row. "
        "The write half fires on a real create. The zero-row state was a quiet "
        "period, not a broken path."
    ))


def render(result: Dict[str, Any]) -> None:
    print("\n=== LEG 0: does the ad_attributions write half work? ===\n")
    print(f"cutoff              {result['cutoff']}")
    print(f"                    ({result['cutoff_provenance']})")
    print(f"studies with a conf {result['studies_total']}")
    print(f"  ...actually read  {result['studies_scanned']}")
    print(f"  ...no campaign    {result['studies_without_campaign']}")
    print(f"  ...unreachable    {len(result['studies_unreachable'])}")
    print(f"ad_attributions     {result['ad_attributions_total_rows']} row(s) total")
    print(f"ads created since   {result['ads_created_since_cutoff']}")
    print(f"  ...with a row     {result['ads_with_row']}")
    print(f"  ...without a row  {len(result['ads_without_row'])}")

    if result["studies_unreachable"]:
        live = len(result["blind_spots_that_matter"])
        print(f"\n  studies we could not read ({live} of them were recruiting "
              "inside the window):")
        for u in result["studies_unreachable"]:
            flag = "RECRUITING" if u.get("recruiting_in_window") else "finished  "
            print(f"    {flag} {u['slug']:<34} act_{u['ad_account']:<18} "
                  f"{u['error'][:60]}")

    if result["findings"]:
        print("\n  ad id                 created              row?  study")
        for f in result["findings"]:
            print(f"    {f['ad_id']:<20} {f['created_time']:<20} "
                  f"{'yes' if f['has_row'] else 'NO ':<5} {f['slug']}")

    v, meaning = verdict(result)
    print(f"\nVERDICT: {v}\n")
    for line in meaning.split(". "):
        if line.strip():
            print(f"  {line.strip().rstrip('.')}.")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--since", default=DEFAULT_CUTOFF,
                   help=f"ISO cutoff; default {DEFAULT_CUTOFF} ({CUTOFF_PROVENANCE})")
    p.add_argument("--study", action="append", dest="studies", default=None,
                   help="limit to a study slug or id; repeatable")
    p.add_argument("--json", action="store_true",
                   help="emit the raw result, for pasting into a runbook")
    args = p.parse_args()

    cutoff = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    if cutoff.tzinfo is None:
        raise SystemExit("--since needs a timezone; an ambiguous cutoff silently "
                         "shifts the window by hours")

    result = check(cutoff, args.studies)
    result["verdict"], result["meaning"] = verdict(result)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        render(result)

    # Exit non-zero only on the one outcome that must stop a pipeline.
    # INDETERMINATE is a legitimate state of the world, not an error.
    raise SystemExit(1 if result["verdict"] == "BROKEN" else 0)


if __name__ == "__main__":
    main()
