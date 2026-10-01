from datetime import datetime, timedelta, timezone

import pytest

from . import pace

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
CFG = {"pace": {"completion_ref": "q15"}}


def snap(total, last24, end_days=10.0, client=None, target=750, start_days=-20):
    """A snapshot of one part: `total` completes, `last24` of them in the
    last 24 hours, the rest two days back."""
    times = [NOW - timedelta(hours=1)] * last24 + [NOW - timedelta(days=2)] * (total - last24)
    part = {"completes": sorted(t.isoformat() for t in times), "target": target,
            "start_date": (NOW + timedelta(days=start_days)).isoformat(),
            "end_date": (NOW + timedelta(days=end_days)).isoformat(),
            "client_date": client}
    return {"read_at": NOW.isoformat(), "parts": {"AR": part}}


def keys(snapshot, cfg=CFG):
    """The one finding's level and reasons."""
    [f] = pace.check(cfg, snapshot, [])
    assert f.key == "pace:AR"
    return f.level, f.evidence["reasons"]


def test_on_track():
    [f] = pace.check(CFG, snap(500, 50, client="2026-10-14"), [])
    assert (f.level, f.key) == ("ok", "pace:AR")
    assert f.evidence["remaining"] == 250 and f.evidence["per_day"] == 50
    assert f.evidence["projected_finish"] == (NOW + timedelta(days=5)).isoformat()


def test_behind_end_date_and_client_date_is_one_finding_naming_both():
    [f] = pace.check(CFG, snap(500, 20, end_days=10, client="2026-10-12"), [])
    assert f.level == "decision"
    assert f.evidence["reasons"] == ["behind-end-date", "behind-client-date"]
    assert "after the end date 11 Oct 12:00 UTC and the client date 13 Oct 00:00 UTC" in f.summary


def test_client_date_is_the_end_of_that_day():
    # 250 at 50/day finishes 6 Oct 12:00, inside 6 Oct.
    assert keys(snap(500, 50, client="2026-10-06")) == ("ok", ["on-track"])
    assert keys(snap(500, 50, client="2026-10-05")) == ("decision", ["behind-client-date"])


def test_near_target_and_reached():
    assert keys(snap(720, 40)) == ("decision", ["near-target"])
    assert keys(snap(750, 40)) == ("decision", ["target-reached"])


def test_closing_window():
    assert keys(snap(500, 300, end_days=0.5)) == (
        "decision", ["near-target", "window-closing", "behind-end-date"])
    assert keys(snap(500, 10, end_days=-1)) == ("decision", ["window-closed", "behind-end-date"])


def test_zero_in_24h_is_unknown_only_once_the_window_opens():
    assert keys(snap(500, 0)) == ("unknown", ["no-completes"])
    assert keys(snap(0, 0, start_days=1)) == ("ok", ["on-track"])


def test_thresholds_are_overridable_but_window_never_under_24h():
    cfg = {"pace": {"completion_ref": "q15", "near_target_days": 3}}
    assert keys(snap(650, 40), cfg) == ("decision", ["near-target"])
    with pytest.raises(ValueError, match="at least 24"):
        pace.check({"pace": {"window_hours": 6}}, snap(500, 50), [])


def test_missing_end_date_is_unknown():
    s = snap(500, 50)
    s["parts"]["AR"]["end_date"] = None
    assert keys(s) == ("unknown", ["no-end-date"])


def test_completes_are_the_refs_answered_from_count_from():
    rows = [{"user_id": "u1", "variable": "q15", "timestamp": "2026-09-20T10:00:00"},
            {"user_id": "u2", "variable": "q15", "timestamp": "2026-09-18T14:34:59"},
            {"user_id": "u3", "variable": "q15", "timestamp": "2026-09-18T14:35:00"},
            {"user_id": "u1", "variable": "Gender", "timestamp": "2026-09-21T00:00:00"}]
    since = datetime(2026, 9, 18, 14, 35, tzinfo=timezone.utc)
    assert pace.completes(rows, "q15", since) == ["2026-09-18T14:35:00", "2026-09-20T10:00:00"]
    assert len(pace.completes(rows, "q15", None)) == 3
