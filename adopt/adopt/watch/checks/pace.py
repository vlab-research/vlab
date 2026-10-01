"""Recruitment pace: completes per part against its target, the recruitment
conf's `end_date` and the date promised to the client. See README.md."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List, Mapping, Optional

from .. import io
from ..core import LEVELS, Finding, need, parts, settings, utc

M = Mapping[str, Any]
NAME = "pace"
DEFAULTS = {"window_hours": 24, "near_target_days": 1.0, "closing_hours": 24}


def per_part(cfg: M, name: str, key: str, required: bool = False) -> Any:
    """The part's own `key`, else the pace section's."""
    value = parts(cfg)[name].get(key, settings(cfg, NAME, DEFAULTS).get(key))
    if required and value is None:
        raise KeyError(f"watch.yaml has no {key} for part {name!r} (on the part or in pace)")
    return value


def _iso(t: Optional[datetime]) -> Optional[str]:
    return t.isoformat() if t else None


def completes(rows: List[M], ref: str, since: Optional[datetime]) -> List[str]:
    """Times of the `ref` rows of vlab's current data at or after `since`,
    sorted. Current data holds one row per user per variable."""
    return sorted(r["timestamp"] for r in rows
                  if r["variable"] == ref and (since is None or utc(r["timestamp"]) >= since))


def part_completes(cfg: M, name: str, vlab: Any) -> List[str]:
    """One part's completes: its `completion_ref` rows from `count_from`."""
    rows = vlab.current_data(need(cfg, "vlab.org"), parts(cfg)[name]["vlab_slug"])
    return completes(rows, need(cfg, f"{NAME}.completion_ref"),
                     utc(per_part(cfg, name, "count_from")))


def collect(cfg: M) -> dict:
    org, vlab = need(cfg, "vlab.org"), io.vlab_client()
    out = {}
    for name, p in parts(cfg).items():
        rec = vlab.get_confs(org, p["vlab_slug"]).get("recruitment") or {}
        out[name] = {"completes": part_completes(cfg, name, vlab),
                     "target": per_part(cfg, name, "target", required=True),
                     "start_date": rec.get("start_date"), "end_date": rec.get("end_date"),
                     "client_date": per_part(cfg, name, "client_date")}
    return {"parts": out}


def _day(t: datetime) -> str:
    return t.strftime("%d %b %H:%M UTC")


def assess(name: str, c: M, now: datetime, s: M) -> Finding:
    """One finding per part, at the level of its most pressing reason, so a
    part behind on several dates is one decision naming them all."""
    hours, target = s["window_hours"], c["target"]
    times = [utc(t) for t in c["completes"]]
    recent = sum(t > now - timedelta(hours=hours) for t in times)
    remaining = target - len(times)
    per_day = recent * 24 / hours
    start = utc(c["start_date"])
    end, client = (utc(c[k], end_of_day=True) for k in ("end_date", "client_date"))
    key = f"{NAME}:{name}"
    if end is None:
        return Finding(NAME, "unknown", key, f"{name}: the recruitment conf has no end_date",
                       {**c, "reasons": ["no-end-date"]})
    projected = now + timedelta(days=remaining / per_day) if per_day and remaining > 0 else None
    ev = {"total": len(times), "last_window": recent, "window_hours": hours, "target": target,
          "remaining": remaining, "per_day": round(per_day, 1),
          "projected_finish": _iso(projected), "end_date": _iso(end),
          "client_date": _iso(client)}
    reasons: List[tuple] = []  # (level, names, text)
    add = lambda level, reason, text: reasons.append((level, [reason], text))
    if remaining <= 0:
        add("decision", "target-reached", "target reached; stop recruiting")
    else:
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
        missed = [(n, when) for n, when in (("end-date", end), ("client-date", client))
                  if projected and when and projected > when]
        if missed:
            dates = " and ".join(f"the {n.replace('-', ' ')} {_day(w)}" for n, w in missed)
            reasons.append(("decision", [f"behind-{n}" for n, _ in missed],
                            f"at {per_day:.0f}/day finishes {_day(projected)}, after {dates}"))
    if not reasons:
        add("ok", "on-track", f"finishes {_day(projected)}" if projected else "not recruiting")
    level = max((r[0] for r in reasons), key=LEVELS.index)
    head = f"{name}: {len(times)}/{target}, {recent} in the last {hours} h"
    return Finding(NAME, level, key, f"{head}: " + "; ".join(r[2] for r in reasons),
                   {**ev, "reasons": [n for r in reasons for n in r[1]]})


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s, now = settings(cfg, NAME, DEFAULTS), utc(snapshot["read_at"])
    if s["window_hours"] < 24:
        raise ValueError(f"pace.window_hours is {s['window_hours']}; it must be at least 24")
    return [assess(name, c, now, s) for name, c in snapshot["parts"].items()]
