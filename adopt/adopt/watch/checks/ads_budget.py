"""Ad performance and budget per part, in the ad account's currency, against
vlab's `budget_per_arm` and, when configured, the proposal's lines. Meta
insights come through the vlab conf server's `GET /{org}/meta/insights`.
See README.md for the arithmetic."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional
from zoneinfo import ZoneInfo

import yaml

from .. import io
from ..core import Finding, need, parts, settings, utc
from . import pace

M = Mapping[str, Any]
NAME = "ads_budget"
CONVERSATION = "onsite_conversion.messaging_conversation_started_7d"
DEFAULTS = {
    "recent_days": 3,  # the window judged for fading creatives
    "baseline_days": 7,  # the ad set's own previous days it is judged against
    "fade_drop": 0.4,  # conversations per 1,000 impressions down this fraction
    "min_impressions": 1000,  # in each window, so a quiet ad set is not judged
    "max_frequency": 2.0,  # lifetime, ad sets still delivering
    "cost_days": 7,  # ad cost per complete over this many complete days
    "other_campaigns": [],  # name prefixes of other studies sharing the ad account
    "proposal": None,  # {path, currency, lines}; without it no line is judged
}
LINES = ("ads", "incentives")


def shape(row: M, prefixes: Mapping[str, List[str]]) -> Dict[str, Any]:
    """One Meta insights row as numbers, with conversations pulled out of
    `actions` and the part whose campaign prefix it matches (None if none)."""
    num = lambda k: float(row.get(k) or 0)
    name = row.get("campaign_name", "")
    ids = ("campaign_name", "adset_id", "adset_name", "ad_name")
    return {**{k: row[k] for k in ids if k in row},
            "part": next((c for c, ps in prefixes.items()
                             if any(name.startswith(p) for p in ps)), None),
            "date": row.get("date_start"), "spend": num("spend"),
            "impressions": int(num("impressions")), "reach": int(num("reach")),
            "frequency": num("frequency"),
            "conversations": int(sum(float(a.get("value") or 0) for a in row.get("actions") or []
                                     if a.get("action_type") == CONVERSATION))}


def proposal_lines(proposal: M, lines: Mapping[str, str]) -> Dict[str, float]:
    """The proposal's totals for the `ads` and/or `incentives` lines, named by
    their `budget_line_items` description."""
    items = {i["description"]: float(i["total_price"]) for i in proposal["budget_line_items"]}
    if not lines or not set(lines) <= set(LINES) or not set(lines.values()) <= set(items):
        raise KeyError(f"{NAME}.proposal.lines must map ads and/or incentives to budget lines "
                       f"in {list(items)}, not {dict(lines or {})}")
    return {name: items[desc] for name, desc in lines.items()}


def _paid(part: M) -> int:
    """Respondents whose current form is a pay form or one reached after paying."""
    paid = {*part["pay"], *part["after_pay"]}
    if not paid:
        return 0
    summary = io.fly_get("surveys", part["survey_name"], "states", "summary")
    return sum(r["count"] for r in summary["summary"] if r["current_form"] in paid)


def collect(cfg: M) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    org, mine, client = need(cfg, "vlab.org"), parts(cfg), io.vlab_client()
    proposal = None
    if s["proposal"]:
        path = cfg["study_dir"] / need(cfg, f"{NAME}.proposal.path")
        proposal = {"path": str(path), "currency": need(cfg, f"{NAME}.proposal.currency"),
                    "lines": proposal_lines(yaml.safe_load(path.read_text()),
                                            need(cfg, f"{NAME}.proposal.lines"))}
    confs = {c: client.get_confs(org, p["vlab_slug"]) for c, p in mine.items()}
    # A part without `campaigns` matches the campaigns vlab names for it.
    prefixes = {c: p["campaigns"] or [confs[c]["recruitment"]["ad_campaign_name_base"]]
                for c, p in mine.items()}
    accounts = {c: (v["general"]["ad_account"], v["general"].get("credentials_key"))
                for c, v in confs.items()}
    if len(set(accounts.values())) != 1:
        raise ValueError(f"The parts' vlab studies use different ad accounts: {accounts}")
    account, key = next(iter(accounts.values()))

    def insights(**query: Any) -> Dict[str, Any]:
        rows, after = [], None
        while True:
            body = client.meta_insights(org, account=account, credentials_key=key,
                                        limit=500, after=after, **query)
            rows += [shape(r, prefixes) for r in body["data"]]
            if not body["paging"]["truncated"]:
                return {**body, "data": rows}
            after = body["paging"]["after"]

    lifetime = insights(level="adset", date_preset="maximum")
    if not lifetime["timezone"]:
        raise RuntimeError(f"Meta returned no timezone for ad account {account}")
    today = datetime.now(ZoneInfo(lifetime["timezone"])).date()
    since = today - timedelta(days=max(s["recent_days"] + s["baseline_days"], s["cost_days"]))
    ad_days = insights(level="ad", since=since.isoformat(), until=today.isoformat(),
                       time_increment="1")
    arm_keys = ("budget_per_arm", "destinations", "incentive_per_respondent")
    return {
        "account": lifetime["account_id"], "timezone": lifetime["timezone"],
        "currency": lifetime["currency"], "today": today.isoformat(),
        "adsets": lifetime["data"], "ad_days": ad_days["data"],
        "parts": {c: {
            "completes": pace.part_completes(cfg, c, client),
            "target": pace.per_part(cfg, c, "target", required=True),
            "paid": _paid(p),
            "arm": {**{k: confs[c]["recruitment"].get(k) for k in arm_keys},
                    "vlab_spent": sum(v["total_cost"] for v in client.recruitment_stats(
                        org, p["vlab_slug"]).values())},
        } for c, p in mine.items()},
        "proposal": proposal,
    }


def _days(snap: M, skip: int, n: int) -> List[str]:
    """`n` days ending `skip` days before the snapshot's today, oldest first."""
    today = date.fromisoformat(snap["today"])
    return [(today - timedelta(days=skip + i)).isoformat() for i in range(n)][::-1]


def _sum(rows: Iterable[M], days: Iterable[str]) -> Dict[str, float]:
    picked = [r for r in rows if r["date"] in set(days)]
    return {k: round(sum(r[k] for r in picked), 2)
            for k in ("spend", "impressions", "conversations")}


def _rate(t: M) -> Optional[float]:
    return round(1000 * t["conversations"] / t["impressions"], 2) if t["impressions"] else None


def _group(rows: Iterable[M], key: str, mine: bool = True) -> Dict[str, List[M]]:
    """The rows of the study's own campaigns (`mine=False`: the others), by `key`."""
    out: Dict[str, List[M]] = defaultdict(list)
    for r in rows:
        if bool(r["part"]) == mine:
            out[r[key]].append(r)
    return out


def project(name: str, c: M, snap: M, s: M, incentive: float) -> Dict[str, Any]:
    """The budget arithmetic for one part, every input in the result."""
    cost_days = _days(snap, 1, s["cost_days"])
    # Dated in the ad account's timezone, as Meta's days are.
    zone = ZoneInfo(snap["timezone"])
    days = [utc(t).astimezone(zone).date().isoformat() for t in c["completes"]]
    recent = sum(d in cost_days for d in days)
    spend = _sum([r for r in snap["ad_days"] if r["part"] == name], cost_days)["spend"]
    cpc = spend / recent if recent else None
    remaining = max(0, c["target"] - len(c["completes"]))
    ads = round(sum(a["spend"] for a in snap["adsets"] if a["part"] == name), 2)
    out = {"completes": len(c["completes"]), "target": c["target"], "remaining": remaining,
           "paid": c["paid"], "ads_spent": ads,
           "incentives_spent_est": round(c["paid"] * incentive, 2), "incentive": incentive,
           "ad_cost_per_complete": cpc and round(cpc, 2),
           "ad_cost_days": f"{cost_days[0]}..{cost_days[-1]}"}
    if cpc is None and remaining:
        return out
    arm, cpc = c["arm"], cpc or 0.0
    missing = [k for k in ("budget_per_arm", "incentive_per_respondent") if arm.get(k) is None]
    priced = {} if missing else {
        "budget": arm["budget_per_arm"] * len(arm.get("destinations") or [1]),
        "needs": round(remaining * (cpc + float(arm["incentive_per_respondent"])), 2)}
    return {**out, "projected_ads": round(ads + remaining * cpc, 2),
            "projected_incentives": round(out["incentives_spent_est"] + remaining * incentive, 2),
            "arm": {"spent": round(arm["vlab_spent"], 2), "missing": missing, **priced}}


def budget_findings(cfg: M, snap: M, s: M) -> List[Finding]:
    proposal, cur = snap["proposal"], snap["currency"]
    money = lambda x: f"{x:,.0f} {cur}"
    rates = {c: parts(cfg)[c].get("incentive", v["arm"].get("incentive_per_respondent"))
             for c, v in snap["parts"].items()}
    if proposal and "incentives" in proposal["lines"] and None in rates.values():
        raise KeyError(f"no incentive (watch.yaml or vlab) for the proposal's incentives line: "
                       f"{[c for c, r in rates.items() if r is None]}")
    proj = {c: project(c, v, snap, s, float(rates[c] or 0)) for c, v in snap["parts"].items()}
    arms = {c: p["arm"] for c, p in proj.items() if "arm" in p}
    missing = [f"{c}: the recruitment conf has no {k}"
               for c, a in arms.items() for k in a["missing"]]
    short = [f"{c}: budget_per_arm {money(a['budget'])} is below {money(a['spent'])} spent + "
             f"{money(a['needs'])} for the remaining {proj[c]['remaining']}"
             for c, a in arms.items()
             if not a["missing"] and a["budget"] < a["spent"] + a["needs"]]
    level = "unknown" if missing else "decision" if short else "ok"
    out = [Finding(NAME, level, f"{NAME}:budget-per-arm", "; ".join(missing + short)
                   or f"budget_per_arm covers spent + the remaining in {', '.join(arms)}",
                   arms)] if arms else []
    unpriced = [c for c, p in proj.items() if "arm" not in p]
    if unpriced:
        return out + [Finding(NAME, "unknown", f"{NAME}:no-cost-per-complete",
                              f"{', '.join(unpriced)}: no completes in the last "
                              f"{s['cost_days']} days to price the remaining by", proj)]
    if not proposal:
        return out
    if proposal["currency"] != cur:
        return out + [Finding(NAME, "unknown", f"{NAME}:currency",
                              f"Ad account {snap['account']} reports in {cur}; the proposal "
                              f"is in {proposal['currency']}", {"currency": cur})]

    lines = proposal["lines"]
    projected = {k: round(sum(p[f"projected_{k}"] for p in proj.values()), 2) for k in lines}
    ev = {"projected": projected, "lines": lines, "parts": proj}
    total, budget = sum(projected.values()), sum(lines.values())
    tally = ", ".join(f"{k} {money(projected[k])}/{money(lines[k])}" for k in lines)
    over = [k for k in lines if projected[k] > lines[k]]
    if total > budget:
        return out + [Finding(NAME, "decision", f"{NAME}:over-total", f"Projected {money(total)}"
                              f" is over the proposal's {money(budget)} ({tally})", ev)]
    if over:
        return out + [Finding(NAME, "decision", f"{NAME}:over-line:{k}",
                              f"Projected {k} {money(projected[k])} is over its line "
                              f"{money(lines[k])}; the total {money(total)} fits {money(budget)}",
                              ev) for k in over]
    return out + [Finding(NAME, "ok", f"{NAME}:budget",
                          f"Projected {money(total)} of {money(budget)} ({tally})", ev)]


def over_frequency(snap: M, s: M) -> Dict[str, M]:
    """Ad sets past `max_frequency` lifetime that delivered in the last `recent_days`."""
    recent = _days(snap, 1, s["recent_days"])
    delivering = {r["adset_id"] for r in snap["ad_days"]
                  if r["date"] in recent and r["impressions"]}
    return {a["adset_id"]: {k: a[k] for k in ("campaign_name", "adset_name", "frequency", "reach")}
            for a in snap["adsets"] if a["part"] and a["adset_id"] in delivering
            and a["frequency"] > s["max_frequency"]}


def ad_findings(snap: M, s: M, history: List[dict]) -> List[Finding]:
    """Fading ad sets (conversations per 1,000 impressions in the last
    `recent_days` against the `baseline_days` before) and ad sets newly over
    `max_frequency`. Today, still accruing, is in neither window."""
    windows = {"recent": _days(snap, 1, s["recent_days"]),
               "baseline": _days(snap, 1 + s["recent_days"], s["baseline_days"])}
    rates = lambda rows: {w: _rate(_sum(rows, days)) for w, days in windows.items()}
    fading = {}
    for adset_id, rows in _group(snap["ad_days"], "adset_id").items():
        quiet = min(_sum(rows, days)["impressions"] for days in windows.values())
        rate = rates(rows)
        if (quiet >= s["min_impressions"] and rate["baseline"]
                and rate["recent"] < rate["baseline"] * (1 - s["fade_drop"])):
            fading[adset_id] = {
                "campaign_name": rows[0]["campaign_name"], "adset_name": rows[0]["adset_name"],
                **rate, "ads": {ad: rates(rs) for ad, rs in _group(rows, "ad_name").items()}}
    over = over_frequency(snap, s)
    new = [k for k in over if not any(k in over_frequency(h, s) for h in history)]
    names = lambda table, keys: "".join(
        f"; {table[k]['campaign_name']} / {table[k]['adset_name']}" for k in keys)
    return [Finding(NAME, "decision" if fading else "ok", f"{NAME}:fading",
                    f"{len(fading)} ad set(s) fading, conversations per 1,000 impressions in "
                    f"the last {s['recent_days']} days against the {s['baseline_days']} before"
                    f"{names(fading, fading)}", {"days": windows, "adsets": fading}),
            Finding(NAME, "decision" if new else "ok", f"{NAME}:frequency",
                    f"{len(new)} ad set(s) newly past lifetime frequency "
                    f"{s['max_frequency']:g} and still delivering, {len(over)} in all"
                    f"{names(over, new)}", {"new": new, "adsets": over})]


def yesterday(snap: M) -> Finding:
    """Per campaign, the last complete day in the ad account's timezone."""
    [day] = _days(snap, 1, 1)
    table = {}
    for name, rows in _group(snap["ad_days"], "campaign_name").items():
        t = _sum(rows, [day])
        if t["impressions"] or t["spend"]:
            cost = round(t["spend"] / t["conversations"], 2) if t["conversations"] else None
            table[name] = {**t, "per_1000": _rate(t), "cost_per_conversation": cost}
    spend, conv = (sum(t[k] for t in table.values()) for k in ("spend", "conversations"))
    return Finding(NAME, "ok", f"{NAME}:yesterday", f"{day} ({snap['timezone']}): {spend:,.2f} "
                   f"{snap['currency']} for {conv} conversations over {len(table)} campaigns",
                   {"day": day, "campaigns": table})


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s = settings(cfg, NAME, DEFAULTS)
    others = _group(snapshot["ad_days"], "campaign_name", mine=False)
    spent = {n: round(sum(r["spend"] for r in rs), 2) for n, rs in others.items()}
    unmatched = {n: v for n, v in spent.items()
                 if v and not n.startswith(tuple(s["other_campaigns"]))}
    out = [Finding(NAME, "unknown", f"{NAME}:unmatched-campaigns",
                   f"Campaigns matching no part's prefix spent since "
                   f"{min(r['date'] for r in snapshot['ad_days'])}: {', '.join(unmatched)}",
                   {"spend": unmatched})] if unmatched else []
    return (out + budget_findings(cfg, snapshot, s) + ad_findings(snapshot, s, history)
            + [yesterday(snapshot)])
