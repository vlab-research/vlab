from datetime import datetime, timedelta, timezone

import pytest

from . import payments

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CFG = {"countries": {"X": {"survey_name": "s", "pay": ["pay1"]}},
       "payments": {"known_codes": ["ProviderError", "PIN_DRIFT"], "ref_prefixes": ["st_"],
                    "bail_prefix": "st-"}}
LAST_HOUR = [{"read_at": (NOW - timedelta(hours=1)).isoformat()}]


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def line(minutes, user, code, provider="dingconnect"):
    return (f"{ago(minutes)} 2026/09/30 11:00:00 DinersClub withholding {provider} failure for "
            f"user {user}: code={code} recovery=transient.")


def held(user, minutes=60, form="pay1"):
    return {"userid": user, "current_form": form, "form_start_time": ago(minutes)}


def wallet(transfers=(), balance=100.0):
    return {"balance": balance, "currency": "USD", "transfers": list(transfers)}


def run(history=LAST_HOUR, **kw):
    snap = {"read_at": NOW.isoformat(), "waiting": [], "responding": [], "bail_events": [],
            "dinersclub": [], "providers": {"dingconnect": wallet(), "reloadly": wallet()}, **kw}
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


def test_the_studys_bail_mismatches_since_last_read_only():
    def bail(name, minutes):
        return {"bail_name": name, "timestamp": ago(minutes), "users_matched": 3,
                "users_bailed": 1, "error": None}
    f = run(bail_events=[bail("st-1", 30), bail("st-0", 120), bail("other", 30)])
    assert [k for k, v in f.items() if v.level == "decision"] == ["payments:bail:st-1"]


def test_gap_longer_than_the_window_is_unknown():
    assert run([{"read_at": ago(7 * 60)}])["payments:gap"].level == "unknown"
    assert "payments:gap" not in run() and "payments:gap" not in run([])


def test_refusals_group_distinct_held_users_over_the_window():
    users = ["u1", "u2", "u3"]
    lines = [line(m, u, "PIN_DRIFT") for u, m in zip(users, (300, 200, 10))]
    many = run(waiting=[held(u) for u in users], dinersclub=lines)
    assert many["payments:refusal:dingconnect:PIN_DRIFT"].level == "decision"
    lines = [line(m, "u1", "ProviderError") for m in (10, 100, 300, 400)]
    one = run(waiting=[held("u1"), held("u2")],
              dinersclub=lines + [line(10, "elsewhere", "ProviderError")])
    r = one["payments:refusal:dingconnect:ProviderError"]
    assert r.level == "ok" and r.evidence["per_user"] == {"u1": 3}


def test_unknown_code_and_new_unparsed_line_are_unknown():
    lines = [line(10, "u1", "AUTH_ERROR", "reloadly"), f"{ago(10)} withholding in a new format",
             f"{ago(120)} withholding read last hour", "no timestamp withholding"]
    f = run(waiting=[held("u1")], dinersclub=lines)
    assert f["payments:refusal:reloadly:AUTH_ERROR"].level == "unknown"
    assert len(f["payments:refusal:unparsed"].evidence["lines"]) == 2


def test_low_runway_counts_only_successful_sends():
    sends = [{"ref": f"st_{i}", "status": "Complete", "usd": 12.0, "at": ago(60)}
             for i in range(20)]
    failed = [{"status": "FAILED", "usd": 50.0, "at": ago(60)}] * 20
    f = run(providers={"dingconnect": wallet(sends, 30.0), "reloadly": wallet(failed, 1.0)})
    assert f["payments:runway:dingconnect"].evidence["runway_hours"] == 3.0
    assert f["payments:runway:dingconnect"].level == "decision"
    assert f["payments:runway:reloadly"].level == "ok"


def test_ref_completed_twice():
    def t(ref, status="Complete"):
        return {"ref": ref, "status": status, "usd": 1.0, "at": ago(60)}
    sends = [t("st_a"), t("st_a"), t("st_b"), t("st_b", "Failed"), t("other"), t("other")]
    d = run(providers={"dingconnect": wallet(sends, 1e6)})["payments:double-completion"]
    assert d.level == "decision" and list(d.evidence["refs"]) == ["st_a"]
    assert d.evidence["extra_usd"] == 1.0


@pytest.mark.parametrize("body", [{"truncated": True, "items": []},
                                  {"truncated": False, "items": [{}] * 500}])
def test_bail_events_cut_short_raise(monkeypatch, body):
    seen = {}

    def fly_get(*path, params):
        seen.update(params)
        return body
    monkeypatch.setattr(payments.io, "fly_get", fly_get)
    with pytest.raises(RuntimeError, match="unread"):
        payments._bail_events(NOW)
    assert seen == {"since": "2026-09-30T12:00:00+00:00", "limit": 500}
