from datetime import datetime, timedelta, timezone

import pytest

from . import payments

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CFG = {"payments": {"known_codes": ["ProviderError", "PIN_DRIFT"], "ref_prefixes": ["st_"],
                    "pattern_min_users": 3, "runway_hours_min": 6, "rate_hours": 24,
                    "window_hours": 6}}
LAST_HOUR = [{"read_at": (NOW - timedelta(hours=1)).isoformat()}]


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def line(minutes, user, code, provider="dingconnect"):
    return (f"{ago(minutes)} 2026/09/30 11:00:00 DinersClub withholding {provider} failure for "
            f"user {user}: code={code} recovery=transient.")


def held(user, minutes=60):
    return {"userid": user, "form": "pay1", "form_start_time": ago(minutes)}


def wallet(transfers=(), balance=100.0):
    return {"balance": balance, "currency": "USD", "transfers": list(transfers)}


def run(history=LAST_HOUR, **kw):
    snap = {"read_at": NOW.isoformat(), "held": [], "responding": [], "bail_events": [],
            "dinersclub": [], "providers": {"dingconnect": wallet(), "reloadly": wallet()}, **kw}
    return {f.key: f for f in payments.check(CFG, snap, history)}


def test_quiet_study_is_all_ok():
    assert {f.level for f in run().values()} == {"ok"}


def test_held_over_and_under_the_limit():
    f = run(held=[held("u1", 29), held("u2", 45), held("u3", 300)])["payments:held"]
    assert f.level == "decision" and [h["userid"] for h in f.evidence["held"]] == ["u3", "u2"]
    assert run(held=[held("u1", 29)])["payments:held"].level == "ok"


def test_stuck_in_responding():
    rows = [{"userid": "u1", "form": "q", "updated": ago(5)},
            {"userid": "u2", "form": "q", "updated": ago(15)}]
    f = run(responding=rows)["payments:responding"]
    assert f.level == "decision" and [r["userid"] for r in f.evidence["responding"]] == ["u2"]


def test_bail_mismatch_since_last_read_only():
    bail = lambda name, m: {"bail_name": name, "timestamp": ago(m), "users_matched": 3,
                            "users_bailed": 1, "error": None}
    f = run(bail_events=[bail("st-1", 30), bail("st-0", 120)])
    assert f["payments:bail:st-1"].level == "decision" and "payments:bail:st-0" not in f


def test_gap_longer_than_the_window_is_unknown_and_first_read_is_ok():
    assert run([{"read_at": ago(7 * 60)}])["payments:gap"].level == "unknown"
    assert run([])["payments:gap"].level == "ok"
    assert "payments:gap" not in run()


def test_refusals_group_distinct_users_over_the_window():
    users = ["u1", "u2", "u3"]
    lines = [line(m, u, "PIN_DRIFT") for u, m in zip(users, (300, 200, 10))]
    many = run(held=[held(u) for u in users], dinersclub=lines)
    assert many["payments:refusal:dingconnect:PIN_DRIFT"].level == "decision"
    lines = [line(m, "u1", "ProviderError") for m in (10, 100, 300, 400)]
    one = run(held=[held("u1"), held("u2")], dinersclub=lines + [line(10, "elsewhere", "ProviderError")])
    r = one["payments:refusal:dingconnect:ProviderError"]
    assert r.level == "ok" and r.evidence["per_user"] == {"u1": 3}


def test_unknown_code_and_new_unparsed_line_are_unknown():
    lines = [line(10, "u1", "AUTH_ERROR", "reloadly"), f"{ago(10)} withholding in a new format",
             f"{ago(120)} withholding read last hour", "no timestamp withholding"]
    f = run(held=[held("u1")], dinersclub=lines)
    assert f["payments:refusal:reloadly:AUTH_ERROR"].level == "unknown"
    assert len(f["payments:refusal:unparsed"].evidence["lines"]) == 2


def test_low_runway_counts_only_successful_sends():
    sends = [{"ref": f"st_{i}", "status": "Complete", "usd": 12.0, "at": ago(60)} for i in range(20)]
    failed = [{"status": "FAILED", "usd": 50.0, "at": ago(60)}] * 20
    f = run(providers={"dingconnect": wallet(sends, 30.0), "reloadly": wallet(failed, 1.0)})
    assert f["payments:runway:dingconnect"].evidence["runway_hours"] == 3.0
    assert f["payments:runway:dingconnect"].level == "decision"
    assert f["payments:runway:reloadly"].level == "ok"


def test_ref_completed_twice():
    t = lambda ref, status="Complete": {"ref": ref, "status": status, "usd": 1.0, "at": ago(60)}
    sends = [t("st_a"), t("st_a"), t("st_b"), t("st_b", "Failed"), t("other"), t("other")]
    d = run(providers={"dingconnect": wallet(sends, 1e6)})["payments:double-completion"]
    assert d.level == "decision" and list(d.evidence["refs"]) == ["st_a"]
    assert d.evidence["extra_usd"] == 1.0


def test_collect_reads_bail_events_and_only_listed_providers(monkeypatch):
    calls = []
    def fly_get(*path, params=None):
        calls.append(path)
        if path == ("bails", "events"):
            assert params["limit"] == 500 and params["since"].endswith("+00:00")
            return {"truncated": False, "items": [{"bail_name": "st-1"}, {"bail_name": "other"}]}
        return {"total": 0, "states": []}
    def unread(since):
        raise AssertionError("reloadly is not listed")
    monkeypatch.setattr(payments.io, "fly_get", fly_get)
    monkeypatch.setattr(payments, "_dinersclub_lines", lambda *a: [])
    monkeypatch.setitem(payments.PROVIDERS, "dingconnect", (lambda since: wallet(), "Complete"))
    monkeypatch.setitem(payments.PROVIDERS, "reloadly", (unread, "SUCCESSFUL"))
    cfg = {"countries": {"X": {"survey_name": "s", "pay": ["p"]}},
           "payments": {"providers": ["dingconnect"], "bail_prefix": "st-"}}
    snap = payments.collect(cfg)
    assert list(snap["providers"]) == ["dingconnect"]
    assert snap["bail_events"] == [{"bail_name": "st-1"}] and calls.count(("bails", "events")) == 1


def test_bail_events_cut_short_raise(monkeypatch):
    for body in ({"truncated": True, "items": []}, {"truncated": False, "items": [{}] * 500}):
        monkeypatch.setattr(payments.io, "fly_get", lambda *path, params, body=body: body)
        with pytest.raises(RuntimeError, match="unread"):
            payments._bail_events(NOW)
