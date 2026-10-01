"""A. number_health: each WhatsApp number's quality rating and sending status,
read live from Meta through Fly (GET /whatsapp/health), so no Meta token is
needed here.

A read can flicker (one UNKNOWN between two REDs), so a change counts only once
two consecutive reads agree; the second read is the next run's, from history.
Meta's note and error text is part of the reading, so a new note is confirmed
and reported the same way, verbatim in the evidence. The study's free-text
watch log is not written: the snapshots and the runner's watch.log keep every
read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from .. import io
from ..core import Finding, need

NAME = "number_health"
RATINGS = ("GREEN", "YELLOW", "RED")
CAN_SEND = ("AVAILABLE", "LIMITED")
RULES = {
    "RED": "LAC rules: no spend ramp while RED; no re-asks except to someone writing now.",
    "YELLOW": "LAC rules: no spend ramp while YELLOW.",
}
GREEN_AGAIN = "GREEN on two reads after a non-GREEN period: a held spend ramp may go ahead."


def collect(cfg: dict) -> dict:
    ids = [str(i) for i in need(cfg, "number_health.phone_number_ids")]
    read_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = io.fly_get("whatsapp/health", {"phone_number_id": ",".join(ids)})
    return {"read_at": read_at,
            "numbers": {n["phone_number_id"]: n for n in body["numbers"]}}


def notes(number: dict) -> List[str]:
    """Meta's notes and error descriptions across the number's entities, verbatim."""
    out = set()
    for entity in (number.get("health_status") or {}).get("entities") or []:
        out.update(entity.get("additional_info") or [])
        out.update(e.get("error_description") for e in entity.get("errors") or [])
    return sorted(n for n in out if n)


def reading(number: Optional[dict]) -> Optional[dict]:
    if not number or number.get("error"):
        return None
    return {"quality_rating": number.get("quality_rating"),
            "can_send_message": (number.get("health_status") or {}).get("can_send_message"),
            "notes": notes(number)}


def settled(readings: List[Optional[dict]]) -> Optional[dict]:
    """The newest reading that two consecutive reads agree on."""
    return next((a for a, b in zip(readings, readings[1:]) if a is not None and a == b), None)


def label(r: dict) -> str:
    return f"{r['quality_rating']}/{r['can_send_message']}"


def check(cfg: dict, snapshot: dict, history: List[dict]) -> List[Finding]:
    return [_number(str(pid), snapshot, history)
            for pid in need(cfg, "number_health.phone_number_ids")]


def _number(pid: str, snapshot: dict, history: List[dict]) -> Finding:
    key = f"{NAME}:{pid}"
    number = snapshot["numbers"].get(pid)
    ev = {"read_at": snapshot["read_at"], "number": number}

    def finding(level: str, summary: str) -> Finding:
        return Finding(NAME, level, key, f"{pid}: {summary}", ev)

    if number is None:
        return finding("unknown", "Fly returned no reading for this number")
    if number.get("error"):
        return finding("unknown", f"Meta read failed: {number['error']}")
    now = reading(number)
    if now["can_send_message"] not in CAN_SEND or number.get("status") != "CONNECTED":
        return finding("unknown", f"can_send_message={now['can_send_message']} "
                                  f"status={number.get('status')}: sending may be blocked")

    past = [reading(s.get("numbers", {}).get(pid)) for s in history]
    before, after = settled(past), settled([now] + past)
    ev["settled_before"] = before

    if after is None or after == before:
        if after is None:
            return finding("ok", f"read {label(now)}, not yet confirmed by a second read")
        flicker = "" if now == after else f" (this read {label(now)}, unconfirmed)"
        return finding("ok", " ".join(filter(None, [
            f"{label(after)}, unchanged{flicker}.", RULES.get(after["quality_rating"])])))

    rating = after["quality_rating"]
    if rating not in RATINGS:
        return finding("unknown", f"quality_rating {rating} on two reads, not a known rating")
    old_notes = before["notes"] if before else []
    ev["notes_added"] = [n for n in after["notes"] if n not in old_notes]
    ev["notes_removed"] = [n for n in old_notes if n not in after["notes"]]
    if before is None:
        if after["can_send_message"] == "AVAILABLE" and rating == "GREEN":
            return finding("ok", f"{label(after)}, confirmed.")
        return finding("decision", f"{label(after)}, confirmed. {RULES.get(rating, '')}".strip())
    what = (f"{label(before)} -> {label(after)}, confirmed." if label(before) != label(after)
            else f"{label(after)}, Meta's notes changed (in evidence).")
    if rating == "GREEN" and before["quality_rating"] != "GREEN":
        return finding("decision", f"{what} {GREEN_AGAIN}")
    return finding("decision", f"{what} {RULES.get(rating, '')}".strip())
