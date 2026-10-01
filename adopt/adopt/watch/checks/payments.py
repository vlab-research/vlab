"""Payments on Fly, read-only: who the pay forms hold, who is stuck in
RESPONDING, and whether the study's bails (those bound for one of its surveys'
forms) moved everyone they matched. Paying and bailing belong in Fly's payment
sub-bot; the providers are the `providers` check. See README.md."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping, Optional

from .. import io
from ..core import Finding, parts, settings, utc

M = Mapping[str, Any]
NAME = "payments"
DEFAULTS = {"held_minutes": 30, "responding_minutes": 10, "window_hours": 6}
EVENT_FIELDS = ("bail_name", "timestamp", "users_matched", "users_bailed", "error")


def states(survey_name: str, state: str, field: str) -> List[dict]:
    body = io.fly_get("surveys", survey_name, "states", params={"state": state, "limit": 10000})
    if int(body["total"]) != len(body["states"]):
        raise RuntimeError(f"{survey_name} {state}: got {len(body['states'])} "
                           f"of {body['total']} states")
    return [{k: r[k] for k in ("userid", "current_form", field)} for r in body["states"]]


def pay_forms(cfg: M) -> set:
    return {f for p in parts(cfg).values() for f in p["pay"]}


def waiting_on_pay(cfg: M) -> List[dict]:
    """Respondents in WAIT_EXTERNAL_EVENT, read only if the study has pay forms."""
    if not pay_forms(cfg):
        return []
    return [r for p in parts(cfg).values()
            for r in states(p["survey_name"], "WAIT_EXTERNAL_EVENT", "form_start_time")]


def held_on_pay_form(cfg: M, waiting: Iterable[dict]) -> List[dict]:
    pay = pay_forms(cfg)
    return [r for r in waiting if r["current_form"] in pay]


def destinations(bail: M) -> set:
    """A bail's destination forms: its own, and a user list's per-user ones."""
    users = ((bail.get("definition") or {}).get("user_list") or {}).get("users") or []
    return {bail.get("destination_form"), *(u.get("shortcode") for u in users)}


def _bail_events(cfg: M, since: datetime) -> List[dict]:
    """Runs at or after `since` of the bails with a destination among the
    study's surveys' forms. The bail list carries only each bail's last run, without its
    error, so a bail run since then is read in full."""
    surveys = {p["survey_name"] for p in parts(cfg).values()}
    forms = {r["shortcode"] for r in io.fly_get("surveys") if r["survey_name"] in surveys}
    user = io.fly_post("users")["id"]  # create-or-get: the key's own vlab user
    out = []
    for b in io.fly_get("users", user, "bails")["bails"]:
        last = b.get("last_event")
        if destinations(b["bail"]) & forms and last and utc(last["timestamp"]) >= since:
            events = io.fly_get("users", user, "bails", b["bail"]["id"], "events")["events"]
            out += [{k: e.get(k) for k in EVENT_FIELDS} for e in events
                    if utc(e["timestamp"]) >= since]
    return out


def collect(cfg: M) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=s["window_hours"])
    return {"waiting": waiting_on_pay(cfg),
            "responding": [r for p in parts(cfg).values()
                           for r in states(p["survey_name"], "RESPONDING", "updated")],
            "bail_events": _bail_events(cfg, since)}


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


def bails(events: Iterable[dict], last: Optional[datetime]) -> List[Finding]:
    """The study's bail runs since the last read that did not bail all they matched."""
    events = [e for e in events if last is None or utc(e["timestamp"]) > last]
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
    out = [stale("held", held_on_pay_form(cfg, snapshot["waiting"]), "form_start_time",
                 s["held_minutes"], now, "held on a pay form", "payment has not released them")
           ] if pay_forms(cfg) else []
    out.append(stale("responding", snapshot["responding"], "updated", s["responding_minutes"],
                     now, "stuck in RESPONDING", "replybot drops their replies"))
    out += gap(NAME, "Bail events", last, now - timedelta(hours=s["window_hours"]))
    return out + bails(snapshot["bail_events"], last)
