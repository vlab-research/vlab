"""Tests for GET /{org_id}/optimize/{slug}/errors.

This endpoint owns the derivation query from planning/study-errors-surfacing.md
("current open errors" = latest event per (source, fingerprint), filtered to
error/warning severities inside the recency window), so the derivation
semantics are tested here: run_ok supersession, recency age-out (the
dead-man's switch), first_seen, severity filtering, and org-scoped ownership.
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from .db import get_study_errors
from .server import app

client = TestClient(app)

user_id = "test|111"


def _create_user(user_id):
    q = "insert into users (id) values (%s)"
    execute(db_conf, q, (user_id,))


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


def _user_and_study_setup(slug="foo-study"):
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")
    study_id = _create_study(user_id, org_id, slug)
    headers = {"Authorization": "Bearer verysecret"}
    return org_id, study_id, headers


def _insert_event(
    study_id,
    event_type,
    fingerprint,
    severity,
    message="boom",
    details=None,
    occurred_at=None,
):
    q = """
    insert into study_run_events
        (study_id, source, run_id, event_type, fingerprint, severity, message, details, occurred_at)
    values (%s, 'inference', 'run-1', %s, %s, %s, %s, %s, coalesce(%s, now()))
    """
    execute(
        db_conf,
        q,
        (
            study_id,
            event_type,
            fingerprint,
            severity,
            message,
            json.dumps(details) if details is not None else None,
            occurred_at,
        ),
    )


@patch("adopt.server.auth.verify_token")
def test_get_errors_empty_when_no_events(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, _, headers = _user_and_study_setup()

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    assert res.status_code == 200
    assert res.json() == {"errors": []}


@patch("adopt.server.auth.verify_token")
def test_get_errors_returns_open_run_error(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _user_and_study_setup()

    _insert_event(
        study_id,
        "run_error",
        "inference:run",
        "error",
        message="study foo: reduce: boom",
        details={"stage": "reduce"},
    )

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    assert res.status_code == 200
    errors = res.json()["errors"]
    assert len(errors) == 1
    e = errors[0]
    assert e["source"] == "inference"
    assert e["fingerprint"] == "inference:run"
    assert e["severity"] == "error"
    assert e["message"] == "study foo: reduce: boom"
    assert e["details"] == {"stage": "reduce"}
    assert "last_seen" in e
    assert "first_seen" in e


@patch("adopt.server.auth.verify_token")
def test_get_errors_first_seen_is_oldest_error_in_group(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _user_and_study_setup()

    # Two occurrences of the same problem: first_seen approximates how long
    # this has been broken (the incident's "broken for ~3 days" visibility).
    old = datetime.now(timezone.utc) - timedelta(minutes=80)
    _insert_event(
        study_id, "run_error", "inference:run", "error", occurred_at=old
    )
    _insert_event(study_id, "run_error", "inference:run", "error")

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    errors = res.json()["errors"]
    assert len(errors) == 1
    # py3.10 fromisoformat has no 'Z' support; normalize.
    first_seen = datetime.fromisoformat(errors[0]["first_seen"].replace("Z", "+00:00"))
    last_seen = datetime.fromisoformat(errors[0]["last_seen"].replace("Z", "+00:00"))
    assert first_seen < last_seen
    assert abs((first_seen - old).total_seconds()) < 5


@patch("adopt.server.auth.verify_token")
def test_get_errors_run_ok_supersedes_prior_run_error(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _user_and_study_setup()

    # The incident's resolution path: a failing run, then a healthy run on the
    # shared fingerprint closes the error (latest event per group wins).
    older = datetime.now(timezone.utc) - timedelta(minutes=30)
    _insert_event(
        study_id, "run_error", "inference:run", "error", occurred_at=older
    )
    _insert_event(study_id, "run_ok", "inference:run", "")

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    assert res.json() == {"errors": []}


@patch("adopt.server.auth.verify_token")
def test_get_errors_ages_out_stale_errors(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _user_and_study_setup()

    # Dead-man's switch: an error not re-emitted within the 90-min recency
    # window ages out, even with no closing event.
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    _insert_event(
        study_id, "run_error", "inference:run", "error", occurred_at=stale
    )

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    assert res.json() == {"errors": []}


@patch("adopt.server.auth.verify_token")
def test_get_errors_includes_warnings_and_orders_errors_first(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _user_and_study_setup()

    newer = datetime.now(timezone.utc)
    older = datetime.now(timezone.utc) - timedelta(minutes=10)
    _insert_event(
        study_id,
        "extraction_warning",
        "inference:extraction:source=Fly",
        "warning",
        message="data source not in SourceVariableMapping (skipped): Fly",
        occurred_at=newer,
    )
    _insert_event(
        study_id, "run_error", "inference:run", "error", occurred_at=older
    )

    res = client.get(f"/{org_id}/optimize/foo-study/errors", headers=headers)

    errors = res.json()["errors"]
    assert [e["severity"] for e in errors] == ["error", "warning"]


@patch("adopt.server.auth.verify_token")
def test_get_errors_404_for_unknown_study(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")
    headers = {"Authorization": "Bearer verysecret"}

    res = client.get(f"/{org_id}/optimize/no-such-study/errors", headers=headers)

    assert res.status_code == 404


@patch("adopt.server.auth.verify_token")
def test_get_errors_scoped_to_owning_org(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}

    # Study belongs to a different user/org; the JWT user must not see it.
    other_user = "test|222"
    _create_user(other_user)
    other_org = _create_org(other_user, "other org")
    other_study = _create_study(other_user, other_org, "other-study")
    _insert_event(other_study, "run_error", "inference:run", "error")

    _create_user(user_id)
    my_org = _create_org(user_id, "my org")
    headers = {"Authorization": "Bearer verysecret"}

    # The other org's study errors are not visible through my org path.
    res = client.get(
        f"/{my_org}/optimize/other-study/errors", headers=headers
    )
    assert res.status_code == 404


@patch("adopt.server.db.query")
def test_get_study_errors_degrades_gracefully_when_table_missing(query_mock):
    # Migration not yet applied in some env: the read must degrade to
    # "no errors", never break the dashboard with a 500.
    query_mock.side_effect = psycopg.errors.UndefinedTable(
        'relation "study_run_events" does not exist'
    )

    assert get_study_errors("any-study-id") == []
