from datetime import datetime, timedelta, timezone

from . import providers

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CFG = {"countries": {"X": {"survey_name": "s", "pay": ["pay1"]}},
       "providers": {"known_codes": ["ProviderError", "PIN_DRIFT"], "ref_prefixes": ["st_"]}}
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
    snap = {"read_at": NOW.isoformat(), "waiting": [], "dinersclub": [],
            "providers": {"dingconnect": wallet(), "reloadly": wallet()}, **kw}
    return {f.key: f for f in providers.check(CFG, snap, history)}


def test_quiet_study_is_all_ok():
    assert {f.level for f in run().values()} == {"ok"}


def test_gap_longer_than_the_window_is_unknown():
    assert run([{"read_at": ago(7 * 60)}])["providers:gap"].level == "unknown"
    assert "providers:gap" not in run() and "providers:gap" not in run([])


def test_refusals_group_distinct_held_users_over_the_window():
    users = ["u1", "u2", "u3"]
    lines = [line(m, u, "PIN_DRIFT") for u, m in zip(users, (300, 200, 10))]
    many = run(waiting=[held(u) for u in users], dinersclub=lines)
    assert many["providers:refusal:dingconnect:PIN_DRIFT"].level == "decision"
    lines = [line(m, "u1", "ProviderError") for m in (10, 100, 300, 400)]
    one = run(waiting=[held("u1"), held("u2"), held("u3", form="q")],
              dinersclub=lines + [line(10, "elsewhere", "ProviderError"),
                                  line(10, "u3", "ProviderError")])
    r = one["providers:refusal:dingconnect:ProviderError"]
    assert r.level == "ok" and r.evidence["per_user"] == {"u1": 3}


def test_unknown_code_and_new_unparsed_line_are_unknown():
    lines = [line(10, "u1", "AUTH_ERROR", "reloadly"), f"{ago(10)} withholding in a new format",
             f"{ago(120)} withholding read last hour", "no timestamp withholding"]
    f = run(waiting=[held("u1")], dinersclub=lines)
    assert f["providers:refusal:reloadly:AUTH_ERROR"].level == "unknown"
    assert len(f["providers:refusal:unparsed"].evidence["lines"]) == 2


def test_low_runway_counts_only_successful_sends():
    sends = [{"ref": f"st_{i}", "status": "Complete", "usd": 12.0, "at": ago(60)}
             for i in range(20)]
    failed = [{"status": "FAILED", "usd": 50.0, "at": ago(60)}] * 20
    f = run(providers={"dingconnect": wallet(sends, 30.0), "reloadly": wallet(failed, 1.0)})
    assert f["providers:runway:dingconnect"].evidence["runway_hours"] == 3.0
    assert f["providers:runway:dingconnect"].level == "decision"
    assert f["providers:runway:reloadly"].level == "ok"


def test_ref_completed_twice():
    def t(ref, status="Complete"):
        return {"ref": ref, "status": status, "usd": 1.0, "at": ago(60)}
    sends = [t("st_a"), t("st_a"), t("st_b"), t("st_b", "Failed"), t("other"), t("other")]
    d = run(providers={"dingconnect": wallet(sends, 1e6)})["providers:double-completion"]
    assert d.level == "decision" and list(d.evidence["refs"]) == ["st_a"]
    assert d.evidence["extra_usd"] == 1.0
