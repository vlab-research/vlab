from . import number_health as nh

PID = "111"
CFG = {"number_health": {"phone_number_ids": [int(PID)]}}
SIP = {"error_code": 138024, "error_description": "SIP not enabled"}
DECREASE = "Your messaging limit will decrease if your quality rating doesn't improve"


def snap(rating="GREEN", send="AVAILABLE", status="CONNECTED", info=(), error=None):
    entity = {"entity_type": "PHONE_NUMBER", "id": PID, "can_send_message": send,
              "errors": [SIP], "additional_info": list(info)}
    number = {"phone_number_id": PID, "quality_rating": rating, "status": status,
              "health_status": {"can_send_message": send, "entities": [entity]},
              "error": error}
    return {"read_at": "2026-09-30T12:00:00+00:00", "numbers": {PID: number}}


def run(*reads):
    """Check the last of `reads` (oldest first) with the others as history."""
    *older, latest = reads
    [f] = nh.check(CFG, latest, list(reversed(older)))
    return f


def test_first_read_is_unconfirmed():
    f = run(snap("RED", "LIMITED"))
    assert (f.level, f.key) == ("ok", "number_health:111")
    assert "not yet confirmed" in f.summary


def test_first_confirmed_red_is_a_decision_naming_the_rules():
    f = run(snap("RED", "LIMITED"), snap("RED", "LIMITED"))
    assert f.level == "decision"
    assert "RED/LIMITED" in f.summary and "no spend ramp" in f.summary and "re-asks" in f.summary


def test_unchanged_green_and_unchanged_red_are_ok():
    assert run(snap(), snap(), snap()).level == "ok"
    f = run(*[snap("RED", "LIMITED")] * 3)
    assert f.level == "ok" and "unchanged" in f.summary and "no spend ramp" in f.summary


def test_single_flicker_is_not_reported():
    red = snap("RED", "LIMITED")
    f = run(red, red, snap("UNKNOWN", "AVAILABLE"))
    assert f.level == "ok" and "UNKNOWN/AVAILABLE, unconfirmed" in f.summary
    assert run(red, red, snap("UNKNOWN", "AVAILABLE"), red).level == "ok"


def test_confirmed_change_to_yellow():
    f = run(snap(), snap(), snap("YELLOW"), snap("YELLOW"))
    assert f.level == "decision"
    assert "GREEN/AVAILABLE -> YELLOW/AVAILABLE" in f.summary and "no spend ramp" in f.summary


def test_green_twice_after_red_lets_a_held_ramp_go():
    red = snap("RED", "LIMITED")
    assert run(red, red, snap()).level == "ok"
    f = run(red, red, snap(), snap())
    assert f.level == "decision" and "held spend ramp may go ahead" in f.summary


def test_new_note_text_is_confirmed_and_reported_verbatim():
    red = snap("RED", "LIMITED")
    noted = snap("RED", "LIMITED", info=[DECREASE])
    assert run(red, red, noted).level == "ok"
    f = run(red, red, noted, noted)
    assert f.level == "decision" and "notes changed" in f.summary
    assert f.evidence["notes_added"] == [DECREASE] and f.evidence["notes_removed"] == []


def test_unfamiliar_rating_on_two_reads_is_unknown():
    assert run(snap(), snap(), snap("PURPLE"), snap("PURPLE")).level == "unknown"


def test_cannot_send_is_unknown_at_once():
    for s in (snap("RED", "BLOCKED"), snap(status="FLAGGED"), snap(send="SOMETHING_NEW")):
        f = run(snap(), snap(), s)
        assert f.level == "unknown" and "sending may be blocked" in f.summary


def test_failed_or_missing_read_is_unknown():
    assert run(snap(error={"code": 190, "message": "Session expired"})).level == "unknown"
    assert run({"read_at": "t", "numbers": {}}).level == "unknown"


def test_collect_asks_fly_for_the_configured_numbers(monkeypatch):
    seen = {}

    def fly_get(path, params):
        seen.update(path=path, params=params)
        return {"numbers": [snap()["numbers"][PID]]}

    monkeypatch.setattr(nh.io, "fly_get", fly_get)
    out = nh.collect(CFG)
    assert seen == {"path": "whatsapp/health", "params": {"phone_number_id": PID}}
    assert set(out) == {"read_at", "numbers"} and out["numbers"][PID]["quality_rating"] == "GREEN"
