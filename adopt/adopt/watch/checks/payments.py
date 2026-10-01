"""Payments on Fly, read-only: who the pay forms hold, who is stuck in
RESPONDING, and whether bails moved everyone they matched. Paying and bailing
belong in Fly's payment sub-bot; the providers are the `providers` check.
See README.md."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping, Optional

from .. import io
from ..core import Finding, need, settings, utc

M = Mapping[str, Any]
NAME = "payments"
DEFAULTS = {"held_minutes": 30, "responding_minutes": 10, "window_hours": 6, "bail_prefix": ""}
BAIL_LIMIT = 500


def states(survey_name: str, state: str, field: str) -> List[dict]:
    body = io.fly_get("surveys", survey_name, "states", params={"state": state, "limit": 10000})
    if int(body["total"]) != len(body["states"]):
        raise RuntimeError(f"{survey_name} {state}: got {len(body['states'])} "
                           f"of {body['total']} states")
    return [{k: r[k] for k in ("userid", "current_form", field)} for r in body["states"]]


def held_on_pay_form(cfg: M, waiting: Iterable[dict]) -> List[dict]:
    pay = {f for c in need(cfg, "countries").values() for f in c["pay"]}
    return [r for r in waiting if r["current_form"] in pay]


def _bail_events(since: datetime) -> List[dict]:
    body = io.fly_get("bails", "events", params={"since": since.isoformat(), "limit": BAIL_LIMIT})
    if body["truncated"]:
        raise RuntimeError(f"Over {BAIL_LIMIT} bail events since {since}: some are unread")
    return body["items"]


def collect(cfg: M) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    now = datetime.now(timezone.utc)
    waiting, responding = [], []
    for c in need(cfg, "countries").values():
        waiting += states(c["survey_name"], "WAIT_EXTERNAL_EVENT", "form_start_time")
        responding += states(c["survey_name"], "RESPONDING", "updated")
    return {"waiting": waiting, "responding": responding,
            "bail_events": _bail_events(now - timedelta(hours=s["window_hours"]))}


def gap(name: str, what: str, last: Optional[datetime], window_from: datetime) -> List[Finding]:
    """The stretch between the last good read and this window, which no read saw."""
    if not last or last >= window_from:
        return []
    return [Finding(name, "unknown", f"{name}:gap", f"{what} between {last:%d %b %H:%M} and "
                    f"{window_from:%d %b %H:%M} UTC were not read")]


def stale(name: str, rows: List[dict], field: str, minutes: float, now: datetime,
          what: str, why: str) -> Finding:
    """`rows` whose `field` time is over `minutes` before `now`, oldest first."""
    rows = sorted((r for r in rows if utc(r[field]) < now - timedelta(minutes=minutes)),
                  key=lambda r: utc(r[field]))
    tail = f", oldest since {rows[0][field]}; {why}" if rows else ""
    return Finding(NAME, "decision" if rows else "ok", f"{NAME}:{name}",
                   f"{len(rows)} {what} over {minutes} min{tail}", {name: rows})


def bails(events: Iterable[dict], prefix: str, last: Optional[datetime]) -> List[Finding]:
    """The study's bail runs since the last read that did not bail all they matched."""
    events = [e for e in events if (e["bail_name"] or "").startswith(prefix)
              and (last is None or utc(e["timestamp"]) > last)]
    bad = [Finding(NAME, "decision", f"{NAME}:bail:{e['bail_name']}",
                   f"Bail {e['bail_name']} matched {e['users_matched']}, bailed "
                   f"{e['users_bailed']}" + (f", error {e['error']}" if e["error"] else ""), e)
           for e in events if e["users_matched"] != e["users_bailed"] or e["error"]]
    return bad or [Finding(NAME, "ok", f"{NAME}:bails", f"{len(events)} bail run(s) since "
                           "the last read, each bailed all it matched")]


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s = settings(cfg, NAME, DEFAULTS)
    now = utc(snapshot["read_at"])
    last = utc(history[0]["read_at"]) if history else None
    held = held_on_pay_form(cfg, snapshot["waiting"])
    out = [stale("held", held, "form_start_time", s["held_minutes"], now,
                 "held on a pay form", "the sweep should pay them"),
           stale("responding", snapshot["responding"], "updated", s["responding_minutes"], now,
                 "stuck in RESPONDING", "replybot drops their replies")]
    out += gap(NAME, "Bail events", last, now - timedelta(hours=s["window_hours"]))
    out += bails(snapshot["bail_events"], s["bail_prefix"], last)
    return out
