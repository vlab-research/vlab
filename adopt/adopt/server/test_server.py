import json
import os
import uuid
from datetime import datetime
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

from fastapi.testclient import TestClient

from ..db import execute, query
from ..study_conf import GeneralConf, SimpleRecruitment, WebDestination

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"

from .server import app

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


def _conf_create_and_get_happy_path(path, dat):

    _create_user(user_id)
    org_id = _create_org(user_id, "test org")

    _create_study(user_id, org_id, "foo-study")

    token = "verysecret"

    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/{org_id}/studies/foo-study/confs/{path}", headers=headers, json=dat
    )

    assert res.status_code == 201

    res_dat = res.json()
    assert "data" in res_dat

    res = client.get(f"/{org_id}/studies/foo-study/confs/{path}", headers=headers)
    res_dat = res.json()

    assert res_dat["data"] == dat


@patch("adopt.server.server.verify_token")
def test_server_create_and_get_general_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = GeneralConf(
        name="foo",
        objective="test",
        optimization_goal="test",
        destination_type="app",
        page_id="123",
        min_budget=1,
        opt_window=48,
        ad_account="234",
    )

    dat = conf.dict()
    _conf_create_and_get_happy_path("general", dat)


@patch("adopt.server.server.verify_token")
def test_server_create_and_get_destinations_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = [
        WebDestination(name="foo", url_template="http://foo.com/{ref}"),
        WebDestination(name="bar", url_template="http://bar.com/{ref}"),
    ]

    dat = [c.dict() for c in conf]
    _conf_create_and_get_happy_path("destinations", dat)


@patch("adopt.server.server.verify_token")
def test_server_create_and_get_recruitment_conf(verify_mock):
    _reset_db()

    verify_mock.return_value = {"sub": user_id}

    conf = SimpleRecruitment(
        ad_campaign_name="foo",
        start_date=_dt(1),
        end_date=_dt(2),
        budget=10,
        max_sample=100,
    )
    dat = json.loads(conf.json())
    _conf_create_and_get_happy_path("recruitment", dat)
