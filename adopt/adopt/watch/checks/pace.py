"""Recruitment pace: completes per country against target, the recruitment
conf's `end_date` and the date promised to the client. See README.md."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Mapping, Optional

from .. import io
from ..core import Finding, need, settings, utc

M = Mapping[str, Any]
NAME = "pace"
DEFAULTS = {"window_hours": 24, "near_target_days": 1.0, "closing_hours": 24}
PAGE = 5000


def per_country(cfg: M, country: str, key: str, required: bool = False) -> Any:
    """`pace.countries.<country>.<key>`, else `pace.<key>`."""
    s = settings(cfg, NAME, DEFAULTS)
    value = ((s.get("countries") or {}).get(country) or {}).get(key, s.get(key))
    if required and value is None:
        raise KeyError(f"watch.yaml has no pace.{key} for {country}")
    return value


def _iso(t: Optional[datetime]) -> Optional[str]:
    return t.isoformat() if t else None


def _responses(survey: str, ref: str, since: Optional[datetime]) -> Iterator[dict]:
    params = {"survey": survey, "question_ref": ref, "pageSize": PAGE, "since": _iso(since)}
    # Paged to an empty page, not a short one, so a server cap on pageSize
    # cannot end the read early.
    while page := io.fly_get("responses", params=params)["responses"]:
        yield from page
        params = {**params, "after": page[-1]["token"]}


def completes(cfg: M, country: str) -> List[str]:
    """Each user's first answer to `pace.completion_ref` on a questionnaire
    version created from `count_from` on, as sorted ISO times."""
    ref = need(cfg, f"{NAME}.completion_ref")
    c = need(cfg, f"countries.{country}")
    since = utc(per_country(cfg, country, "count_from"))
    forms = {v["id"] for v in io.fly_get("surveys")
             if v["survey_name"] == c["survey_name"] and v["shortcode"] in c["questionnaire"]
             and (since is None or utc(v["created"]) >= since)}
    if not forms:
        raise RuntimeError(f"No versions of {c['questionnaire']} in {c['survey_name']!r} "
                           f"created from {_iso(since)}")
    first: Dict[str, str] = {}
    for r in _responses(c["survey_name"], ref, since):
        if r["question_ref"] == ref and r["surveyid"] in forms:
            first.setdefault(r["userid"], r["timestamp"])
    return sorted(first.values())


def collect(cfg: M) -> dict:
    org = need(cfg, "vlab.org")
    vlab = io.vlab_client()
    out = {}
    for country, c in need(cfg, "countries").items():
        rec = vlab.get_confs(org, c["vlab_slug"]).get("recruitment") or {}
        out[country] = {"completes": completes(cfg, country),
                        "target": per_country(cfg, country, "target", required=True),
                        "start_date": rec.get("start_date"), "end_date": rec.get("end_date"),
                        "client_date": per_country(cfg, country, "client_date")}
    return {"countries": out}


def _day(t: datetime) -> str:
    return t.strftime("%d %b %H:%M UTC")


def assess(country: str, c: M, now: datetime, s: M) -> List[Finding]:
    hours, target = s["window_hours"], c["target"]
    times = [utc(t) for t in c["completes"]]
    recent = sum(t > now - timedelta(hours=hours) for t in times)
    remaining = target - len(times)
    per_day = recent * 24 / hours
    start = utc(c["start_date"])
    end, client = (utc(c[k], end_of_day=True) for k in ("end_date", "client_date"))
    key = f"{NAME}:{country}"
    if end is None:
        return [Finding(NAME, "unknown", f"{key}:no-end-date",
                        f"{country}: the recruitment conf has no end_date", dict(c))]
    projected = now + timedelta(days=remaining / per_day) if per_day and remaining > 0 else None
    ev = {"total": len(times), "last_window": recent, "window_hours": hours, "target": target,
          "remaining": remaining, "per_day": round(per_day, 1),
          "projected_finish": _iso(projected), "end_date": _iso(end),
          "client_date": _iso(client)}
    head = f"{country}: {len(times)}/{target}, {recent} in the last {hours} h"
    out: List[Finding] = []
    add = lambda level, name, text: out.append(
        Finding(NAME, level, f"{key}:{name}", f"{head}: {text}", ev))
    if remaining <= 0:
        add("decision", "target-reached", "target reached; stop the country")
        return out
    if remaining <= per_day * s["near_target_days"]:
        add("decision", "near-target",
            f"{remaining} to go, within {s['near_target_days']:g} day(s) at this pace")
    if now >= end:
        add("decision", "window-closed",
            f"recruitment window closed {_day(end)}, {remaining} short")
    elif end - now <= timedelta(hours=s["closing_hours"]):
        add("decision", "window-closing",
            f"recruitment window closes {_day(end)}, {remaining} to go")
    if (start is None or start <= now) and now < end and recent == 0:
        add("unknown", "no-completes", "no completes while the window is open")
    for name, when in (("end-date", end), ("client-date", client)):
        if projected and when and projected > when:
            add("decision", f"behind-{name}", f"at {per_day:.0f}/day finishes {_day(projected)}, "
                f"after the {name.replace('-', ' ')} {_day(when)}")
    if not out:
        add("ok", "on-track", f"finishes {_day(projected)}" if projected else "not recruiting")
    return out


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s, now = settings(cfg, NAME, DEFAULTS), utc(snapshot["read_at"])
    if s["window_hours"] < 24:
        raise ValueError(f"pace.window_hours is {s['window_hours']}; it must be at least 24")
    return [f for country, c in snapshot["countries"].items()
            for f in assess(country, c, now, s)]
