"""Ad performance and budget against the proposal (study-watch-plan.md §5, §6).

Meta is read through the vlab conf server's `GET /{org}/meta/insights`, so no
Meta token is needed here. Insights dates are the ad account's days (LAC:
Europe/Madrid) and the account's today is still accruing, so every day
comparison stops at yesterday in that timezone.

Budget, per country, in USD:
- ads spent: Meta lifetime spend (`date_preset=maximum`) on the campaigns whose
  names start with one of `ads_budget.countries.<c>.campaigns`, which catches
  arms vlab has since dropped from `destinations`;
- incentives spent: an ESTIMATE, respondents who reached a pay, end or apology
  form (Fly's states summary) times `incentive_usd`. Real provider history is
  the payments check's; this undercounts when prices were higher before;
- remaining: the `pace` check's target less its completes (its definition of a
  complete, version filter included), so the two checks agree;
- projected: spent + remaining x (ad cost per complete over the last
  `cost_days` days + `incentive_usd`).
Projections are compared with the proposal's lines (`ads_budget.lines`).
`budget_per_arm` is compared with what adopt itself counts as spent against it
(`recruitment_stats` total cost: the current arms' ad spend plus its modelled
incentives, as of the last plan run) plus what the remaining sample needs at
the study's `incentive_per_respondent`: when that is short, adopt stops
spending before the target.

Not collected: the started/completed funnel per day. Fly's API has no cheap
per-day count of consents; completes per day are in the `pace` snapshot.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

import yaml

from .. import io
from ..core import Finding, need
from . import pace

NAME = "ads_budget"
CONVERSATION = "onsite_conversion.messaging_conversation_started_7d"
DEFAULTS = {
    "recent_days": 3,  # the window judged for fading creatives
    "baseline_days": 7,  # the ad set's own previous week it is judged against
    "fade_drop": 0.4,  # conversations per 1,000 impressions down this fraction
    "min_impressions": 1000,  # in each window, so a quiet ad set is not judged
    "max_frequency": 2.0,  # lifetime, ad sets still delivering
    "cost_days": 7,  # ad cost per complete over this many complete days
    "pooled": False,  # true: only the pass-through total must fit, not each line
}


def settings(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    return {**DEFAULTS, **need(cfg, NAME)}


# ---- collect ---------------------------------------------------------------

def _num(row: Mapping[str, Any], key: str) -> float:
    return float(row.get(key) or 0)


def shape(row: Mapping[str, Any]) -> Dict[str, Any]:
    """One Meta insights row as numbers, with conversations pulled out of
    `actions`. Ids and names are kept as Meta named them."""
    out = {k: row[k] for k in ("campaign_id", "campaign_name", "adset_id", "adset_name",
                               "ad_id", "ad_name") if k in row}
    out.update(
        date=row.get("date_start"),
        spend=_num(row, "spend"),
        impressions=int(_num(row, "impressions")),
        reach=int(_num(row, "reach")),
        frequency=_num(row, "frequency"),
        ctr=_num(row, "ctr"),
        conversations=int(sum(float(a.get("value") or 0) for a in row.get("actions") or []
                              if a.get("action_type") == CONVERSATION)),
    )
    return out


def country_of(campaign_name: str, prefixes: Mapping[str, List[str]]) -> Optional[str]:
    for country, names in prefixes.items():
        if any(campaign_name.startswith(p) for p in names):
            return country
    return None


def _insights(client: Any, org: str, account: str, key: Optional[str],
              **query: Any) -> Dict[str, Any]:
    """Every page of one insights query."""
    rows: List[dict] = []
    after = None
    while True:
        body = client.meta_insights(org, account=account, credentials_key=key,
                                    limit=500, after=after, **query)
        rows += body["data"]
        if not body["paging"]["truncated"]:
            return {**body, "data": rows}
        after = body["paging"]["after"]


def _paid(survey_name: str, forms: Iterable[str]) -> int:
    """Respondents whose current form is one of `forms` (pay, end, apology)."""
    summary = io.fly_get(f"surveys/{quote(survey_name, safe='')}/states/summary")
    forms = set(forms)
    return sum(r["count"] for r in summary["summary"] if r["current_form"] in forms)


def proposal_lines(proposal: Mapping[str, Any], lines: Mapping[str, str]) -> Dict[str, float]:
    """The proposal's totals for the `ads` and `incentives` lines, named by
    their `budget_line_items` description."""
    if set(lines) != {"ads", "incentives"}:
        raise KeyError(f"{NAME}.lines must name exactly ads and incentives, not {list(lines)}")
    items = {i["description"]: float(i["total_price"]) for i in proposal["budget_line_items"]}
    missing = [d for d in lines.values() if d not in items]
    if missing:
        raise KeyError(f"Proposal has no budget line {missing}; it has {list(items)}")
    return {name: items[desc] for name, desc in lines.items()}


def collect(cfg: Mapping[str, Any]) -> dict:
    s = settings(cfg)
    org = need(cfg, "vlab.org")
    countries = need(cfg, "countries")
    mine = need(cfg, f"{NAME}.countries")
    prefixes = {c: list(need(cfg, f"{NAME}.countries.{c}.campaigns")) for c in mine}
    proposal_path = Path(need(cfg, f"{NAME}.proposal")).expanduser()
    if not proposal_path.is_absolute():
        raise ValueError(f"{NAME}.proposal must be an absolute or ~ path, not {proposal_path}")
    lines = proposal_lines(yaml.safe_load(proposal_path.read_text()), need(cfg, f"{NAME}.lines"))
    client = io.vlab_client()

    confs = {c: client.get_confs(org, countries[c]["vlab_slug"]) for c in mine}
    general = next(iter(confs.values()))["general"]
    account = s.get("ad_account") or general["ad_account"]
    key = s.get("credentials_key") or general.get("credentials_key")

    totals = _insights(client, org, account, key, level="campaign", date_preset="maximum")
    tz = totals["timezone"]
    if not tz:
        raise RuntimeError(f"Meta returned no timezone for ad account {account}")
    today = datetime.now(ZoneInfo(tz)).date()
    days = max(s["recent_days"] + s["baseline_days"], s["cost_days"])
    window = {"since": (today - timedelta(days=days)).isoformat(),
              "until": today.isoformat(), "time_increment": "1"}

    def rows(body: Mapping[str, Any]) -> List[dict]:
        out = []
        for r in map(shape, body["data"]):
            country = country_of(r["campaign_name"], prefixes)
            if country:
                out.append({**r, "country": country})
        return out

    paced = pace.collect(cfg)["countries"]
    return {
        "read_at": datetime.now(timezone.utc).isoformat(),
        "account": totals["account_id"],
        "timezone": tz,
        "currency": totals["currency"],
        "today": today.isoformat(),
        "campaign_totals": rows(totals),
        "campaign_days": rows(_insights(client, org, account, key, level="campaign", **window)),
        "ad_days": rows(_insights(client, org, account, key, level="ad", **window)),
        "adsets": rows(_insights(client, org, account, key, level="adset",
                                 date_preset="maximum")),
        "countries": {
            c: {
                "completes": [t[:10] for t in paced[c]["completes"]],
                "target": paced[c]["target"],
                "paid": _paid(countries[c]["survey_name"],
                              [*countries[c]["pay"], countries[c]["end"],
                               countries[c]["apology"]]),
                "arm": {
                    **{k: confs[c]["recruitment"].get(k) for k in (
                        "budget_per_arm", "destinations", "incentive_per_respondent")},
                    "vlab_spent": sum(v["total_cost"] for v in client.recruitment_stats(
                        org, countries[c]["vlab_slug"]).values()),
                },
            }
            for c in mine
        },
        "proposal": {"path": str(proposal_path), "lines": lines},
    }


# ---- check (pure) ----------------------------------------------------------

def per_1000(conversations: float, impressions: float) -> Optional[float]:
    return round(1000 * conversations / impressions, 2) if impressions else None


def _days_before(today: date, start: int, n: int) -> List[str]:
    """`n` days ending `start` days before `today`, oldest first."""
    return [(today - timedelta(days=start + i)).isoformat() for i in range(n)][::-1]


def _sum(rows: Iterable[Mapping[str, Any]], days: Iterable[str]) -> Dict[str, float]:
    days = set(days)
    picked = [r for r in rows if r["date"] in days]
    return {k: sum(r[k] for r in picked) for k in ("spend", "impressions", "conversations")}


def project(country: str, c: Mapping[str, Any], snap: Mapping[str, Any],
            s: Mapping[str, Any]) -> Dict[str, Any]:
    """The budget arithmetic for one country, every input in the result."""
    today = date.fromisoformat(snap["today"])
    cost_days = _days_before(today, 1, s["cost_days"])
    incentive = float(need(s, f"countries.{country}.incentive_usd"))
    mine = [r for r in snap["campaign_totals"] if r["country"] == country]
    recent = _sum([r for r in snap["campaign_days"] if r["country"] == country], cost_days)
    recent_completes = sum(d in set(cost_days) for d in c["completes"])
    ads_spent = sum(r["spend"] for r in mine)
    if recent_completes:
        ad_cpc = recent["spend"] / recent_completes
    elif c["paid"]:
        ad_cpc = ads_spent / c["paid"]
    else:
        ad_cpc = None
    remaining = max(0, c["target"] - len(c["completes"]))
    out = {
        "completes": len(c["completes"]), "target": c["target"], "remaining": remaining,
        "paid": c["paid"], "ads_spent": round(ads_spent, 2),
        "incentives_spent_est": round(c["paid"] * incentive, 2),
        "incentive_usd": incentive, "ad_cost_per_complete": ad_cpc and round(ad_cpc, 2),
        "ad_cost_basis": (f"{cost_days[0]}..{cost_days[-1]}" if recent_completes
                          else "lifetime spend / paid"),
    }
    if ad_cpc is None:
        return out
    out["projected_ads"] = round(ads_spent + remaining * ad_cpc, 2)
    out["projected_incentives"] = round(out["incentives_spent_est"] + remaining * incentive, 2)

    arm = c["arm"]
    per_resp = float(arm.get("incentive_per_respondent") or 0)
    out["arm"] = {
        "budget": (arm.get("budget_per_arm") or 0) * len(arm.get("destinations") or [1]),
        "spent": round(arm["vlab_spent"], 2),
        "needs": round(remaining * (ad_cpc + per_resp), 2),
    }
    return out


def budget_findings(snap: Mapping[str, Any], s: Mapping[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    lines = snap["proposal"]["lines"]
    proj = {c: project(c, v, snap, s) for c, v in snap["countries"].items()}

    for c, p in proj.items():
        if "projected_ads" not in p:
            out.append(Finding(NAME, "unknown", f"{NAME}:no-cost-per-complete:{c}",
                               f"{c}: no completes or paid respondents to price the "
                               f"remaining {p['remaining']} by", p))
            continue
        arm = p["arm"]
        if arm["budget"] < arm["spent"] + arm["needs"]:
            out.append(Finding(
                NAME, "decision", f"{NAME}:budget-per-arm:{c}",
                f"{c}: budget_per_arm ${arm['budget']:,.0f} is below spent "
                f"${arm['spent']:,.0f} + ${arm['needs']:,.0f} for the remaining "
                f"{p['remaining']}", p))
    if any("projected_ads" not in p for p in proj.values()):
        return out

    projected = {"ads": sum(p["projected_ads"] for p in proj.values()),
                 "incentives": sum(p["projected_incentives"] for p in proj.values())}
    evidence = {"projected": {k: round(v, 2) for k, v in projected.items()},
                "lines": lines, "countries": proj}
    total, budget = sum(projected.values()), sum(lines.values())
    over = [k for k in lines if projected.get(k, 0) > lines[k]]
    tally = ", ".join(f"{k} ${projected.get(k, 0):,.0f}/${lines[k]:,.0f}" for k in lines)
    if total > budget:
        out.append(Finding(NAME, "decision", f"{NAME}:over-total",
                           f"Projected ${total:,.0f} is over the proposal's ${budget:,.0f} "
                           f"({tally})", evidence))
    elif over and not s["pooled"]:
        out += [Finding(NAME, "decision", f"{NAME}:over-line:{k}",
                        f"Projected {k} ${projected[k]:,.0f} is over its line "
                        f"${lines[k]:,.0f}; the total ${total:,.0f} fits ${budget:,.0f}",
                        evidence) for k in over]
    else:
        out.append(Finding(NAME, "ok", f"{NAME}:budget",
                           f"Projected ${total:,.0f} of ${budget:,.0f} ({tally})", evidence))
    return out


def ad_findings(snap: Mapping[str, Any], s: Mapping[str, Any]) -> List[Finding]:
    """Fading ad sets (conversations per 1,000 impressions in the last
    `recent_days` against the `baseline_days` before) and ad sets still
    delivering past `max_frequency` lifetime. Today is never in either window."""
    today = date.fromisoformat(snap["today"])
    recent_days = _days_before(today, 1, s["recent_days"])
    base_days = _days_before(today, 1 + s["recent_days"], s["baseline_days"])
    by_adset: Dict[str, List[dict]] = defaultdict(list)
    for r in snap["ad_days"]:
        by_adset[r["adset_id"]].append(r)

    out: List[Finding] = []
    delivering = set()
    for adset_id, rows in by_adset.items():
        recent, base = _sum(rows, recent_days), _sum(rows, base_days)
        if recent["impressions"]:
            delivering.add(adset_id)
        r_rate, b_rate = _rate(recent), _rate(base)
        if (min(recent["impressions"], base["impressions"]) < s["min_impressions"]
                or not b_rate or r_rate >= b_rate * (1 - s["fade_drop"])):
            continue
        ads = defaultdict(list)
        for r in rows:
            ads[r["ad_name"]].append(r)
        name = rows[0]["adset_name"]
        out.append(Finding(
            NAME, "decision", f"{NAME}:fading:{adset_id}",
            f"{rows[0]['campaign_name']} / {name}: {r_rate} conversations per 1,000 "
            f"impressions in the last "
            f"{s['recent_days']} days against {b_rate} the {s['baseline_days']} before",
            {"adset": name, "campaign": rows[0]["campaign_name"],
             "recent": {**recent, "per_1000": r_rate, "days": recent_days},
             "baseline": {**base, "per_1000": b_rate, "days": base_days},
             "ads": {ad: {"recent": _rate(_sum(rs, recent_days)),
                          "baseline": _rate(_sum(rs, base_days))}
                     for ad, rs in ads.items()}}))

    for a in snap["adsets"]:
        if a["adset_id"] in delivering and a["frequency"] > s["max_frequency"]:
            out.append(Finding(
                NAME, "decision", f"{NAME}:frequency:{a['adset_id']}",
                f"{a['campaign_name']} / {a['adset_name']}: lifetime frequency "
                f"{a['frequency']:.2f} "
                f"(reach {a['reach']:,}), still delivering",
                {k: a[k] for k in ("adset_name", "campaign_name", "reach", "frequency",
                                   "impressions")}))
    return out


def _rate(totals: Mapping[str, float]) -> Optional[float]:
    return per_1000(totals["conversations"], totals["impressions"])


def yesterday(snap: Mapping[str, Any]) -> Finding:
    """Per campaign, the last complete day in the ad account's timezone."""
    day = (date.fromisoformat(snap["today"]) - timedelta(days=1)).isoformat()
    rows = [r for r in snap["campaign_days"] if r["date"] == day]
    table = {r["campaign_name"]: {
        "spend": r["spend"], "impressions": r["impressions"], "reach": r["reach"],
        "ctr": r["ctr"], "conversations": r["conversations"],
        "cost_per_conversation": (round(r["spend"] / r["conversations"], 2)
                                  if r["conversations"] else None),
        "per_1000": per_1000(r["conversations"], r["impressions"])} for r in rows}
    spend = sum(r["spend"] for r in rows)
    conv = sum(r["conversations"] for r in rows)
    return Finding(NAME, "ok", f"{NAME}:yesterday",
                   f"{day} ({snap['timezone']}): ${spend:,.2f} for {conv} conversations "
                   f"over {len(rows)} campaigns",
                   {"day": day, "campaigns": table})


def check(cfg: Mapping[str, Any], snapshot: Mapping[str, Any],
          history: List[dict]) -> List[Finding]:
    s = settings(cfg)
    if snapshot["currency"] != "USD":
        return [Finding(NAME, "unknown", f"{NAME}:currency",
                        f"Ad account {snapshot['account']} reports in "
                        f"{snapshot['currency']}; budgets here are USD",
                        {"currency": snapshot["currency"]})]
    return budget_findings(snapshot, s) + ad_findings(snapshot, s) + [yesterday(snapshot)]
