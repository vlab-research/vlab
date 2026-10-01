"""number_health: each WhatsApp number's quality rating and sending status,
read live from Meta through Fly (GET /whatsapp/health).

A read can flicker (one UNKNOWN between two REDs), so a change, including new
note or error text from Meta, counts only once two consecutive reads agree.
"""

from __future__ import annotations

from typing import List, Optional

from .. import io
from ..core import Finding, need

NAME = "number_health"
RULES = {
    "GREEN": "",
    "YELLOW": "LAC rules: no spend ramp while YELLOW.",
    "RED": "LAC rules: no spend ramp while RED; no re-asks except to someone writing now.",
}
GREEN_AGAIN = "GREEN on two reads after a non-GREEN period: a held spend ramp may go ahead."


def collect(cfg: dict) -> dict:
    ids = ",".join(str(i) for i in need(cfg, "number_health.phone_number_ids"))
    body = io.fly_get("whatsapp/health", {"phone_number_id": ids})
    return {"numbers": {n["phone_number_id"]: n for n in body["numbers"]}}


def reading(number: Optional[dict]) -> Optional[dict]:
    """Rating, sending status and Meta's note and error text, verbatim; None if the read failed."""
    if not number or number.get("error"):
        return None
    health = number.get("health_status") or {}
    notes = set()
    for entity in health.get("entities") or []:
        notes.update(entity.get("additional_info") or [])
        notes.update(e.get("error_description") for e in entity.get("errors") or [])
    return {"quality_rating": number.get("quality_rating"),
            "can_send_message": health.get("can_send_message"),
            "notes": sorted(n for n in notes if n)}


def settled(readings: List[Optional[dict]]) -> Optional[dict]:
    """The newest reading that two consecutive reads agree on."""
    return next((a for a, b in zip(readings, readings[1:]) if a is not None and a == b), None)


def label(r: dict) -> str:
    return f"{r['quality_rating']}/{r['can_send_message']}"


def check(cfg: dict, snapshot: dict, history: List[dict]) -> List[Finding]:
    return [_number(str(pid), snapshot, history)
            for pid in need(cfg, "number_health.phone_number_ids")]


def _number(pid: str, snapshot: dict, history: List[dict]) -> Finding:
    number = snapshot["numbers"].get(pid)
    ev = {"read_at": snapshot["read_at"], "number": number}

    def finding(level: str, summary: str) -> Finding:
        return Finding(NAME, level, f"{NAME}:{pid}", f"{pid}: {summary}".strip(), ev)

    now = reading(number)
    if now is None:
        return finding("unknown", f"Meta read failed: {number['error']}" if number
                       else "Fly returned no reading for this number")
    if now["can_send_message"] not in ("AVAILABLE", "LIMITED") or number.get("status") != "CONNECTED":
        return finding("unknown", f"can_send_message={now['can_send_message']} "
                                  f"status={number.get('status')}: sending may be blocked")
    past = [reading(s["numbers"].get(pid)) for s in history]
    before, after = settled(past), settled([now] + past)
    ev["settled_before"] = before
    if after is None:
        return finding("ok", f"read {label(now)}, not yet confirmed by a second read")
    rule = RULES.get(after["quality_rating"])
    if rule is None:
        return finding("unknown", f"quality_rating {after['quality_rating']} is not a known rating")
    if after == before:
        flicker = "" if now == after else f" (this read {label(now)}, unconfirmed)"
        return finding("ok", f"{label(after)}, unchanged{flicker}. {rule}")
    old = before["notes"] if before else []
    ev["notes_added"] = [n for n in after["notes"] if n not in old]
    ev["notes_removed"] = [n for n in old if n not in after["notes"]]
    if before is None:
        what = f"{label(after)}, confirmed."
        if label(after) == "GREEN/AVAILABLE":
            return finding("ok", what)
    elif label(before) != label(after):
        what = f"{label(before)} -> {label(after)}, confirmed."
    else:
        what = f"{label(after)}, Meta's notes changed (in evidence)."
    if before and before["quality_rating"] != "GREEN" and after["quality_rating"] == "GREEN":
        rule = GREEN_AGAIN
    return finding("decision", f"{what} {rule}")
