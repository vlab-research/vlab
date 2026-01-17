"""
Tests for report healing functionality.

Tests the healing job that generates respondents_over_time and cost_over_time
reports for recent studies without requiring Facebook API access or running optimization.
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from test.dbfix import cnf, _reset_db

import pandas as pd
import pytest

from .campaign_queries import create_campaign_confs
from .db import execute, query
from .malaria import (
    get_study_conf_for_reports,
    heal_reports_for_study,
    run_report_healing,
    calculate_respondents_over_time_report,
    calculate_cost_over_time_report,
)
from .recruitment_data import day_start, day_end, get_recent_studies


def _dt(day=1, hour=0, month=1, year=2022):
    """Helper to create datetime objects."""
    return datetime(year, month, day, hour)


def create_study(name, user_id="test@email.com"):
    """
    Create a test study with all required dependencies.

    Note: Use insert_study_conf() separately to add dates and configuration.

    Args:
        name: Study name
        user_id: User ID

    Returns:
        Tuple of (user_id, study_id)
    """
    # Create user
    q = """
    INSERT INTO users(id) VALUES (%s)
    ON CONFLICT (id) DO NOTHING
    RETURNING id
    """
    execute(cnf, q, [user_id])

    # Create study
    q = """
    INSERT INTO studies(user_id, name, slug)
    VALUES (%s, %s, %s) RETURNING id
    """
    res = query(cnf, q, [user_id, name, name])
    study_id = list(res)[0][0]

    # Note: study_state is a VIEW based on study_confs with type='recruitment'
    # So dates are set via insert_study_conf() instead

    return user_id, study_id


def insert_study_conf(study_id, start_date, end_date, strata_config=None, recruitment_config=None):
    """
    Insert study configuration including recruitment and strata configs.

    Args:
        study_id: Study ID
        start_date: Study start date
        end_date: Study end date
        strata_config: Optional strata configuration dict
        recruitment_config: Optional recruitment configuration dict
    """
    # Default strata config
    if strata_config is None:
        strata_config = [
            {
                "id": "stratum1",
                "quota": 100,
                "creatives": ["creative1"],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {"geo_locations": {"countries": ["US"]}},
                "metadata": {},
            }
        ]

    # Default recruitment config with all required fields for SimpleRecruitment
    if recruitment_config is None:
        recruitment_config = {
            "ad_campaign_name": "test_campaign",
            "objective": "OUTCOME_ENGAGEMENT",
            "optimization_goal": "CONVERSATIONS",
            "destination_type": "MESSENGER",
            "min_budget": 10,
            "budget": 100,
            "max_sample": 1000,
            "start_date": start_date.isoformat() if isinstance(start_date, datetime) else start_date,
            "end_date": end_date.isoformat() if isinstance(end_date, datetime) else end_date,
            "inference_days_back": 7,
            "incentive_per_respondent": 1.0,
        }

    # Insert recruitment config
    create_campaign_confs(study_id, "recruitment", recruitment_config, cnf)

    # Insert strata config
    create_campaign_confs(study_id, "strata", strata_config, cnf)

    # Insert complete general config (required for StudyConf)
    general_config = {
        "name": "Test Study",
        "ad_account": "test_account",
        "credentials_key": "test_key",
        "credentials_entity": "test_entity",
        "opt_window": 168,
    }
    create_campaign_confs(study_id, "general", general_config, cnf)

    # Insert minimal creatives config
    creatives_config = [
        {
            "name": "creative1",
            "template": {},
            "destination": "messenger",
        }
    ]
    create_campaign_confs(study_id, "creatives", creatives_config, cnf)

    # Insert minimal destinations config
    destinations_config = []
    create_campaign_confs(study_id, "destinations", destinations_config, cnf)

    # Insert minimal audiences config
    audiences_config = []
    create_campaign_confs(study_id, "audiences", audiences_config, cnf)


def insert_inference_data(study_id, user_id, variable, value, timestamp):
    """Insert test inference data (survey responses)."""
    q = """
    INSERT INTO inference_data(study_id, user_id, variable, value_type, value, timestamp, updated)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    # value column is JSONB, so wrap the value in JSON
    execute(
        cnf,
        q,
        [study_id, user_id, variable, "string", json.dumps(value), timestamp, timestamp],
    )


def insert_recruitment_data_event(study_id, period_start, period_end, temp, data):
    """Insert test recruitment data event."""
    q = """
    INSERT INTO recruitment_data_events(study_id, source_name, period_start, period_end, temp, data)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute(
        cnf,
        q,
        [study_id, "facebook", period_start, period_end, temp, json.dumps(data)],
    )


def get_reports(study_id):
    """Get all reports for a study."""
    q = """
    SELECT report_type, details
    FROM adopt_reports
    WHERE study_id = %s
    ORDER BY created DESC
    """
    res = query(cnf, q, [study_id], as_dict=True)
    return list(res)


# Tests for get_recent_studies()
def test_get_recent_studies_returns_empty_for_no_studies():
    """Test that get_recent_studies returns empty list when no studies exist."""
    _reset_db()
    now = _dt(2, 12)
    studies = get_recent_studies(cnf, now, days_back=14)
    assert studies == []


def test_get_recent_studies_returns_currently_active_studies():
    """Test that get_recent_studies includes currently active studies."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("active_study")
    insert_study_conf(study_id, start, end)

    studies = get_recent_studies(cnf, now, days_back=14)
    assert len(studies) == 1
    assert studies[0] == study_id


def test_get_recent_studies_includes_recently_ended_studies():
    """Test that get_recent_studies includes studies that ended within lookback window."""
    _reset_db()
    now = _dt(10, 12)

    # Study ended 5 days ago
    start = _dt(1, 10)
    end = _dt(5, 23)
    user_id, study_id = create_study("recent_study")
    insert_study_conf(study_id, start, end)

    studies = get_recent_studies(cnf, now, days_back=14)
    assert len(studies) == 1
    assert studies[0] == study_id


def test_get_recent_studies_excludes_old_ended_studies():
    """Test that get_recent_studies excludes studies that ended before lookback window."""
    _reset_db()
    now = _dt(30, 12)

    # Study ended 20 days ago
    start = _dt(1, 10)
    end = _dt(10, 23)
    user_id, study_id = create_study("old_study")
    insert_study_conf(study_id, start, end)

    studies = get_recent_studies(cnf, now, days_back=14)
    assert len(studies) == 0


def test_get_recent_studies_respects_days_back_parameter():
    """Test that get_recent_studies correctly uses different lookback windows."""
    _reset_db()
    now = _dt(20, 12)

    # Study ended 5 days ago
    start1 = _dt(1, 10)
    end1 = _dt(15, 23)
    user_id1, study_id1 = create_study("recent1", "user1@email.com")
    insert_study_conf(study_id1, start1, end1)

    # Study ended 10 days ago
    start2 = _dt(1, 10)
    end2 = _dt(10, 23)
    user_id2, study_id2 = create_study("recent2", "user2@email.com")
    insert_study_conf(study_id2, start2, end2)

    # With 7 days lookback, only first study
    studies = get_recent_studies(cnf, now, days_back=7)
    assert len(studies) == 1
    assert study_id1 in studies

    # With 14 days lookback, both studies
    studies = get_recent_studies(cnf, now, days_back=14)
    assert len(studies) == 2
    assert study_id1 in studies
    assert study_id2 in studies


# Tests for get_study_conf_for_reports()
def test_get_study_conf_for_reports_loads_without_fb_credentials():
    """Test that get_study_conf_for_reports loads config without Facebook credentials."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # Should not raise an error even though there are no FB credentials
    study_conf = get_study_conf_for_reports(cnf, study_id)

    assert study_conf is not None
    assert study_conf.id == str(study_id)
    assert study_conf.user.survey_user == str(study_id)
    assert study_conf.user.token == ""


def test_get_study_conf_for_reports_raises_on_missing_config():
    """Test that get_study_conf_for_reports raises error when config is missing."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    # Don't insert study_conf

    with pytest.raises(Exception):
        get_study_conf_for_reports(cnf, study_id)


# Tests for heal_reports_for_study()
def test_heal_reports_for_study_creates_both_reports_successfully():
    """Test that heal_reports_for_study creates both respondents_over_time and cost_over_time reports."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # Insert some test inference data
    insert_inference_data(study_id, "user1", "stratum", "stratum1", start + timedelta(hours=2))
    insert_inference_data(study_id, "user2", "stratum", "stratum1", start + timedelta(hours=4))

    # Insert recruitment data for cost calculation
    recruitment_data = {
        "campaign1": {
            "stratum1": {
                "spend": "100.0",
                "reach": "1000",
                "unique_clicks": "50",
                "impressions": "2000",
                "date_start": start.date().isoformat(),
                "date_stop": start.date().isoformat(),
            }
        }
    }
    insert_recruitment_data_event(study_id, start, day_end(start), False, recruitment_data)

    # Run healing
    respondents_ok, cost_ok = heal_reports_for_study(cnf, study_id)

    assert respondents_ok is True
    assert cost_ok is True

    # Verify reports were created
    reports = get_reports(study_id)
    assert len(reports) >= 2

    report_types = [r["report_type"] for r in reports]
    assert "respondents_over_time" in report_types
    assert "cost_over_time" in report_types


def test_heal_reports_for_study_handles_empty_inference_data():
    """Test that heal_reports_for_study handles empty inference data gracefully."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # No inference data inserted

    # Run healing - should still succeed but with empty data
    respondents_ok, cost_ok = heal_reports_for_study(cnf, study_id)

    assert respondents_ok is True
    assert cost_ok is True

    # Verify reports were created (even if empty)
    reports = get_reports(study_id)
    report_types = [r["report_type"] for r in reports]
    assert "respondents_over_time" in report_types
    assert "cost_over_time" in report_types


def test_heal_reports_for_study_continues_on_single_report_failure():
    """Test that heal_reports_for_study continues when one report fails."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # Insert some test inference data
    insert_inference_data(study_id, "user1", "stratum", "stratum1", start + timedelta(hours=2))

    # Mock to make respondents report fail
    with patch(
        "adopt.malaria.calculate_respondents_over_time_report",
        side_effect=Exception("Test error"),
    ):
        respondents_ok, cost_ok = heal_reports_for_study(cnf, study_id)

    # Respondents failed, but cost should still succeed
    assert respondents_ok is False
    assert cost_ok is True


def test_heal_reports_for_study_returns_false_on_missing_config():
    """Test that heal_reports_for_study returns false when config is missing."""
    _reset_db()
    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    # Don't insert study_conf

    respondents_ok, cost_ok = heal_reports_for_study(cnf, study_id)

    assert respondents_ok is False
    assert cost_ok is False


# Tests for run_report_healing()
def test_run_report_healing_processes_multiple_studies():
    """Test that run_report_healing processes all recent studies."""
    _reset_db()
    now = _dt(10, 12)

    # Create two recent studies
    start1 = _dt(1, 10)
    end1 = _dt(5, 23)
    user_id1, study_id1 = create_study("study1", "user1@email.com")
    insert_study_conf(study_id1, start1, end1)
    insert_inference_data(study_id1, "user1", "stratum", "stratum1", start1 + timedelta(hours=2))

    start2 = _dt(2, 10)
    end2 = _dt(6, 23)
    user_id2, study_id2 = create_study("study2", "user2@email.com")
    insert_study_conf(study_id2, start2, end2)
    insert_inference_data(study_id2, "user2", "stratum", "stratum1", start2 + timedelta(hours=2))

    # Mock Env to provide database config
    with patch("adopt.malaria.Env") as mock_env:
        mock_env.return_value.return_value = cnf
        run_report_healing(days_back=14, now=now)

    # Verify both studies have reports
    reports1 = get_reports(study_id1)
    reports2 = get_reports(study_id2)

    assert len(reports1) >= 2
    assert len(reports2) >= 2


def test_run_report_healing_continues_on_study_failure():
    """Test that run_report_healing continues processing when one study fails."""
    _reset_db()
    now = _dt(10, 12)

    # Create two studies
    start1 = _dt(1, 10)
    end1 = _dt(5, 23)
    user_id1, study_id1 = create_study("study1", "user1@email.com")
    insert_study_conf(study_id1, start1, end1)
    insert_inference_data(study_id1, "user1", "stratum", "stratum1", start1 + timedelta(hours=2))

    start2 = _dt(2, 10)
    end2 = _dt(6, 23)
    user_id2, study_id2 = create_study("study2", "user2@email.com")
    # Don't insert config for study2 - will fail

    # Mock Env to provide database config
    with patch("adopt.malaria.Env") as mock_env:
        mock_env.return_value.return_value = cnf
        run_report_healing(days_back=14, now=now)

    # Study1 should have reports, study2 should not
    reports1 = get_reports(study_id1)
    reports2 = get_reports(study_id2)

    assert len(reports1) >= 2
    assert len(reports2) == 0


def test_run_report_healing_handles_no_studies():
    """Test that run_report_healing handles case with no studies gracefully."""
    _reset_db()

    # Mock Env to provide database config
    with patch("adopt.malaria.Env") as mock_env:
        mock_env.return_value.return_value = cnf
        # Should not raise an error
        run_report_healing(days_back=14)


# Tests for calculate_respondents_over_time_report()
def test_calculate_respondents_over_time_report_with_valid_data():
    """Test that calculate_respondents_over_time_report generates correct structure."""
    _reset_db()
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # Insert inference data
    insert_inference_data(study_id, "user1", "stratum", "stratum1", start + timedelta(hours=2))
    insert_inference_data(study_id, "user2", "stratum", "stratum1", start + timedelta(hours=4))
    insert_inference_data(study_id, "user3", "stratum", "stratum1", start + timedelta(hours=6))

    # Load the data
    from .responses import get_inference_data
    from .study_conf import StratumConf

    df = get_inference_data(study_id, study_id, cnf, start, end)

    strata = [
        StratumConf(
            id="stratum1",
            quota=100,
            creatives=["creative1"],
            audiences=[],
            excluded_audiences=[],
            facebook_targeting={"geo_locations": {"countries": ["US"]}},
            metadata={},
        )
    ]

    report = calculate_respondents_over_time_report(df, strata, start, end)

    assert "data" in report
    assert isinstance(report["data"], list)


def test_calculate_respondents_over_time_report_with_empty_data():
    """Test that calculate_respondents_over_time_report handles empty data."""
    from .study_conf import StratumConf

    start = _dt(1, 10)
    end = _dt(3, 23)

    df = pd.DataFrame([])
    strata = [
        StratumConf(
            id="stratum1",
            quota=100,
            creatives=["creative1"],
            audiences=[],
            excluded_audiences=[],
            facebook_targeting={"geo_locations": {"countries": ["US"]}},
            metadata={},
        )
    ]

    report = calculate_respondents_over_time_report(df, strata, start, end)

    assert report == {"data": []}


# Tests for calculate_cost_over_time_report()
def test_calculate_cost_over_time_report_with_valid_data():
    """Test that calculate_cost_over_time_report generates correct structure."""
    _reset_db()
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("test_study")
    insert_study_conf(study_id, start, end)

    # Insert inference data
    insert_inference_data(study_id, "user1", "stratum", "stratum1", start + timedelta(hours=2))
    insert_inference_data(study_id, "user2", "stratum", "stratum1", start + timedelta(hours=4))

    # Insert recruitment data
    recruitment_data = {
        "campaign1": {
            "stratum1": {
                "spend": "100.0",
                "reach": "1000",
                "unique_clicks": "50",
                "impressions": "2000",
                "date_start": start.date().isoformat(),
                "date_stop": start.date().isoformat(),
            }
        }
    }
    insert_recruitment_data_event(study_id, start, day_end(start), False, recruitment_data)

    # Load the data
    from .responses import get_inference_data
    from .study_conf import StratumConf

    df = get_inference_data(study_id, study_id, cnf, start, end)

    strata = [
        StratumConf(
            id="stratum1",
            quota=100,
            creatives=["creative1"],
            audiences=[],
            excluded_audiences=[],
            facebook_targeting={"geo_locations": {"countries": ["US"]}},
            metadata={},
        )
    ]

    report = calculate_cost_over_time_report(df, strata, cnf, study_id, 1.0)

    assert isinstance(report, list)


def test_calculate_cost_over_time_report_with_empty_data():
    """Test that calculate_cost_over_time_report handles empty data."""
    from .study_conf import StratumConf

    df = pd.DataFrame([])
    strata = [
        StratumConf(
            id="stratum1",
            quota=100,
            creatives=["creative1"],
            audiences=[],
            excluded_audiences=[],
            facebook_targeting={"geo_locations": {"countries": ["US"]}},
            metadata={},
        )
    ]

    report = calculate_cost_over_time_report(df, strata, cnf, "test_study_id", 1.0)

    assert report == []
