"""Check the field contract against live Facebook ads.

    adopt-probe <study-id-or-name>            # read-only report
    adopt-probe <study-id-or-name> --update   # also rewrite DROPPED

For every field in field_contract.COMPARED_AD, this builds the creative the
study config says an ad should have — the same way `adset_instructions` does —
fetches the live ad, and classifies each leaf path:

    ok       we sent it, Facebook echoed it back unchanged
    dropped  we sent it, Facebook did not return it at all
    differs  we sent it, Facebook returned something else
    stale    declared DROPPED, but Facebook does return it now

`dropped` paths that are not declared are what cause endless rewrites, so they
are the point of this tool. `--update` writes them into field_contract.DROPPED
with today's date; review the git diff as you would any other change.

Read-only by default: it points at ads that are spending real money.
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from environs import Env

from ..malaria import hydrate_strata, load_basics
from ..marketing import (
    ADSET_HOURS,
    AdsetConf,
    adset_destination_type,
    adset_promoted_object,
    create_adset,
    create_creative,
    pair_creatives_with_destinations,
)
from ..study_conf import StudyConf
from . import field_contract
from .reconciliation import _eq
from .state import FacebookState

logger = logging.getLogger(__name__)

OK = "ok"
DROPPED = "dropped"
DIFFERS = "differs"

CONTRACT_PATH = Path(field_contract.__file__)
BEGIN = "# BEGIN DROPPED (managed by adopt-probe)"
END = "# END DROPPED (managed by adopt-probe)"


def _unwrap(x: Any) -> Any:
    """Facebook SDK objects and plain dicts both show up; normalise to dicts."""
    try:
        return x.export_all_data()
    except AttributeError:
        return x


def classify(
    desired: Any, source: Any, fields: List[str]
) -> List[Tuple[str, str, Any, Any]]:
    """Walk `fields` of desired vs source, returning (path, verdict, want, got).

    Mirrors how reconciliation._eq traverses, but reports every leaf instead of
    short-circuiting on the first difference — the whole point is to see all of
    them at once.
    """
    findings: List[Tuple[str, str, Any, Any]] = []

    d, s = _unwrap(desired), _unwrap(source)
    if not isinstance(d, dict) or not isinstance(s, dict):
        return findings

    for f in fields:
        if f not in d:
            continue
        if f not in s:
            findings.append((f".{f}", OK if not d[f] else DROPPED, d[f], None))
            continue
        findings.extend(_walk(d[f], s[f], f".{f}"))

    return findings


def _walk(want: Any, got: Any, path: str) -> List[Tuple[str, str, Any, Any]]:
    want, got = _unwrap(want), _unwrap(got)

    # Mirror _eq: canonicalise representations before comparing, or the probe
    # reports differences the reconciler does not act on.
    normalize = field_contract.normalizer_for(path)
    if normalize is not None:
        try:
            want, got = normalize(want), normalize(got)
        except (TypeError, ValueError):
            pass

    if isinstance(want, dict) and isinstance(got, dict):
        out: List[Tuple[str, str, Any, Any]] = []
        for k, v in want.items():
            if k not in got:
                # Mirror _eq: an empty value we asked for and Facebook elided
                # is agreement, not a drop.
                out.append((f"{path}.{k}", OK if not v else DROPPED, v, None))
                continue
            out.extend(_walk(v, got[k], f"{path}.{k}"))
        return out

    # Lists and scalars are compared by _eq itself rather than reimplemented
    # here. Its list handling is subtle — sorted for order-independence, then
    # element dicts compared on shared keys only, because Facebook reorders
    # audience refs and strips `name` from some entries. A second
    # implementation would drift from it and report differences the reconciler
    # never acts on.
    return [(path, OK if _eq(want, got, _path=path) else DIFFERS, want, got)]


def probe_study(
    study: StudyConf, state: FacebookState, strata
) -> Tuple[List[Tuple[str, str, Any, Any]], int]:
    """Classify every compared field across every live ad in the study.

    Returns the findings and how many ads were actually compared — a report
    over 3 ads and one over 300 deserve different amounts of trust.

    `strata` is passed in rather than hydrated here: hydrate_strata appends to
    the stratum's excluded_custom_audiences in place, so calling it twice in
    one process duplicates entries and invents differences that do not exist.
    """
    by_id = {s.id: s for s in strata}
    fields = list(field_contract.COMPARED_AD)

    findings: List[Tuple[str, str, Any, Any]] = []
    ads_compared = 0

    for campaign_name in study.campaign_names:
        try:
            cs = state.campaign_state(campaign_name)
            live = cs.campaign_state
        except Exception as e:
            logger.warning(f"skipping campaign {campaign_name}: {e}")
            continue

        for adset, ads in live:
            stratum = by_id.get(_unwrap(adset).get("name"))
            if stratum is None:
                continue

            pairs = pair_creatives_with_destinations(study, stratum, campaign_name)
            desired = {
                c.name: create_creative(study, stratum, c, d) for c, d in pairs
            }

            for ad in ads:
                a = _unwrap(ad)
                want = desired.get(a.get("name"))
                if want is None or "creative" not in a:
                    continue
                findings.extend(classify(want, a["creative"], fields))
                ads_compared += 1

    return findings, ads_compared


def probe_adsets(
    study: StudyConf, state: FacebookState, strata
) -> Tuple[List[Tuple[str, str, Any, Any]], int]:
    """Classify every compared field across every live adset in the study.

    Compared desired-first, the same order `update_adset` and `update_ad` both
    use, so a clean report means the reconciler really will no-op.

    The live adset's budget and status are fed back in as the desired ones.
    The optimizer moves the budget every run by design; that is an intended
    change, not drift, and leaving it in would bury the representation
    problems this is looking for.
    """
    by_id = {s.id: s for s in strata}
    fields = list(field_contract.COMPARED_ADSET)

    findings: List[Tuple[str, str, Any, Any]] = []
    adsets_compared = 0

    for campaign_name in study.campaign_names:
        try:
            cs = state.campaign_state(campaign_name)
            live_adsets = cs.campaign_state
        except Exception as e:
            logger.warning(f"skipping campaign {campaign_name}: {e}")
            continue

        for live, _ads in live_adsets:
            data = _unwrap(live)
            stratum = by_id.get(data.get("name"))
            if stratum is None:
                continue

            pairs = pair_creatives_with_destinations(study, stratum, campaign_name)

            # Shared with adset_instructions rather than reimplemented. This was
            # a second copy of the app-only branch, so the moment a third
            # destination type appeared the probe built a different adset than
            # production sends — and the probe exists precisely to report what
            # production sends.
            #
            # destination_type is derived here for the same reason. It used to
            # be read straight off the recruitment conf, which agreed with the
            # derivation for every study whose destinations imply their channel
            # and disagreed for the ones that do not — so the probe would have
            # reported drift on exactly the studies the derivation exists to
            # fix, and reported it against an adset production never sends.
            promoted_object = adset_promoted_object(pairs)
            destination_type = adset_destination_type(
                pairs, study.recruitment.destination_type
            )

            desired = create_adset(
                AdsetConf(
                    cs.campaign,
                    stratum,
                    int(data.get("daily_budget") or 0),
                    data.get("status", "ACTIVE"),
                    ADSET_HOURS,
                    study.recruitment.optimization_goal,
                    destination_type,
                    promoted_object,
                )
            )

            findings.extend(classify(desired, live, fields))
            adsets_compared += 1

    return findings, adsets_compared


def summarise(findings) -> Dict[str, Dict[str, Any]]:
    """Collapse per-ad findings into one row per path."""
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: Dict[str, Tuple[Any, Any]] = {}

    for path, verdict, want, got in findings:
        counts[path][verdict] += 1
        if verdict != OK and path not in examples:
            examples[path] = (want, got)

    rows = {}
    for path, c in counts.items():
        # A path is only "clean" if it was clean on every ad.
        verdict = OK
        if c.get(DIFFERS):
            verdict = DIFFERS
        elif c.get(DROPPED):
            verdict = DROPPED

        declared = field_contract.is_dropped(path)
        rows[path] = {
            "verdict": verdict,
            "declared_dropped": declared,
            "ads": sum(c.values()),
            "hits": c.get(verdict, 0),
            "example": examples.get(path),
        }

    # Declared drops that Facebook now echoes back are stale declarations.
    for path, row in rows.items():
        if row["declared_dropped"] and row["verdict"] != DROPPED:
            row["verdict"] = "stale"

    return rows


def render(
    rows: Dict[str, Dict[str, Any]],
    ads_compared: int = 0,
    what: str = "live ads",
    missing_label: str = "UNDECLARED DROPS — these cause a rewrite every run:",
) -> str:
    undeclared = sorted(
        p for p, r in rows.items() if r["verdict"] == DROPPED and not r["declared_dropped"]
    )
    declared = sorted(
        p for p, r in rows.items() if r["verdict"] == DROPPED and r["declared_dropped"]
    )
    differs = sorted(p for p, r in rows.items() if r["verdict"] == DIFFERS)
    stale = sorted(p for p, r in rows.items() if r["verdict"] == "stale")
    ok = sorted(p for p, r in rows.items() if r["verdict"] == OK)

    # "live adsets" -> "adsets", so adset findings are not counted in "ads".
    unit = what.split()[-1]

    out = []
    out.append(f"compared {len(rows)} field paths across {ads_compared} {what}\n")

    if undeclared:
        out.append(missing_label)
        for p in undeclared:
            out.append(f"  {p}  ({rows[p]['hits']}/{rows[p]['ads']} {unit})")
        out.append("  declare them with --update, or stop sending them\n")

    if differs:
        out.append("VALUE DIFFERS — a real change, will be rewritten once:")
        for p in differs:
            want, got = rows[p]["example"] or (None, None)
            out.append(f"  {p}\n    want={want!r}\n    got ={got!r}")
        out.append("")

    if stale:
        out.append("STALE DECLARATIONS — Facebook returns these now, undeclare them:")
        for p in stale:
            out.append(f"  {p}")
        out.append("")

    if declared:
        out.append(f"declared drops, still dropped: {len(declared)}")
        for p in declared:
            out.append(f"  {p}")
        out.append("")

    out.append(f"clean: {len(ok)} paths")

    if not undeclared and not differs and not stale:
        out.append("\ncontract matches live Facebook behaviour.")

    return "\n".join(out)


def render_dropped_block(paths: Dict[str, str]) -> str:
    """Regenerate the DROPPED literal between the markers."""
    lines = [BEGIN, "DROPPED: Dict[str, str] = {"]
    for path in sorted(paths):
        why = paths[path]
        lines.append(f'    "{path}": (')
        for chunk in _wrap(why, 74):
            lines.append(f'        "{chunk}"')
        lines.append("    ),")
    lines.append("}")
    lines.append(END)
    return "\n".join(lines)


def _wrap(text: str, width: int) -> List[str]:
    """Wrap `text` into string-literal chunks, keeping a trailing space."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur + " ")
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def update_contract(rows: Dict[str, Dict[str, Any]], today: str) -> Optional[str]:
    """Rewrite DROPPED to match what the probe just saw. Returns new file text."""
    keep = {
        p: why
        for p, why in field_contract.DROPPED.items()
        # Drop declarations Facebook has started honouring again.
        if rows.get(f".{p}", {}).get("verdict") != "stale"
    }

    for path, row in rows.items():
        if row["verdict"] == DROPPED and not row["declared_dropped"]:
            keep[path.lstrip(".")] = (
                f"Sent by adopt, absent from Facebook's response. "
                f"Confirmed live {today} by adopt-probe."
            )

    if keep == field_contract.DROPPED:
        return None

    text = CONTRACT_PATH.read_text()
    block = render_dropped_block(keep)
    new = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END), block, text, flags=re.DOTALL
    )
    return new if new != text else None


def resolve_study_id(db_conf, ident: str) -> str:
    """Accept either a study id or a study name."""
    from ..db import query  # local import: keeps module import cheap for tests

    # db.query is a generator — materialise it, or every check below is
    # truthy and the name gets passed through as if it were an id.
    rows = list(query(db_conf, "select id from studies where id::text = %s", [ident]))
    if rows:
        return ident

    rows = list(query(db_conf, "select id from studies where name = %s", [ident]))
    if not rows:
        raise SystemExit(f"no study with id or name {ident!r}")
    if len(rows) > 1:
        raise SystemExit(f"{ident!r} matches {len(rows)} studies — pass the id")
    return str(rows[0][0])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="adopt-probe", description="Check the field contract against live ads."
    )
    parser.add_argument("study", help="study id or name")
    parser.add_argument(
        "--update",
        action="store_true",
        help="rewrite field_contract.DROPPED to match what was found",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    env = Env()
    db_conf = env("PG_URL")

    study_id = resolve_study_id(db_conf, args.study)
    study, state = load_basics(study_id, db_conf, env)

    # Hydrated once and shared: hydrate_strata mutates the strata it is given.
    strata = hydrate_strata(state, study.strata, study.creatives)

    ad_findings, ads_compared = probe_study(study, state, strata)
    adset_findings, adsets_compared = probe_adsets(study, state, strata)

    if not ad_findings and not adset_findings:
        print("no live ads or adsets matched this study's config — nothing to compare")
        return 0

    ad_rows = summarise(ad_findings)
    adset_rows = summarise(adset_findings)

    if args.json:
        print(
            json.dumps(
                {
                    "ads": _jsonable(ad_rows),
                    "adsets": _jsonable(adset_rows),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("ADS")
        print(render(ad_rows, ads_compared))
        print("\nADSETS")
        print(render(adset_rows, adsets_compared, what="live adsets"))

    if args.update:
        # Both directions are now desired-first, so "missing" means the same
        # thing on each: Facebook did not echo back what we sent.
        new = update_contract({**ad_rows, **adset_rows}, date.today().isoformat())
        if new is None:
            print("\nfield_contract.DROPPED already matches — nothing written")
        else:
            CONTRACT_PATH.write_text(new)
            print(f"\nwrote {CONTRACT_PATH} — review the diff")

    def _dirty(rows):
        return any(
            r["verdict"] == DROPPED and not r["declared_dropped"] or r["verdict"] == "stale"
            for r in rows.values()
        )

    dirty = _dirty(ad_rows) or _dirty(adset_rows)
    return 1 if dirty and not args.update else 0


def _jsonable(rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {p: {k: v for k, v in r.items() if k != "example"} for p, r in rows.items()}


if __name__ == "__main__":
    sys.exit(main())
