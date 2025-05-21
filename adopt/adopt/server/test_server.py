import json
import os
import uuid
from datetime import datetime
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch, ANY
import pandas as pd
from fastapi.testclient import TestClient

from ..db import execute, query
from ..facebook.update import Instruction
from ..study_conf import GeneralConf, WebDestination, StratumConf
from ..test_study_conf import _simple
from ..recruitment_data import AdPlatformRecruitmentStats, RecruitmentStats

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from .auth import DifferentAuthError
from .server import OptimizeInstruction, OptimizeReport, app

client = TestClient(app)

user_id = "test|111"


def _dt(day, month=1, year=2022, hour=0, minute=0):
    return datetime(year, month, day, hour=hour, minute=minute)


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

    _create_study(user_id, org_id, "foo-study")

    token = "verysecret"

    headers = {"Authorization": f"Bearer {token}"}

    return org_id, headers


def _conf_create_and_get_happy_path(path, dat):
    org_id, headers = _user_and_study_setup()

    res = client.post(
        f"/{org_id}/studies/foo-study/confs/{path}", headers=headers, json=dat
    )

    assert res.status_code == 201

    res_dat = res.json()
    assert "data" in res_dat

    res = client.get(f"/{org_id}/studies/foo-study/confs/{path}", headers=headers)
    res_dat = res.json()

    assert res_dat["data"] == dat

    return org_id, headers


@patch("adopt.server.auth.verify_token")
def test_server_create_and_get_general_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = GeneralConf(
        name="foo",
        opt_window=48,
        ad_account="234",
        credentials_key="facebook",
        credentials_entity="facebook",
    )

    dat = conf.model_dump()
    _conf_create_and_get_happy_path("general", dat)


@patch("adopt.server.auth.verify_token")
def test_server_create_and_get_destinations_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = [
        WebDestination(type="web", name="foo", url_template="http://foo.com/{ref}"),
        WebDestination(type="web", name="bar", url_template="http://bar.com/{ref}"),
    ]

    dat = [c.model_dump() for c in conf]
    _conf_create_and_get_happy_path("destinations", dat)


@patch("adopt.server.auth.verify_token")
def test_server_create_and_get_recruitment_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = _simple()
    dat = json.loads(conf.model_dump_json())
    _conf_create_and_get_happy_path("recruitment", dat)


@patch("adopt.server.auth.verify_token")
def test_server_get_all_study_confs(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = GeneralConf(
        name="foo",
        opt_window=48,
        ad_account="234",
        credentials_key="facebook",
        credentials_entity="facebook",
    )

    dat = conf.model_dump()
    org_id, headers = _conf_create_and_get_happy_path("general", dat)

    res = client.get(f"/{org_id}/studies/foo-study/confs", headers=headers)
    res_dat = res.json()
    assert "general" in res_dat["data"]
    assert res_dat["data"]["general"]["name"] == "foo"


@patch("adopt.server.server.run_study_opt")
@patch("adopt.server.auth.verify_token")
def test_optimize_study_returns_instructions(verify_mock, run_study_opt):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    run_study_opt.return_value = [Instruction("foo", "bar", {})]

    org_id, headers = _user_and_study_setup()

    res = client.get(f"/{org_id}/optimize/foo-study", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["data"] == [
        {"node": "foo", "action": "bar", "params": {}, "id": None}
    ]


@patch("adopt.server.server.run_study_opt")
@patch("adopt.server.auth.verify_token")
def test_optimize_study_returns_errors_if_any_optimization_error(
    verify_mock, run_study_opt
):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    run_study_opt.side_effect = Exception("foo error")

    org_id, headers = _user_and_study_setup()

    res = client.get(f"/{org_id}/optimize/foo-study", headers=headers)
    assert res.status_code == 500
    res_data = res.json()
    assert res_data == {"detail": "foo error"}


@patch("adopt.server.server.run_single_instruction")
@patch("adopt.server.auth.verify_token")
def test_optimize_instruction_returns_report(verify_mock, run_single_instruction):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}

    instruction = OptimizeInstruction(node="foo", action="bar", params={})

    run_single_instruction.return_value = OptimizeReport(
        timestamp="10:00",
        instruction=instruction,
    )

    org_id, headers = _user_and_study_setup()

    req_data = instruction.model_dump()

    res = client.post(
        f"/{org_id}/optimize/foo-study/instruction", headers=headers, json=req_data
    )

    assert res.status_code == 201
    res_data = res.json()
    assert res_data["data"] == {
        "timestamp": "10:00",
        "instruction": {"node": "foo", "action": "bar", "params": {}, "id": None},
    }


@patch("adopt.server.server.run_single_instruction")
@patch("adopt.server.auth.verify_token")
def test_optimize_instruction_returns_error_in_running(
    verify_mock, run_single_instruction
):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}

    instruction = OptimizeInstruction(node="foo", action="bar", params={})

    run_single_instruction.side_effect = Exception("foo error")

    org_id, headers = _user_and_study_setup()

    req_data = instruction.model_dump()

    res = client.post(
        f"/{org_id}/optimize/foo-study/instruction", headers=headers, json=req_data
    )

    assert res.status_code == 500
    res_data = res.json()
    assert res_data == {"detail": "foo error"}


@patch("adopt.server.server.fetch_current_data")
@patch("adopt.server.auth.verify_token")
async def test_get_current_data_returns_data(verify_mock, fetch_current_data_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}

    # Create sample inference data with ISO format timestamps
    test_data = pd.DataFrame(
        {
            "user_id": ["user1", "user2"],
            "variable": ["var1", "var2"],
            "value": [10.0, 20.0],
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00", "2024-01-02T00:00:00"]),
            "updated": pd.to_datetime(["2024-01-01T00:00:00", "2024-01-02T00:00:00"]),
        }
    )
    fetch_current_data_mock.return_value = test_data

    org_id, headers = _user_and_study_setup()

    res = client.get(f"/{org_id}/optimize/foo-study/current-data", headers=headers)
    assert res.status_code == 200
    res_data = res.json()

    # Verify the returned data structure
    assert len(res_data["data"]) == 2
    assert all(
        key in res_data["data"][0]
        for key in ["user_id", "variable", "value", "timestamp", "updated"]
    )
    assert res_data["data"][0]["value"] == 10.0
    assert res_data["data"][1]["value"] == 20.0
    # Verify timestamp format
    assert "2024-01-01" in res_data["data"][0]["timestamp"]
    assert "2024-01-02" in res_data["data"][1]["timestamp"]


@patch("adopt.server.auth.verify_token")
def test_api_key_creation_and_use(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    req_data = {"name": "foo-name"}
    res = client.post("/users/api-key", headers=headers, json=req_data)

    assert res.status_code == 201
    res_data = res.json()

    assert res_data["data"]["name"] == "foo-name"

    verify_mock.side_effect = DifferentAuthError("foo")

    # Test fake auth to ensure server-side auth rejecting
    api_token = "fake"
    headers = {"Authorization": f"Bearer {api_token}"}

    conf = GeneralConf(
        name="foo",
        opt_window=48,
        ad_account="234",
        credentials_key="facebook",
        credentials_entity="facebook",
    )

    dat = conf.model_dump()

    res = client.post(
        f"/{org_id}/studies/foo-study/confs/general", headers=headers, json=dat
    )

    assert res.status_code == 401

    # Test returned token to ensure it is working
    api_token = res_data["data"]["token"]
    headers = {"Authorization": f"Bearer {api_token}"}

    res = client.post(
        f"/{org_id}/studies/foo-study/confs/general", headers=headers, json=dat
    )

    assert res.status_code == 201


@patch("adopt.budget.calculate_strata_stats")
@patch("adopt.server.server.get_latest_adopt_report")
@patch("adopt.recruitment_data.get_recruitment_data")
@patch("adopt.server.auth.verify_token")
def test_get_recruitment_stats_returns_data(
    verify_mock,
    get_recruitment_data_mock,
    get_latest_adopt_report_mock,
    calculate_strata_stats_mock,
):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    get_recruitment_data_mock.return_value = []
    get_latest_adopt_report_mock.return_value = {
        "stratum1": 100
    }  # Mock respondents data

    # Create mock complete stats using RecruitmentStats
    mock_stats = {
        "stratum1": RecruitmentStats(
            spend=1000.0,
            frequency=2.0,
            reach=25000,
            cpm=20.0,
            unique_clicks=1000,
            unique_ctr=0.02,
            respondents=100,
            price_per_respondent=10.0,
            incentive_cost=1000.0,
            total_cost=2000.0,
            conversion_rate=0.1,
        )
    }
    calculate_strata_stats_mock.return_value = mock_stats

    org_id, headers = _user_and_study_setup()
    # Post general conf first
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
    # Post recruitment conf using _simple()
    recruitment_conf = json.loads(_simple().model_dump_json())
    client.post(
        f"/{org_id}/studies/foo-study/confs/recruitment",
        headers=headers,
        json=recruitment_conf,
    )
    # Post strata conf using StratumConf model
    stratum = StratumConf(
        id="stratum1",
        name="Test Stratum",
        quota=100,
        creatives=[],
        audiences=[],
        excluded_audiences=[],
        facebook_targeting={},
        metadata={},
    )
    strata_conf = [stratum.model_dump()]
    client.post(
        f"/{org_id}/studies/foo-study/confs/strata",
        headers=headers,
        json=strata_conf,
    )
    res = client.get(f"/{org_id}/studies/foo-study/recruitment-stats", headers=headers)

    assert res.status_code == 200
    res_data = res.json()
    assert "data" in res_data

    # Convert the mock stats to the expected response format using model_dump
    expected_data = {
        stratum_id: stats.model_dump() for stratum_id, stats in mock_stats.items()
    }
    assert res_data["data"] == expected_data


@patch("adopt.server.auth.verify_token")
def test_get_recruitment_stats_returns_404_for_missing_study(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()
    res = client.get(
        f"/{org_id}/studies/non-existent/recruitment-stats", headers=headers
    )
    assert res.status_code == 404
    assert "Study not found" in res.json()["detail"]


@patch("adopt.budget.calculate_strata_stats")
@patch("adopt.server.server.fetch_current_data")
@patch("adopt.recruitment_data.get_recruitment_data")
@patch("adopt.server.auth.verify_token")
def test_get_recruitment_stats_returns_404_for_missing_strata(
    verify_mock,
    get_recruitment_data_mock,
    fetch_current_data_mock,
    calculate_strata_stats_mock,
):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    get_recruitment_data_mock.return_value = []
    fetch_current_data_mock.return_value = pd.DataFrame()
    org_id, headers = _user_and_study_setup()
    # Post general conf first
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
    # Post recruitment conf using _simple(), but no strata conf
    recruitment_conf = json.loads(_simple().model_dump_json())
    client.post(
        f"/{org_id}/studies/foo-study/confs/recruitment",
        headers=headers,
        json=recruitment_conf,
    )
    res = client.get(f"/{org_id}/studies/foo-study/recruitment-stats", headers=headers)
    assert res.status_code == 404
    assert "No strata found" in res.json()["detail"]


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
