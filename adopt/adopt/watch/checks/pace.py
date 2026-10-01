"""Recruitment pace: completes per country against target, `end_date` and the
date promised to the client.

A complete is a distinct user answering the completion question
(`pace.completion_ref`) on a questionnaire form (the country's
`questionnaire` shortcodes), counting only form versions created at or after
`pace.count_from` when it is set (what the client counts). Counted from Fly's
response stream, not vlab's `strata_progress`, which only a plan run refreshes.
The snapshot keeps each complete's time and no user ids.

Pace is completes in the last `window_hours` (at least 24: nothing arrives at
night local time, so a shorter window extrapolates from silence or a burst).
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .. import io
from ..core import Finding, need

NAME = "pace"
DEFAULTS = {"window_hours": 24, "near_target_days": 1.0, "closing_hours": 24}
PAGE = 5000


def _utc(value: Any) -> Optional[datetime]:
    """A datetime in UTC from an ISO string, datetime or date (a date means
    the end of that day, UTC). Naive values are UTC, as in vlab's confs."""
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc) + timedelta(days=1)
    if isinstance(value, str):
        if len(value) == 10:
            return _utc(date.fromisoformat(value))
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def settings(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    s = {**DEFAULTS, **(cfg.get(NAME) or {})}
    if s["window_hours"] < 24:
        raise ValueError(f"pace.window_hours is {s['window_hours']}; it must be at least 24")
    return s


def _country(s: Mapping[str, Any], country: str, key: str) -> Any:
    """The per-country override in `pace.countries.<country>`, else `pace.<key>`."""
    return ((s.get("countries") or {}).get(country) or {}).get(key, s.get(key))


# ---- collect ---------------------------------------------------------------

def _responses_since(survey_name: str, since: Optional[datetime]) -> Iterable[dict]:
    """Every response of the survey from `since` on, oldest first.

    Fly's `/responses` has no time filter, only a cursor, and a study's whole
    history is far more than a run needs. The cursor is base64 of
    "timestamp,userid,question_ref" (dashboard-server
    queries/responses/token.js), so one built at `since` starts the stream
    there. Swap for a `since` parameter, or a completes count, once Fly has one.
    """
    after = None
    if since:
        stamp = since.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
        after = base64.b64encode(f"{stamp},,".encode()).decode()
    while True:
        params = {"survey": survey_name, "pageSize": PAGE}
        if after:
            params["after"] = after
        page = io.fly_get("responses", params)["responses"]
        yield from page
        if len(page) < PAGE:
            return
        after = page[-1]["token"]


def _counted_forms(surveys: List[dict], survey_name: str, shortcodes: List[str],
                   count_from: Optional[datetime]) -> List[str]:
    ids = [s["id"] for s in surveys
           if s["survey_name"] == survey_name and s["shortcode"] in shortcodes
           and (count_from is None or _utc(s["created"]) >= count_from)]
    if not ids:
        raise RuntimeError(f"No form versions of {shortcodes} in {survey_name!r} "
                           f"created from {_iso(count_from)}")
    return ids


def first_completes(responses: Iterable[dict], ref: str, form_ids: Iterable[str]) -> List[str]:
    """Each user's first answer to `ref` on a counted form, as sorted ISO times."""
    form_ids = set(form_ids)
    first: Dict[str, str] = {}
    for r in responses:
        if r["question_ref"] == ref and r["surveyid"] in form_ids:
            first.setdefault(r["userid"], r["timestamp"])
    return sorted(first.values())


def collect(cfg: Mapping[str, Any]) -> dict:
    s = settings(cfg)
    ref = need(cfg, f"{NAME}.completion_ref")
    org = need(cfg, "vlab.org")
    vlab = io.vlab_client()
    surveys = io.fly_get("surveys")
    out = {}
    for country, c in need(cfg, "countries").items():
        count_from = _utc(_country(s, country, "count_from"))
        target = _country(s, country, "target")
        if not target:
            raise KeyError(f"watch.yaml has no pace.target for {country}")
        forms = _counted_forms(surveys, c["survey_name"], list(c["questionnaire"]), count_from)
        completes = first_completes(_responses_since(c["survey_name"], count_from), ref, forms)
        rec = vlab.get_confs(org, c["vlab_slug"]).get("recruitment") or {}
        out[country] = {
            "completes": completes,
            "target": target,
            "start_date": _iso(_utc(rec.get("start_date"))),
            "end_date": _iso(_utc(rec.get("end_date"))),
            "client_date": _iso(_utc(_country(s, country, "client_date"))),
            "count_from": _iso(count_from),
            "counted_forms": forms,
        }
    return {"read_at": datetime.now(timezone.utc).isoformat(), "countries": out}


# ---- check (pure) ----------------------------------------------------------

def _day(t: datetime) -> str:
    return t.strftime("%d %b %H:%M UTC")


def assess(country: str, c: Mapping[str, Any], now: datetime,
           s: Mapping[str, Any]) -> List[Finding]:
    times = [_utc(t) for t in c["completes"]]
    window = timedelta(hours=s["window_hours"])
    total = len(times)
    recent = sum(t > now - window for t in times)
    target = c["target"]
    remaining = target - total
    per_day = recent / (window / timedelta(days=1))
    start, end, client = (_utc(c.get(k)) for k in ("start_date", "end_date", "client_date"))
    if end is None:
        return [Finding(NAME, "unknown", f"{NAME}:{country}:no-end-date",
                        f"{country}: the recruitment conf has no end_date", dict(c))]
    projected = now + timedelta(days=remaining / per_day) if per_day and remaining > 0 else None
    ev = {"total": total, "last_window": recent, "window_hours": s["window_hours"],
          "target": target, "remaining": remaining, "per_day": round(per_day, 1),
          "projected_finish": _iso(projected), "end_date": _iso(end),
          "client_date": _iso(client), "read_at": _iso(now)}
    head = f"{country}: {total}/{target}, {recent} in the last {s['window_hours']} h"
    key = f"{NAME}:{country}"
    recruiting = (start is None or start <= now) and now < end

    if remaining <= 0:
        return [Finding(NAME, "decision", f"{key}:target-reached",
                        f"{head}: target reached; stop the country", ev)]
    out = []
    if remaining <= per_day * s["near_target_days"]:
        out.append(Finding(NAME, "decision", f"{key}:near-target",
                           f"{head}: {remaining} to go, within {s['near_target_days']:g} day(s) at this pace", ev))
    if now >= end:
        out.append(Finding(NAME, "decision", f"{key}:window-closed",
                           f"{head}: recruitment window closed {_day(end)}, {remaining} short", ev))
    elif end - now <= timedelta(hours=s["closing_hours"]):
        out.append(Finding(NAME, "decision", f"{key}:window-closing",
                           f"{head}: recruitment window closes {_day(end)}, {remaining} to go", ev))
    if recruiting and recent == 0:
        out.append(Finding(NAME, "unknown", f"{key}:no-completes",
                           f"{head}: no completes while the window is open", ev))
    if projected and projected > end:
        out.append(Finding(NAME, "decision", f"{key}:behind-end-date",
                           f"{head}: at {per_day:.0f}/day finishes {_day(projected)}, after end_date {_day(end)}", ev))
    if projected and client and projected > client:
        out.append(Finding(NAME, "decision", f"{key}:behind-client-date",
                           f"{head}: at {per_day:.0f}/day finishes {_day(projected)}, after the client date {_day(client)}", ev))
    if not out:
        when = f"finishes {_day(projected)}" if projected else "not recruiting"
        out.append(Finding(NAME, "ok", f"{key}:on-track", f"{head}: {when}", ev))
    return out


def check(cfg: Mapping[str, Any], snapshot: Mapping[str, Any], history: List[dict]) -> List[Finding]:
    s = settings(cfg)
    now = _utc(snapshot["read_at"])
    return [f for country, c in snapshot["countries"].items()
            for f in assess(country, c, now, s)]
