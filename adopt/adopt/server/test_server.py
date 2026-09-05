import json

import pytest
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
def test_server_rejects_invalid_destination_conf_with_422(verify_mock):
    # `FlyWhatsAppDestination.shortcode_must_survive_the_entry_pattern` raises
    # `InvalidConfigError` -- a cross-field validator on a single conf section,
    # so it fires here at write time rather than hours later when
    # `load_basics` assembles the whole `StudyConf` on the optimize cron. Built
    # as a raw dict (not `FlyWhatsAppDestination(...)`) because constructing
    # the model directly raises client-side before the request is ever sent;
    # the point of this test is what the SERVER does with a bad payload.
    #
    # Before InvalidConfigError derived from ValueError (study_conf.py:930),
    # this validator's message never reached the caller: pydantic does not
    # wrap a raised BaseException into a ValidationError, so it propagated
    # past Starlette's exception middleware and the caller got a bare 500 with
    # no body. Guards against that regressing.
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    dat = [
        {
            "type": "whatsapp",
            "name": "whatsapp",
            "initial_shortcode": "mnch week",  # space: unsafe per the entry regex
            "welcome_message": "Hi",
            "whatsapp_phone_number": "15419202635",
        }
    ]

    org_id, headers = _user_and_study_setup()

    res = client.post(
        f"/{org_id}/studies/foo-study/confs/destinations", headers=headers, json=dat
    )

    assert res.status_code == 422
    assert "initial_shortcode" in res.text


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


# ---------------------------------------------------------------------------
# Unknown fields on a write are a 422 that names the field.
#
# Until 2026-09-05 every conf model ran on pydantic's default, `extra="ignore"`,
# so a misspelled key was accepted and dropped: `201 Created`, and the field
# simply did not exist in the stored conf. That is invisible to a dashboard user
# (the form supplies the names) and is the likeliest failure mode there is for
# an agent authoring JSON. The nine POST routes now annotate the strict twins in
# `study_conf_strict.py`. See planning/conf-extra-fields.md.
#
# `VALID_CONF_BODIES` is doing double duty and the second job is the important
# one: these bodies mirror what the dashboard actually sends (verified
# field-for-field against the forms under
# dashboard/src/pages/StudyConfPage/forms/), so the happy-path test below is the
# regression guard that `extra="forbid"` did not break the dashboard. Add a
# required field to a model and it fails here, which is the point.
# ---------------------------------------------------------------------------

VALID_CONF_BODIES = {
    "general": {
        "name": "foo",
        "credentials_key": "facebook",
        "credentials_entity": "facebook",
        "ad_account": "234",
        "opt_window": 48,
    },
    "recruitment": {
        "ad_campaign_name": "camp",
        "objective": "OUTCOME_ENGAGEMENT",
        "optimization_goal": "CONVERSATIONS",
        "min_budget": 100,
        "budget": 1000,
        "max_sample": 500,
        "start_date": "2022-01-01T00:00",
        "end_date": "2022-03-01T00:00",
        "incentive_per_respondent": 0,
        "efficiency_weight": 1,
    },
    "destinations": [
        {
            "type": "web",
            "name": "site",
            "url_template": "https://x.example/{ref}",
        }
    ],
    "creatives": [
        {
            "name": "creative-a",
            "destination": "site",
            "template": {"object_story_spec": {"page_id": "1"}},
            "template_campaign": "tmpl",
        }
    ],
    "audiences": [{"name": "aud", "subtype": "CUSTOM"}],
    "variables": [
        {
            "name": "age",
            "properties": ["age"],
            "levels": [
                {
                    "name": "18_24",
                    "template_campaign": "tmpl",
                    "template_adset": "tmpl-adset",
                    "facebook_targeting": {"age_min": 18, "age_max": 24},
                    "quota": 0.5,
                }
            ],
        }
    ],
    "strata": [
        {
            "id": "age_18_24",
            "quota": 1.0,
            "creatives": ["creative-a"],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {"age_min": 18},
            "question_targeting": {
                "op": "equal",
                "vars": [
                    {"type": "variable", "value": "age"},
                    {"type": "constant", "value": "18_24"},
                ],
            },
            "metadata": {"age": "18_24"},
        }
    ],
    "data-sources": [
        {
            "name": "fly",
            "source": "typeform",
            "credentials_key": "typeform",
            "config": {"survey_name": "hpv"},
        }
    ],
    "inference-data": {
        "data_sources": {
            "fly": {
                "extraction_confs": [
                    {
                        "location": "variable",
                        "key": "age",
                        "name": "age",
                        "functions": [{"function": "identity", "params": None}],
                        "value_type": "categorical",
                        "aggregate": "last",
                    }
                ],
                "user_variable": "userid",
            }
        }
    },
}

# Every route, so a new one cannot be added without a decision about strictness.
CONF_PATHS = list(VALID_CONF_BODIES)


def _post_conf(org_id, headers, path, body):
    return client.post(
        f"/{org_id}/studies/foo-study/confs/{path}", headers=headers, json=body
    )


def _with_extra_key(body, key, value="typo"):
    """The same body with one unknown key, at the top level of the conf object.

    A list-bodied section gets the key on its first element, which is the top
    level of the model that section is a list of.
    """
    if isinstance(body, list):
        return [{**body[0], key: value}, *body[1:]]
    return {**body, key: value}


@pytest.mark.parametrize("path", CONF_PATHS)
@patch("adopt.server.auth.verify_token")
def test_every_conf_route_accepts_the_body_the_dashboard_sends(verify_mock, path):
    """The regression guard for `extra="forbid"`.

    If forbidding extras ever starts rejecting a shape the dashboard sends, it
    fails here rather than in production on someone's study.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    res = _post_conf(org_id, headers, path, VALID_CONF_BODIES[path])

    assert res.status_code == 201, res.text


@pytest.mark.parametrize("path", CONF_PATHS)
@patch("adopt.server.auth.verify_token")
def test_every_conf_route_rejects_an_unknown_top_level_key(verify_mock, path):
    """422, and the response body names the key.

    Naming it is the whole value of the change: "extra inputs are not permitted"
    with no key would leave an agent no better off than the silent drop did.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    body = _with_extra_key(VALID_CONF_BODIES[path], "definitely_not_a_field")
    res = _post_conf(org_id, headers, path, body)

    assert res.status_code == 422, res.text
    assert "definitely_not_a_field" in res.text


# The four sections that nest a model inside another model, and a typo placed
# at the deepest point each one reaches. `extra="forbid"` is per-class and does
# not inherit into fields, so these would still be dropped silently if only the
# outer class were strict -- and a hand-written targeting tree or extraction
# conf is exactly where the typing, and the typos, happen.
#
# The other five sections nest nothing: `general`, `recruitment` and
# `destinations` are flat, `creatives.template` is a Meta blob typed
# `Dict[str, Any]`, and `data-sources.config` is `Any`. Their coverage is the
# top-level test above.
NESTED_TYPO_BODIES = {
    "audiences": [
        {
            "name": "aud",
            "subtype": "CUSTOM",
            "question_targeting": {
                "op": "equal",
                "vars": [{"type": "variable", "value": "age", "vlaue": "typo"}],
            },
        }
    ],
    "variables": [
        {
            "name": "age",
            "properties": ["age"],
            "levels": [
                {
                    "name": "18_24",
                    "template_campaign": "tmpl",
                    "template_adset": "tmpl-adset",
                    "facebok_targeting": {"age_min": 18},
                    "facebook_targeting": {"age_min": 18},
                    "quota": 0.5,
                }
            ],
        }
    ],
    "strata": [
        {
            "id": "age_18_24",
            "quota": 1.0,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "equal",
                "vars": [{"type": "variable", "value": "age", "vlaue": "typo"}],
            },
        }
    ],
    "inference-data": {
        "data_sources": {
            "fly": {
                "extraction_confs": [
                    {
                        "location": "variable",
                        "key": "age",
                        "name": "age",
                        "functions": [{"function": "identity", "parms": None}],
                        "value_type": "categorical",
                        "aggregate": "last",
                    }
                ]
            }
        }
    },
}

NESTED_TYPO_KEYS = {
    "audiences": "vlaue",
    "variables": "facebok_targeting",
    "strata": "vlaue",
    "inference-data": "parms",
}


@pytest.mark.parametrize("path", list(NESTED_TYPO_BODIES))
@patch("adopt.server.auth.verify_token")
def test_a_conf_route_rejects_an_unknown_key_nested_inside_the_body(verify_mock, path):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    res = _post_conf(org_id, headers, path, NESTED_TYPO_BODIES[path])

    assert res.status_code == 422, res.text
    assert NESTED_TYPO_KEYS[path] in res.text


@patch("adopt.server.auth.verify_token")
def test_a_destination_posted_without_a_type_is_a_422(verify_mock):
    """The strict destination union drops the legacy `messenger` default.

    `_default_missing_destination_type` fills in "messenger" so that the 45
    stored confs predating the `type` field keep LOADING. Nothing POSTed today
    predates the field, so a missing `type` on a write is an author who forgot
    it, and quietly giving them a Messenger destination is the same silent
    mis-resolution the discriminator was added to stop.
    planning/conf-extra-fields.md §6 question 2.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    res = _post_conf(
        org_id,
        headers,
        "destinations",
        [
            {
                "name": "mess",
                "initial_shortcode": "hpv",
                "welcome_message": "Hi",
                "button_text": "Start",
            }
        ],
    )

    assert res.status_code == 422, res.text
    assert "type" in res.text


@patch("adopt.server.auth.verify_token")
def test_a_recruitment_conf_written_without_a_tag_is_still_accepted(verify_mock):
    """Unlike destinations, and deliberately.

    Every recruitment conf in existence is untagged -- `extra="ignore"` dropped
    the `type` the dashboard sent before it was ever stored -- and the
    dashboard's edit path re-POSTs what `GET /confs` returned. Requiring the
    tag would 422 every edit of every study.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    body = dict(VALID_CONF_BODIES["recruitment"])
    assert "type" not in body

    res = _post_conf(org_id, headers, "recruitment", body)

    assert res.status_code == 201, res.text
    # The tag is filled in on the way to storage, which is what will eventually
    # make the shape inference removable.
    assert res.json()["data"]["conf"]["type"] == "simple"


@patch("adopt.server.auth.verify_token")
def test_an_over_specified_recruitment_conf_is_rejected_rather_than_downgraded(
    verify_mock,
):
    """`arms` and `destinations` together used to mean "pipeline", silently.

    Union order won and `destinations` was dropped as an extra, so a study
    configured as a destination experiment could run as a pipeline one and
    nothing said so (planning/agent-study-authoring.md §11.4 item 3).
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    res = _post_conf(
        org_id,
        headers,
        "recruitment",
        {
            "ad_campaign_name_base": "camp",
            "objective": "OUTCOME_ENGAGEMENT",
            "optimization_goal": "CONVERSATIONS",
            "min_budget": 100,
            "budget_per_arm": 1000,
            "max_sample_per_arm": 500,
            "start_date": "2022-01-01T00:00",
            "end_date": "2022-03-01T00:00",
            "arms": 3,
            "recruitment_days": 7,
            "offset_days": 7,
            "destinations": ["wa", "mess"],
        },
    )

    assert res.status_code == 422, res.text
    assert "destinations" in res.text


@patch("adopt.server.auth.verify_token")
def test_a_retired_field_on_a_stored_conf_does_not_block_re_saving_it(verify_mock):
    """`destination_type` was required on all three recruitment arms until
    d382000c (2026-08-30), so every recruitment conf older than that has it in
    its stored JSON -- and the dashboard re-POSTs stored JSON verbatim when you
    edit a study. Without the retired-key allowance, "extend this study's end
    date" would 422 on the existing corpus.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    body = {**VALID_CONF_BODIES["recruitment"], "destination_type": "MESSENGER"}
    res = _post_conf(org_id, headers, "recruitment", body)

    assert res.status_code == 201, res.text
    # Accepted and dropped -- exactly what has happened to it since the day the
    # field was removed. The list of such keys is closed; a typo'd one is not
    # on it and is still a 422 (see test_study_conf_strict.py).
    assert "destination_type" not in res.json()["data"]["conf"]


@pytest.mark.parametrize(
    "url_segment,stored_type",
    [("data-sources", "data_sources"), ("inference-data", "inference_data")],
)
@patch("adopt.server.auth.verify_token")
def test_a_hyphenated_conf_type_can_be_read_back_by_the_url_that_wrote_it(
    verify_mock, url_segment, stored_type
):
    """`POST /confs/data-sources` stores `data_sources`, and `GET` used to pass
    its URL segment straight to the query -- so the only URL that could write a
    section was the one URL that could not read it back
    (planning/agent-study-authoring.md §11.4 item 5). Both spellings work now:
    the underscore is what `GET /confs` returns as a key, and that caller was
    the only one that worked before.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, headers = _user_and_study_setup()

    assert _post_conf(org_id, headers, url_segment, VALID_CONF_BODIES[url_segment])

    for spelling in (url_segment, stored_type):
        res = client.get(
            f"/{org_id}/studies/foo-study/confs/{spelling}", headers=headers
        )
        assert res.status_code == 200, res.text
        assert res.json()["data"] is not None
