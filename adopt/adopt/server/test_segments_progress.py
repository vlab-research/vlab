import json
import os
import uuid
from datetime import datetime
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch
import pandas as pd
from fastapi.testclient import TestClient

from ..db import execute, query
from ..study_conf import StratumConf
from ..test_study_conf import _simple
from ..recruitment_data import AdPlatformRecruitmentStats

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from .server import app

client = TestClient(app)

user_id = "test|111"


def _create_user(user_id):
    q = "insert into users (id) values (%s)"
    execute(db_conf, q, (user_id,))


def _create_org(user_id, name):
    org_id = uuid.uuid4()
    insert_query = "insert into orgs (id, name) values (%s, %s)"
    execute(db_conf, insert_query, (org_id, name))
    insert_query = "insert into orgs_lookup (org_id, user_id) values (%s, %s)"
    execute(db_conf, insert_query, (org_id, user_id))
    return org_id


def _create_study(user_id, org_id, slug):
    insert_query = """
    insert into studies (user_id, org_id, name, slug)
    values (%s, %s,  %s, %s)
    returning id
    """
    res = query(db_conf, insert_query, (user_id, org_id, slug, slug), as_dict=True)
    return list(res)[0]["id"]


def _user_and_study_setup():
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")
    study_id = _create_study(user_id, org_id, "foo-study")

    # Create fake credentials for the study
    insert_query = """
    insert into credentials (user_id, key, entity, details)
    values (%s, %s, %s, %s)
    """
    execute(
        db_conf,
        insert_query,
        (user_id, "facebook", "facebook", json.dumps({"access_token": "fake_token"})),
    )

    token = "verysecret"
    headers = {"Authorization": f"Bearer {token}"}
    return org_id, headers


def _setup_segments_progress_config(org_id, headers, strata_list):
    """Helper to set up configurations for segments progress tests."""
    # Post general conf (required for credentials)
    general_conf = {
        "name": "foo",
        "opt_window": 48,
        "ad_account": "234",
        "credentials_key": "facebook",
        "credentials_entity": "facebook",
    }
    client.post(
        f"/{org_id}/studies/foo-study/confs/general",
        headers=headers,
        json=general_conf,
    )

    # Post recruitment conf
    recruitment_conf = json.loads(_simple().model_dump_json())
    client.post(
        f"/{org_id}/studies/foo-study/confs/recruitment",
        headers=headers,
        json=recruitment_conf,
    )

    # Post strata conf
    strata_conf = []
    for stratum_data in strata_list:
        stratum = StratumConf(**stratum_data)
        strata_conf.append(stratum.model_dump())

    client.post(
        f"/{org_id}/studies/foo-study/confs/strata",
        headers=headers,
        json=strata_conf,
    )


# ============================================================================
# Tests for get_segments_progress endpoint
# ============================================================================


@patch("adopt.campaign_queries.get_user_info")
@patch("adopt.recruitment_data.calculate_stat_sql")
@patch("adopt.responses.get_inference_data")
@patch("adopt.server.auth.verify_token")
def test_segments_progress_with_empty_inference_data(
    verify_mock,
    get_inference_data_mock,
    calculate_stat_sql_mock,
    get_user_info_mock,
):
    """Test segments progress with no participants yet (empty inference data)."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    # Setup configuration
    _setup_segments_progress_config(
        org_id,
        headers,
        [
            {
                "id": "stratum_1",
                "name": "Stratum 1",
                "quota": 100,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {},
                "metadata": {},
            }
        ],
    )

    # Mock user info
    get_user_info_mock.return_value = {"survey_user": "test-survey-user"}

    # Return None for empty inference data
    get_inference_data_mock.return_value = None
    calculate_stat_sql_mock.return_value = {}

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200

    res_data = res.json()
    assert "data" in res_data
    assert res_data["data"] == []


@patch("adopt.campaign_queries.get_user_info")
@patch("adopt.recruitment_data.calculate_stat_sql")
@patch("adopt.responses.get_inference_data")
@patch("adopt.server.auth.verify_token")
def test_segments_progress_with_empty_dataframe(
    verify_mock,
    get_inference_data_mock,
    calculate_stat_sql_mock,
    get_user_info_mock,
):
    """Test segments progress with empty DataFrame (no participants yet)."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    _setup_segments_progress_config(
        org_id,
        headers,
        [
            {
                "id": "stratum_1",
                "name": "Stratum 1",
                "quota": 100,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {},
                "metadata": {},
            }
        ],
    )

    # Mock user info
    get_user_info_mock.return_value = {"survey_user": "test-survey-user"}

    # Return empty DataFrame
    get_inference_data_mock.return_value = pd.DataFrame(
        columns=["user_id", "variable", "value_type", "value", "timestamp", "updated"]
    )
    calculate_stat_sql_mock.return_value = {}

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200

    res_data = res.json()
    assert "data" in res_data
    assert res_data["data"] == []


@patch("adopt.campaign_queries.get_latest_respondents_over_time_report")
@patch("adopt.server.auth.verify_token")
def test_segments_progress_returns_data_with_single_stratum(
    verify_mock,
    get_latest_respondents_over_time_report_mock,
):
    """Test segments progress with data from a single stratum."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    _setup_segments_progress_config(
        org_id,
        headers,
        [
            {
                "id": "stratum_1",
                "name": "Stratum 1",
                "quota": 100,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {},
                "metadata": {},
            }
        ],
    )

    # Mock the pre-computed report from database
    # Report contains hourly buckets with cumulative participant counts
    report_data = {
        "data": [
            {
                "datetime": int(datetime(2024, 1, 1, 0, 0).timestamp() * 1000),
                "totalParticipants": 2,
                "segments": [
                    {"id": "stratum_1", "participants": 2}
                ],
            },
            {
                "datetime": int(datetime(2024, 1, 2, 0, 0).timestamp() * 1000),
                "totalParticipants": 3,
                "segments": [
                    {"id": "stratum_1", "participants": 3}
                ],
            },
        ]
    }
    get_latest_respondents_over_time_report_mock.return_value = report_data

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200

    res_data = res.json()
    assert len(res_data["data"]) > 0

    # Verify all buckets have only one segment
    for bucket in res_data["data"]:
        assert len(bucket["segments"]) == 1
        assert bucket["segments"][0]["id"] == "stratum_1"

    # Verify participant counts are cumulative
    first_bucket = res_data["data"][0]
    second_bucket = res_data["data"][1]
    assert first_bucket["segments"][0]["participants"] == 2
    assert second_bucket["segments"][0]["participants"] == 3


@patch("adopt.campaign_queries.get_latest_respondents_over_time_report")
@patch("adopt.server.auth.verify_token")
def test_segments_progress_returns_cumulative_counts(
    verify_mock,
    get_latest_respondents_over_time_report_mock,
):
    """Test that segments progress correctly calculates cumulative counts."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    _setup_segments_progress_config(
        org_id,
        headers,
        [
            {
                "id": "stratum_1",
                "name": "Stratum 1",
                "quota": 100,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {},
                "metadata": {},
            }
        ],
    )

    # Mock the pre-computed report with cumulative counts across multiple days
    report_data = {
        "data": [
            {
                "datetime": int(datetime(2024, 1, 1, 0, 0).timestamp() * 1000),
                "totalParticipants": 2,
                "segments": [
                    {"id": "stratum_1", "participants": 2}
                ],
            },
            {
                "datetime": int(datetime(2024, 1, 2, 0, 0).timestamp() * 1000),
                "totalParticipants": 3,
                "segments": [
                    {"id": "stratum_1", "participants": 3}
                ],
            },
            {
                "datetime": int(datetime(2024, 1, 3, 0, 0).timestamp() * 1000),
                "totalParticipants": 4,
                "segments": [
                    {"id": "stratum_1", "participants": 4}
                ],
            },
        ]
    }
    get_latest_respondents_over_time_report_mock.return_value = report_data

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200

    res_data = res.json()

    # Extract cumulative counts from each bucket
    counts = [
        bucket["segments"][0]["participants"]
        for bucket in res_data["data"]
    ]

    # Check that counts are non-decreasing (cumulative)
    for i in range(1, len(counts)):
        assert counts[i] >= counts[i - 1], f"Counts should be cumulative, but decreased from {counts[i-1]} to {counts[i]}"


@patch("adopt.campaign_queries.get_latest_respondents_over_time_report")
@patch("adopt.server.auth.verify_token")
def test_segments_progress_verifies_response_structure(
    verify_mock,
    get_latest_respondents_over_time_report_mock,
):
    """Test that response structure matches expected schema with correct data types."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    _setup_segments_progress_config(
        org_id,
        headers,
        [
            {
                "id": "stratum_1",
                "name": "Stratum 1",
                "quota": 100,
                "creatives": [],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {},
                "metadata": {},
            }
        ],
    )

    # Mock the pre-computed report
    report_data = {
        "data": [
            {
                "datetime": int(datetime(2024, 1, 1, 0, 0).timestamp() * 1000),
                "totalParticipants": 1,
                "segments": [
                    {"id": "stratum_1", "participants": 1}
                ],
            }
        ]
    }
    get_latest_respondents_over_time_report_mock.return_value = report_data

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200

    res_data = res.json()

    # Verify top-level structure
    assert "data" in res_data
    assert isinstance(res_data["data"], list)

    if len(res_data["data"]) > 0:
        bucket = res_data["data"][0]

        # Verify bucket structure
        assert "datetime" in bucket
        assert isinstance(bucket["datetime"], int)  # Unix timestamp in milliseconds
        assert bucket["datetime"] > 0

        assert "totalParticipants" in bucket
        assert isinstance(bucket["totalParticipants"], int)
        assert bucket["totalParticipants"] >= 0

        assert "segments" in bucket
        assert isinstance(bucket["segments"], list)

        if len(bucket["segments"]) > 0:
            segment = bucket["segments"][0]

            # Verify segment structure and data types
            expected_fields = ["id", "participants"]
            for field in expected_fields:
                assert field in segment, f"Missing field: {field}"

            # Verify data types
            assert isinstance(segment["id"], str)
            assert isinstance(segment["participants"], int)

            # Verify non-negative values
            assert segment["participants"] >= 0


@patch("adopt.server.auth.verify_token")
def test_segments_progress_study_not_found(verify_mock):
    """Test segments progress returns 404 when study is not found."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    res = client.get(
        f"/{org_id}/studies/non-existent-study/segments-progress", headers=headers
    )
    assert res.status_code == 404
    assert "Study not found" in res.json()["detail"]


@patch("adopt.server.auth.verify_token")
def test_segments_progress_no_strata_configured(verify_mock):
    """Test segments progress returns empty data when no strata are configured."""
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    # Post only recruitment conf, no strata
    recruitment_conf = json.loads(_simple().model_dump_json())
    client.post(
        f"/{org_id}/studies/foo-study/confs/recruitment",
        headers=headers,
        json=recruitment_conf,
    )

    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["data"] == []


@patch("adopt.server.auth.verify_token")
def test_segments_progress_unauthorized_no_token(verify_mock):
    """Test segments progress returns 403 when no authentication token is provided."""
    _reset_db()
    org_id, _ = _user_and_study_setup()

    # Don't provide authorization header
    res = client.get(f"/{org_id}/studies/foo-study/segments-progress")
    assert res.status_code == 403  # FastAPI returns 403 for missing credentials


@patch("adopt.server.auth.verify_token")
def test_segments_progress_unauthorized_invalid_token(verify_mock):
    """Test segments progress returns 401 when an invalid token is provided."""
    from ..server.auth import AuthError

    _reset_db()
    org_id, _ = _user_and_study_setup()

    # Mock token verification to raise AuthError
    verify_mock.side_effect = AuthError({"code": "invalid_token", "description": "Invalid token"}, 401)

    headers = {"Authorization": "Bearer invalid-token"}
    res = client.get(f"/{org_id}/studies/foo-study/segments-progress", headers=headers)
    assert res.status_code == 401
