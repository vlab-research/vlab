from datetime import datetime, timedelta, timezone

import pytest

from . import pace

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
CFG = {"pace": {"completion_ref": "q15"}}


def snap(total, last24, end_days=10.0, client=None, target=750, start_days=-20):
    """A snapshot of one country: `total` completes, `last24` of them in the
    last 24 hours, the rest two days back."""
    times = [NOW - timedelta(hours=1)] * last24 + [NOW - timedelta(days=2)] * (total - last24)
    country = {"completes": sorted(t.isoformat() for t in times), "target": target,
               "start_date": (NOW + timedelta(days=start_days)).isoformat(),
               "end_date": (NOW + timedelta(days=end_days)).isoformat(),
               "client_date": client}
    return {"read_at": NOW.isoformat(), "countries": {"AR": country}}


def keys(snapshot, cfg=CFG):
    return sorted((f.level, f.key.split(":")[-1]) for f in pace.check(cfg, snapshot, []))


def test_on_track():
    [f] = pace.check(CFG, snap(500, 50, client="2026-10-14"), [])
    assert (f.level, f.key) == ("ok", "pace:AR:on-track")
    assert f.evidence["remaining"] == 250 and f.evidence["per_day"] == 50
    assert f.evidence["projected_finish"] == (NOW + timedelta(days=5)).isoformat()


def test_behind_end_date_and_client_date():
    assert keys(snap(500, 20, end_days=10, client="2026-10-12")) == [
        ("decision", "behind-client-date"), ("decision", "behind-end-date")]


def test_client_date_is_the_end_of_that_day():
    # 250 at 50/day finishes 6 Oct 12:00, inside 6 Oct.
    assert keys(snap(500, 50, client="2026-10-06")) == [("ok", "on-track")]
    assert keys(snap(500, 50, client="2026-10-05")) == [("decision", "behind-client-date")]


def test_near_target_and_reached():
    assert keys(snap(720, 40)) == [("decision", "near-target")]
    assert keys(snap(750, 40)) == [("decision", "target-reached")]


def test_closing_window():
    assert ("decision", "window-closing") in keys(snap(500, 300, end_days=0.5))
    assert ("decision", "window-closed") in keys(snap(500, 0, end_days=-1))


def test_zero_in_24h_while_recruiting_is_unknown():
    assert keys(snap(500, 0)) == [("unknown", "no-completes")]


def test_zero_before_the_window_opens_is_ok():
    assert keys(snap(0, 0, start_days=1)) == [("ok", "on-track")]


def test_thresholds_are_overridable_but_window_never_under_24h():
    cfg = {"pace": {"completion_ref": "q15", "near_target_days": 3}}
    assert ("decision", "near-target") in keys(snap(650, 40), cfg)
    with pytest.raises(ValueError, match="at least 24"):
        pace.check({"pace": {"window_hours": 6}}, snap(500, 50), [])


def test_missing_end_date_is_unknown():
    s = snap(500, 50)
    s["countries"]["AR"]["end_date"] = None
    assert keys(s) == [("unknown", "no-end-date")]


def test_completes_counts_each_users_first_answer_on_counted_versions(monkeypatch):
    surveys = [{"id": "v12", "survey_name": "AR", "shortcode": "ar1", "created": "2026-09-18T15:00:00Z"},
               {"id": "v11", "survey_name": "AR", "shortcode": "ar1", "created": "2026-09-01T00:00:00Z"},
               {"id": "x", "survey_name": "AR", "shortcode": "arpay", "created": "2026-09-20T00:00:00Z"}]
    rows = [{"question_ref": "q15", "surveyid": "v12", "userid": "u1", "timestamp": "t1"},
            {"question_ref": "q15", "surveyid": "v12", "userid": "u1", "timestamp": "t2"},
            {"question_ref": "q15", "surveyid": "v11", "userid": "u2", "timestamp": "t1"},
            {"question_ref": "q1", "surveyid": "v12", "userid": "u3", "timestamp": "t1"},
            {"question_ref": "q15", "surveyid": "v12", "userid": "u4", "timestamp": "t0", "token": "T"}]
    calls = []

    def fly_get(path, params=None):
        calls.append(params)
        if path == "surveys":
            return surveys
        return {"responses": rows if "after" not in params else rows[:1]}

    monkeypatch.setattr(pace, "PAGE", 5)
    monkeypatch.setattr(pace.io, "fly_get", fly_get)
    cfg = {"pace": {"completion_ref": "q15", "count_from": "2026-09-18T14:35:00Z"},
           "countries": {"AR": {"survey_name": "AR", "questionnaire": ["ar1"]}}}
    assert pace.completes(cfg, "AR") == ["t0", "t1"]
    assert calls[1:] == [
        {"survey": "AR", "question_ref": "q15", "pageSize": 5, "since": "2026-09-18T14:35:00+00:00"},
        {"survey": "AR", "question_ref": "q15", "pageSize": 5, "since": "2026-09-18T14:35:00+00:00",
         "after": "T"}]
