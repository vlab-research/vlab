from datetime import datetime, timedelta, timezone

from . import payments

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CFG = {"parts": [{"name": "X", "vlab_slug": "x", "survey_name": "s", "pay": ["pay1"]}]}
LAST_HOUR = [{"read_at": (NOW - timedelta(hours=1)).isoformat()}]


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def held(user, minutes=60, form="pay1"):
    return {"userid": user, "current_form": form, "form_start_time": ago(minutes)}


def run(history=LAST_HOUR, **kw):
    snap = {"read_at": NOW.isoformat(), "waiting": [], "responding": [], "bail_events": [], **kw}
    return {f.key: f for f in payments.check(CFG, snap, history)}


def test_quiet_study_is_all_ok():
    assert {f.level for f in run().values()} == {"ok"}


def test_held_on_a_pay_form_or_stuck_responding_over_the_limit_oldest_first():
    waiting = [held("u1", 29), held("u2", 45), held("u3", 300), held("u4", 300, form="q")]
    f = run(waiting=waiting)["payments:held"]
    assert f.level == "decision" and [h["userid"] for h in f.evidence["held"]] == ["u3", "u2"]
    rows = [{"userid": "u1", "current_form": "q", "updated": ago(5)},
            {"userid": "u2", "current_form": "q", "updated": ago(15)}]
    f = run(responding=rows)["payments:responding"]
    assert f.level == "decision" and [r["userid"] for r in f.evidence["responding"]] == ["u2"]


def test_bail_mismatches_since_last_read_only():
    def bail(name, minutes):
        return {"bail_name": name, "timestamp": ago(minutes), "users_matched": 3,
                "users_bailed": 1, "error": None}
    f = run(bail_events=[bail("st-1", 30), bail("st-0", 120)])
    assert [k for k, v in f.items() if v.level == "decision"] == ["payments:bail:st-1"]


def test_gap_longer_than_the_window_is_unknown():
    assert run([{"read_at": ago(7 * 60)}])["payments:gap"].level == "unknown"
    assert "payments:gap" not in run() and "payments:gap" not in run([])


def test_bail_events_read_only_bails_into_the_studys_forms_run_in_the_window(monkeypatch):
    def item(bid, name, minutes, form="end"):
        return {"bail": {"id": bid, "name": name, "destination_form": form},
                "last_event": minutes and {"timestamp": ago(minutes)}}
    listed = {**item("b5", "list", 30, ""), "bail": {"id": "b5", "name": "list", "definition": {
        "type": "user_list", "user_list": {"users": [{"userid": "x", "shortcode": "end"}]}}}}
    bails = [item("b1", "st-a", 30), item("b2", "st-b", 600),
             item("b3", "other", 30, "elsewhere"), item("b4", "st-c", None), listed]
    surveys = [{"survey_name": "s", "shortcode": "end"},
               {"survey_name": "t", "shortcode": "elsewhere"}]
    history = [{"bail_name": "st-a", "timestamp": ago(m), "users_matched": 2, "users_bailed": 2,
                "definition_snapshot": {}, "execution_results": {"user_ids": ["p"]}}
               for m in (30, 600)]
    reads = []

    def fly_get(*path, params=None):
        reads.append(path)
        if path == ("surveys",):
            return surveys
        return {"bails": bails} if path == ("users", "u1", "bails") else {"events": history}
    monkeypatch.setattr(payments.io, "fly_post", lambda *path, body=None: {"id": "u1"})
    monkeypatch.setattr(payments.io, "fly_get", fly_get)

    events = payments._bail_events(CFG, NOW - timedelta(hours=6))
    assert reads == [("surveys",), ("users", "u1", "bails"),
                     ("users", "u1", "bails", "b1", "events"),
                     ("users", "u1", "bails", "b5", "events")]
    assert events == [{"bail_name": "st-a", "timestamp": ago(30), "users_matched": 2,
                       "users_bailed": 2, "error": None}] * 2
