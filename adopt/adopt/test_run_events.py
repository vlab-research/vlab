import json
import logging
import re
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from facebook_business.exceptions import FacebookRequestError

from . import malaria
from .run_events import (
    DEFAULT_WINDOW,
    EVENT_RUN_ERROR,
    EVENT_RUN_OK,
    EVENT_RUN_STARTED,
    MAX_MESSAGE_CHARS,
    SOURCE_INFERENCE,
    SOURCE_OPTIMIZER_ADS,
    SOURCE_OPTIMIZER_AUDIENCE,
    SOURCE_OPTIMIZER_RECRUITMENT_DATA,
    SOURCE_PERIODS,
    STAGE_EXECUTE,
    STAGE_LOAD,
    STAGE_PLAN,
    RunEvent,
    describe_exception,
    event_row,
    is_within_window,
    max_recency_window,
    record_events,
    recency_window,
    run_error,
    run_fingerprint,
    run_ok,
    run_started,
)

STUDY = "7a1f6b8e-0000-0000-0000-000000000001"


def _facebook_error(error, params=None):
    return FacebookRequestError(
        "Call was not successful",
        {
            "method": "POST",
            "path": "/act_123/ads",
            "params": params or {"access_token": "EAAB-SECRET-TOKEN"},
        },
        400,
        {},
        json.dumps({"error": error}),
    )


# ---------------------------------------------------------------- mapping


def test_run_started_carries_no_fingerprint_or_severity():
    e = run_started(STUDY, SOURCE_OPTIMIZER_ADS, "r1")
    assert e == RunEvent(STUDY, "optimizer:ads", "r1", EVENT_RUN_STARTED)


def test_run_ok_and_run_error_share_the_source_fingerprint():
    ok = run_ok(STUDY, SOURCE_OPTIMIZER_ADS, "r1")
    err = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r2", STAGE_PLAN, ValueError("x"))

    assert ok.event_type == EVENT_RUN_OK
    assert ok.severity == ""
    assert err.event_type == EVENT_RUN_ERROR
    assert err.severity == "error"
    assert ok.fingerprint == err.fingerprint == "optimizer:ads:run"


def test_fingerprint_is_stable_across_runs_and_messages():
    # Repeated refusals must group into one open error, so nothing volatile
    # (run id, message text) may reach the fingerprint.
    a = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_PLAN, ValueError("a"))
    b = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r2", STAGE_EXECUTE, KeyError("b"))
    assert a.fingerprint == b.fingerprint == run_fingerprint(SOURCE_OPTIMIZER_ADS)


def test_each_job_has_its_own_fingerprint():
    # A healthy recruitment-data run must not close a failing ads run.
    sources = [
        SOURCE_OPTIMIZER_ADS,
        SOURCE_OPTIMIZER_AUDIENCE,
        SOURCE_OPTIMIZER_RECRUITMENT_DATA,
    ]
    assert len({run_fingerprint(s) for s in sources}) == 3


def test_run_error_message_keeps_the_guard_text_verbatim():
    guard = Exception(
        "Creative 'c1' points at destination 'wa', which opens ['WHATSAPP'], "
        "but its template ad's asset_feed_spec opens ['MESSENGER']. Rebuild "
        "the template ad in Ads Manager to open ['WHATSAPP']."
    )
    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_PLAN, guard)

    assert e.message == f"Could not work out what to change on Facebook: {guard}"
    assert e.details == {"stage": "plan", "exception": "Exception"}


def test_run_error_names_the_stage():
    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_LOAD, KeyError("general"))
    assert e.message.startswith("Could not load the study's configuration: ")
    assert e.details["stage"] == "load"


def test_unknown_stage_still_produces_a_message():
    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", "mystery", ValueError("x"))
    assert e.message == "Failed during mystery: x"


def test_exception_without_text_falls_back_to_its_type():
    assert describe_exception(KeyboardInterrupt()) == (
        "KeyboardInterrupt",
        {"exception": "KeyboardInterrupt"},
    )


def test_long_messages_are_truncated():
    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_PLAN, ValueError("x" * 10_000))
    assert len(e.message) == MAX_MESSAGE_CHARS
    assert e.message.endswith("…")


def test_facebook_error_uses_meta_fields_and_never_the_token():
    exc = _facebook_error(
        {
            "message": "Invalid parameter",
            "type": "OAuthException",
            "code": 100,
            "error_subcode": 1885183,
            "error_user_title": "Ads creative post was created by an app that is in development mode",
            "error_user_msg": "Switch the app to live mode.",
            "is_transient": False,
        }
    )
    assert "EAAB-SECRET-TOKEN" in str(exc)  # the reason str() is not used

    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_EXECUTE, exc)

    assert "EAAB-SECRET-TOKEN" not in e.message
    assert "EAAB-SECRET-TOKEN" not in json.dumps(e.details)
    assert e.message == (
        "Facebook refused a change: Invalid parameter — Ads creative post was "
        "created by an app that is in development mode: Switch the app to live mode."
    )
    assert e.details == {
        "stage": "execute",
        "exception": "FacebookRequestError",
        "http_status": 400,
        "api_error_code": 100,
        "api_error_subcode": 1885183,
        "api_error_type": "OAuthException",
        "is_transient": False,
        "method": "POST",
        "path": "/act_123/ads",
    }


def test_facebook_error_without_user_message():
    exc = _facebook_error({"message": "Unsupported post request.", "code": 100})
    description, details = describe_exception(exc)
    assert description == "Unsupported post request."
    assert details["api_error_code"] == 100
    assert "api_error_subcode" not in details


def test_event_row_serialises_details_as_json():
    e = run_error(STUDY, SOURCE_OPTIMIZER_ADS, "r1", STAGE_PLAN, ValueError("x"))
    row = event_row(e)
    assert row[:7] == (
        STUDY,
        "optimizer:ads",
        "r1",
        "run_error",
        "optimizer:ads:run",
        "error",
        "Could not work out what to change on Facebook: x",
    )
    assert json.loads(row[7]) == {"stage": "plan", "exception": "ValueError"}
    assert event_row(run_started(STUDY, SOURCE_OPTIMIZER_ADS, "r1"))[7] is None


# ---------------------------------------------------------------- windows


def test_window_is_three_periods():
    assert recency_window(SOURCE_INFERENCE) == timedelta(hours=3)
    assert recency_window(SOURCE_OPTIMIZER_ADS) == timedelta(hours=12)


def test_unknown_source_gets_the_default_window():
    assert recency_window("connector:fly") == DEFAULT_WINDOW


def test_is_within_window_per_source():
    five_hours = timedelta(hours=5)
    assert not is_within_window(SOURCE_INFERENCE, five_hours)
    assert is_within_window(SOURCE_OPTIMIZER_ADS, five_hours)


def test_max_window_covers_every_source():
    assert all(max_recency_window() >= recency_window(s) for s in SOURCE_PERIODS)


CRONJOB_SOURCES = {
    "swoosh": SOURCE_INFERENCE,
    "adopt-ads": SOURCE_OPTIMIZER_ADS,
    "adopt-audience": SOURCE_OPTIMIZER_AUDIENCE,
    "adopt-recruitment-data": SOURCE_OPTIMIZER_RECRUITMENT_DATA,
}

VALUES_DIR = Path(__file__).resolve().parents[2] / "devops" / "values"


def cron_period(schedule: str) -> timedelta:
    """The period of the minute/hour cron shapes the values files use."""
    minute, hour, *rest = schedule.split()
    if rest != ["*", "*", "*"] or not re.fullmatch(r"\d+", minute):
        raise ValueError(f"unhandled cron schedule {schedule!r}")
    if hour == "*":
        return timedelta(hours=1)
    step = re.fullmatch(r"\*/(\d+)", hour)
    if step:
        return timedelta(hours=int(step[1]))
    return timedelta(days=1)


def test_cron_period():
    assert cron_period("30 * * * *") == timedelta(hours=1)
    assert cron_period("30 */2 * * *") == timedelta(hours=2)
    assert cron_period("0 5 * * *") == timedelta(days=1)


@pytest.mark.skipif(not VALUES_DIR.exists(), reason="devops/values not checked out")
def test_every_deployed_cron_fits_its_source_period():
    """A slowed cron would make its errors flicker; say so here instead."""
    checked = 0
    for values_file in sorted(VALUES_DIR.glob("*.yaml")):
        values = yaml.safe_load(values_file.read_text()) or {}
        for job in values.get("cronjobs") or []:
            source = CRONJOB_SOURCES.get(job.get("name"))
            if source is None:
                continue
            period = cron_period(job["schedule"])
            assert period <= SOURCE_PERIODS[source], (
                f"{values_file.name}: {job['name']} runs every {period}, longer "
                f"than SOURCE_PERIODS[{source!r}] = {SOURCE_PERIODS[source]}"
            )
            checked += 1
    assert checked > 0


# ---------------------------------------------------------------- write path


def test_record_events_writes_each_event():
    events = [
        run_started(STUDY, SOURCE_OPTIMIZER_ADS, "r1"),
        run_ok(STUDY, SOURCE_OPTIMIZER_ADS, "r1"),
    ]
    with patch("adopt.run_events.execute") as execute:
        assert record_events("db", events) is True

    assert [c.args[2] for c in execute.call_args_list] == [event_row(e) for e in events]


def test_record_events_swallows_and_logs_a_failed_write(caplog):
    with patch("adopt.run_events.execute", side_effect=RuntimeError("db down")):
        with caplog.at_level(logging.WARNING):
            ok = record_events("db", [run_started(STUDY, SOURCE_OPTIMIZER_ADS, "r1")])

    assert ok is False
    assert "could not record ['run_started']" in caplog.text
    assert "db down" in caplog.text


def test_record_events_with_nothing_to_write_touches_nothing():
    with patch("adopt.run_events.execute") as execute:
        assert record_events("db", []) is True
    execute.assert_not_called()


# ---------------------------------------------------------------- run_updates


def _study(name="s"):
    return SimpleNamespace(general=SimpleNamespace(name=name))


def _run(fn, studies, load=None, run_instructions=None, record=None):
    """Run run_updates with the IO around it replaced; returns recorded events."""
    recorded = []
    load = load or (lambda s, db, env: (_study(s), object()))

    def _record(db_conf, events):
        if record is not None:
            return record(db_conf, events)
        recorded.extend(events)
        return True

    with patch.object(malaria, "get_db_conf", return_value="db"), patch.object(
        malaria, "get_active_studies", return_value=studies
    ), patch.object(malaria, "load_basics", side_effect=load), patch.object(
        malaria, "run_instructions", side_effect=run_instructions
    ), patch.object(
        malaria, "record_events", side_effect=_record
    ):
        malaria.run_updates(fn, SOURCE_OPTIMIZER_ADS)

    return recorded


def test_run_updates_records_started_then_ok():
    events = _run(lambda db, study, state: ([], None), ["s1"])

    assert [(e.study_id, e.event_type) for e in events] == [
        ("s1", "run_started"),
        ("s1", "run_ok"),
    ]
    assert events[0].run_id == events[1].run_id
    assert {e.source for e in events} == {"optimizer:ads"}


def test_run_updates_job_with_no_instructions_is_ok():
    # update_recruitment_data_for_campaign returns (None, None).
    events = _run(lambda db, study, state: (None, None), ["s1"])
    assert [e.event_type for e in events] == ["run_started", "run_ok"]


def test_run_updates_records_the_refusal_and_keeps_going(caplog):
    def fn(db, study, state):
        if study.general.name == "bad":
            raise Exception("refused to build ads for ad set X because Y, fix Z")
        return [], None

    with caplog.at_level(logging.ERROR):
        events = _run(fn, ["bad", "good"])

    assert [(e.study_id, e.event_type) for e in events] == [
        ("bad", "run_started"),
        ("bad", "run_error"),
        ("good", "run_started"),
        ("good", "run_ok"),
    ]
    err = events[1]
    assert err.details["stage"] == "plan"
    assert err.message.endswith("refused to build ads for ad set X because Y, fix Z")
    assert "Error updating campaign bad (plan)" in caplog.text


def test_run_updates_stage_for_load_and_execute_failures():
    def load(s, db, env):
        if s == "unloadable":
            raise KeyError("general")
        return _study(s), object()

    def execute(instructions, state, db_conf):
        raise RuntimeError("graph said no")

    events = _run(
        lambda db, study, state: ([SimpleNamespace(node="adset", action="update")], None),
        ["unloadable", "rejected"],
        load=load,
        run_instructions=execute,
    )

    errors = {e.study_id: e for e in events if e.event_type == "run_error"}
    assert errors["unloadable"].details["stage"] == "load"
    assert errors["rejected"].details["stage"] == "execute"


def test_failed_event_write_does_not_hide_the_error(caplog):
    # record_events is best-effort; even if it reports failure, the original
    # error must already be in the log.
    def fn(db, study, state):
        raise Exception("refused to build ads for ad set X")

    with caplog.at_level(logging.ERROR):
        _run(fn, ["s1"], record=lambda db, events: False)

    assert "refused to build ads for ad set X" in caplog.text


def test_update_jobs_write_under_their_own_source():
    with patch.object(malaria, "run_updates") as run_updates:
        malaria.update_ads()
        malaria.update_audience()
        malaria.update_recruitment_data()

    assert [c.args[1] for c in run_updates.call_args_list] == [
        SOURCE_OPTIMIZER_ADS,
        SOURCE_OPTIMIZER_AUDIENCE,
        SOURCE_OPTIMIZER_RECRUITMENT_DATA,
    ]
