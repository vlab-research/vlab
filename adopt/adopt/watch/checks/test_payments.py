from datetime import datetime, timedelta, timezone

from . import payments

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CFG = {"payments": {"known_codes": ["ProviderError", "PIN_DRIFT"], "ref_prefixes": ["st_"],
                    "pattern_min_users": 3, "runway_hours_min": 6, "rate_hours": 24}}


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def line(minutes, user, code, provider="dingconnect"):
    return (f"{ago(minutes)} 2026/09/30 11:00:00 DinersClub withholding {provider} failure for "
            f"user {user}: code={code} recovery=transient. Respondent stays in WAIT_EXTERNAL_EVENT")


def snap(**kw):
    base = {"at": NOW.isoformat(), "held": [], "responding": [], "bail_events": [],
            "dinersclub": [],
            "dingconnect": {"balance": 100.0, "currency": "USD", "transfers": []},
            "reloadly": {"balance": 100.0, "currency": "USD", "transfers": []}}
    return {**base, **kw}


def by_key(findings):
    return {f.key: f for f in findings}


def held(user, minutes):
    return {"userid": user, "form": "pay1", "form_start_time": ago(minutes)}


def test_quiet_study_is_all_ok():
    assert {f.level for f in payments.check(CFG, snap(), [])} == {"ok"}


def test_held_over_30_minutes_by_form_start_time():
    f = by_key(payments.check(CFG, snap(held=[held("u1", 20), held("u2", 45), held("u3", 300)]), []))
    held_f = f["payments:held"]
    assert held_f.level == "decision"
    assert [h["userid"] for h in held_f.evidence["held"]] == ["u3", "u2"]
    assert ago(300) in held_f.summary


def test_held_under_30_minutes_is_ok():
    f = by_key(payments.check(CFG, snap(held=[held("u1", 29)]), []))
    assert f["payments:held"].level == "ok"


def test_stuck_in_responding():
    rows = [{"userid": "u1", "form": "q", "updated": ago(5)},
            {"userid": "u2", "form": "q", "updated": ago(15)}]
    f = by_key(payments.check(CFG, snap(responding=rows), []))["payments:responding"]
    assert f.level == "decision" and [r["userid"] for r in f.evidence["stuck"]] == ["u2"]


def test_bail_mismatch_since_last_read_only():
    events = [{"bail_name": "st-sweep-1", "timestamp": ago(30), "users_matched": 3,
               "users_bailed": 2, "error": None},
              {"bail_name": "st-sweep-0", "timestamp": ago(120), "users_matched": 3,
               "users_bailed": 1, "error": None}]
    f = by_key(payments.check(CFG, snap(bail_events=events), [{"at": ago(60)}]))
    assert f["payments:bail:st-sweep-1"].level == "decision"
    assert "payments:bail:st-sweep-0" not in f


def test_same_number_refused_repeatedly_is_the_line():
    lines = [line(m, "u1", "ProviderError") for m in (10, 20, 30, 40)]
    f = by_key(payments.check(CFG, snap(held=[held("u1", 60)], dinersclub=lines), []))
    r = f["payments:refusal:dingconnect:ProviderError"]
    assert r.level == "ok" and r.evidence["per_user"] == {"u1": 4}


def test_many_numbers_same_code_is_a_decision():
    users = ["u1", "u2", "u3"]
    lines = [line(10, u, "PIN_DRIFT") for u in users]
    f = by_key(payments.check(CFG, snap(held=[held(u, 60) for u in users], dinersclub=lines), []))
    assert f["payments:refusal:dingconnect:PIN_DRIFT"].level == "decision"


def test_log_lines_for_other_studies_and_before_last_read_are_dropped():
    lines = [line(10, "elsewhere", "ProviderError"), line(90, "u1", "ProviderError")]
    f = payments.check(CFG, snap(held=[held("u1", 60)], dinersclub=lines), [{"at": ago(60)}])
    assert not [x for x in f if x.key.startswith("payments:refusal")]


def test_unknown_error_code_and_unparsed_line_are_unknown():
    lines = [line(10, "u1", "AUTH_ERROR", provider="reloadly"), "withholding in a new format"]
    f = by_key(payments.check(CFG, snap(held=[held("u1", 60)], dinersclub=lines), []))
    assert f["payments:refusal:reloadly:AUTH_ERROR"].level == "unknown"
    assert f["payments:refusal:None:None"].level == "unknown"


def test_low_runway_is_a_decision():
    sends = [{"ref": f"st_{i}", "status": "Complete", "usd": 12.0, "at": ago(60)} for i in range(20)]
    f = by_key(payments.check(CFG, snap(dingconnect={"balance": 30.0, "currency": "USD",
                                                     "transfers": sends}), []))
    r = f["payments:runway:dingconnect"]
    assert r.level == "decision" and r.evidence["runway_hours"] == 3.0
    assert f["payments:runway:reloadly"].level == "ok"


def test_failed_sends_do_not_count_toward_rate():
    sends = [{"status": "FAILED", "usd": 50.0, "at": ago(60)}] * 20
    f = by_key(payments.check(CFG, snap(reloadly={"balance": 1.0, "currency": "USD",
                                                  "transfers": sends}), []))
    assert f["payments:runway:reloadly"].level == "ok"


def test_ref_completed_twice():
    t = lambda ref, status="Complete": {"ref": ref, "status": status, "usd": 1.0, "at": ago(60)}
    sends = [t("st_a_p1"), t("st_a_p1"), t("st_b_p1"), t("st_b_p1", "Failed"),
             t("other_c"), t("other_c")]
    f = by_key(payments.check(CFG, snap(dingconnect={"balance": 1e6, "currency": "USD",
                                                     "transfers": sends}), []))
    d = f["payments:double-completion"]
    assert d.level == "decision" and list(d.evidence["refs"]) == ["st_a_p1"]
    assert d.evidence["extra_usd"] == 1.0
