from . import number_health as nh

PID = "111"
CFG = {"number_health": {"phone_number_ids": [int(PID)]}}
DECREASE = "Your messaging limit will decrease if your quality rating doesn't improve"


def snap(rating="GREEN", send="AVAILABLE", status="CONNECTED", info=(), error=None):
    entity = {"can_send_message": send, "additional_info": list(info),
              "errors": [{"error_code": 138024, "error_description": "SIP not enabled"}]}
    number = {"phone_number_id": PID, "quality_rating": rating, "status": status,
              "health_status": {"can_send_message": send, "entities": [entity]},
              "error": error}
    return {"read_at": "2026-09-30T12:00:00+00:00", "numbers": {PID: number}}


RED = snap("RED", "LIMITED")


def run(*reads):
    """Check the last of `reads` (oldest first) with the others as history."""
    *older, latest = reads
    [f] = nh.check(CFG, latest, list(reversed(older)))
    return f


def test_red_is_unconfirmed_then_a_decision_then_ok_while_unchanged():
    f = run(RED)
    assert (f.level, f.key) == ("ok", "number_health:111") and "not yet confirmed" in f.summary
    f = run(RED, RED)
    assert f.level == "decision"
    assert "RED/LIMITED" in f.summary and "no spend ramp" in f.summary and "re-asks" in f.summary
    f = run(RED, RED, RED)
    assert f.level == "ok" and "unchanged" in f.summary and "no spend ramp" in f.summary


def test_single_flicker_is_not_reported():
    f = run(RED, RED, snap("UNKNOWN"))
    assert f.level == "ok" and "UNKNOWN/AVAILABLE, unconfirmed" in f.summary
    assert run(RED, RED, snap("UNKNOWN"), RED).level == "ok"


def test_confirmed_change_to_yellow():
    f = run(snap(), snap(), snap("YELLOW"), snap("YELLOW"))
    assert f.level == "decision"
    assert "GREEN/AVAILABLE -> YELLOW/AVAILABLE" in f.summary and "no spend ramp" in f.summary


def test_green_twice_after_red_lets_a_held_ramp_go():
    assert run(RED, RED, snap()).level == "ok"
    f = run(RED, RED, snap(), snap())
    assert f.level == "decision" and "held spend ramp may go ahead" in f.summary


def test_new_note_text_is_confirmed_and_reported_verbatim():
    noted = snap("RED", "LIMITED", info=[DECREASE])
    assert run(RED, RED, noted).level == "ok"
    f = run(RED, RED, noted, noted)
    assert f.level == "decision" and "notes changed" in f.summary
    assert f.evidence["notes_added"] == [DECREASE] and f.evidence["notes_removed"] == []


def test_unfamiliar_or_unsendable_values_are_unknown():
    assert run(snap(), snap(), snap("PURPLE"), snap("PURPLE")).level == "unknown"
    for s in (snap("RED", "BLOCKED"), snap(status="FLAGGED"), snap(send="SOMETHING_NEW")):
        f = run(snap(), snap(), s)
        assert f.level == "unknown" and "sending may be blocked" in f.summary


def test_failed_or_missing_read_is_unknown():
    assert run(snap(error={"code": 190, "message": "Session expired"})).level == "unknown"
    assert run({"read_at": "t", "numbers": {}}).level == "unknown"
