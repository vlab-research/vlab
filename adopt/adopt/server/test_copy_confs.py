"""Regression tests for `POST /{org_id}/studies/{slug}/copy-from`.

The endpoint had no tests at all, and it had a cross-tenant write bug: the
destination study was resolved with an unscoped `SELECT id FROM studies WHERE
slug = %s` taken straight off the request path, while `unique_slug` is
`UNIQUE(user_id, slug)` — per user, not global. `test_cannot_copy_into_another_users_study`
is the test that would have caught it.
"""

import os
import uuid
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from .server import app

client = TestClient(app)

OWNER = "test|copy-owner"
ATTACKER = "test|copy-attacker"

HEADERS = {"Authorization": "Bearer verysecret"}


def _create_user(user_id):
    execute(db_conf, "insert into users (id) values (%s)", (user_id,))


def _create_org(user_id, name):
    org_id = uuid.uuid4()
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, name))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, user_id),
    )
    return org_id


def _create_study(user_id, org_id, slug):
    q = """
    insert into studies (user_id, org_id, name, slug)
    values (%s, %s, %s, %s)
    returning id
    """
    res = query(db_conf, q, (user_id, org_id, slug, slug), as_dict=True)
    return list(res)[0]["id"]


def _add_conf(study_id, conf_type, conf):
    execute(
        db_conf,
        "insert into study_confs (study_id, conf_type, conf) values (%s, %s, %s)",
        (study_id, conf_type, conf),
    )


def _confs_of(study_id):
    res = query(
        db_conf,
        "select conf_type from study_confs where study_id = %s",
        (study_id,),
        as_dict=True,
    )
    return {r["conf_type"] for r in res}


@patch("adopt.server.auth.verify_token")
def test_copy_confs_happy_path(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": OWNER}

    _create_user(OWNER)
    org_id = _create_org(OWNER, "copy org")
    source_id = _create_study(OWNER, org_id, "source-study")
    dest_id = _create_study(OWNER, org_id, "dest-study")

    _add_conf(source_id, "creatives", '[{"name": "c1"}]')

    res = client.post(
        f"/{org_id}/studies/dest-study/copy-from",
        headers=HEADERS,
        json={"source_study_slug": "source-study"},
    )

    assert res.status_code == 201
    assert "creatives" in _confs_of(dest_id)


@patch("adopt.server.auth.verify_token")
def test_cannot_copy_into_another_users_study(verify_mock):
    """The cross-tenant write. Two users, the same destination slug, and the
    attacker does not own theirs — the pre-fix code resolved the slug globally
    and wrote the attacker's configuration into the owner's study."""
    _reset_db()

    _create_user(OWNER)
    owner_org = _create_org(OWNER, "owner org")
    victim_id = _create_study(OWNER, owner_org, "shared-slug")

    _create_user(ATTACKER)
    attacker_org = _create_org(ATTACKER, "attacker org")
    attacker_source = _create_study(ATTACKER, attacker_org, "attacker-source")
    _add_conf(attacker_source, "creatives", '[{"name": "malicious"}]')

    verify_mock.return_value = {"sub": ATTACKER}

    res = client.post(
        f"/{attacker_org}/studies/shared-slug/copy-from",
        headers=HEADERS,
        json={"source_study_slug": "attacker-source"},
    )

    assert res.status_code == 404
    # The important assertion is not the status code but that nothing landed.
    assert _confs_of(victim_id) == set()


@patch("adopt.server.auth.verify_token")
def test_copy_into_missing_study_is_404_not_500(verify_mock):
    """Previously the unscoped subselect yielded NULL into a NOT NULL column, so
    a typo'd destination surfaced as a 500 rather than a 404."""
    _reset_db()
    verify_mock.return_value = {"sub": OWNER}

    _create_user(OWNER)
    org_id = _create_org(OWNER, "copy org")
    source_id = _create_study(OWNER, org_id, "source-study")
    _add_conf(source_id, "creatives", '[{"name": "c1"}]')

    res = client.post(
        f"/{org_id}/studies/does-not-exist/copy-from",
        headers=HEADERS,
        json={"source_study_slug": "source-study"},
    )

    assert res.status_code == 404
