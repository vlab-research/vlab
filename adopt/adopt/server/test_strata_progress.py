"""Tests for `GET /{org_id}/studies/{slug}/strata-progress`.

The route explodes a `FACEBOOK_ADOPT` report into per-stratum rows, so the
fixtures here write those rows DIRECTLY rather than running a plan: what is
being asserted is the reading, and a plan run would drag in Meta, the budget
optimizer and a study's worth of confs to assert one dict shape.

The cases that matter, in order of what they protect:

* a report missing a fact is a DEFAULT, never a 500 -- `efficiency_weight` and
  the two counterfactuals postdate the earliest reports, so an old row is not a
  hypothetical;
* `history` is bounded on the handler as well as in `Query`, because
  `POST /mcp` calls the handler directly and the annotation enforces nothing
  there;
* no report at all is a 404 naming the SLUG, not `{"data": []}` -- an agent
  cannot tell an empty allocation from a study that has never been planned;
* the deviation from goal is computed on the RAW percentages, where the Go
  route rounds both first.
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"
os.environ["FACEBOOK_APP_ID"] = "test-app-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-app-secret"

from . import api_keys as ak  # noqa: E402
from .auth import DifferentAuthError, generate_api_token  # noqa: E402
from .server import app  # noqa: E402

client = TestClient(app)

USER = "test|strata-progress"
OTHER = "test|someone-else"
HEADERS = {"Authorization": "Bearer verysecret"}

# One report's worth of facts for one stratum, with everything `report_facts`
# can write present -- including the two counterfactuals, which `budget.py`
# appends only when a constraint binds.
FULL = {
    "current_price_per_participant": 1.25,
    "total_spent": 40.0,
    "lifetime_spent": 90.5,
    "desired_percentage": 0.5,
    "current_participants": 32,
    "current_percentage": 0.4,
    "current_budget": 12.5,
    "expected_participants": 48.75,
    "expected_percentage": 0.55,
    "efficiency_weight": 0.8,
    "counterfactual_spend_to_fill_sample": 220.0,
    "counterfactual_participants_with_unlimited_budget": 130.5,
}


@pytest.fixture(autouse=True)
def clean_db():
    _reset_db()
    ak.clear_api_key_cache()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    execute(db_conf, "insert into users (id) values (%s)", (OTHER,))
    yield
    ak.clear_api_key_cache()


@pytest.fixture(autouse=True)
def any_token_is_our_user():
    with patch("adopt.server.auth.verify_token") as m:
        m.return_value = {"sub": USER}
        yield m


@pytest.fixture
def org():
    org_id = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, "o"))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, USER),
    )
    return org_id


@pytest.fixture
def study(org):
    res = query(
        db_conf,
        """
        insert into studies (user_id, org_id, name, slug)
        values (%s, %s, %s, %s)
        returning id
        """,
        (USER, org, "foo study", "foo-study"),
        as_dict=True,
    )
    return str(list(res)[0]["id"])


def _report(study_id, details, created=None, report_type="FACEBOOK_ADOPT"):
    if created is None:
        execute(
            db_conf,
            "insert into adopt_reports (study_id, report_type, details)"
            " values (%s, %s, %s)",
            (study_id, report_type, json.dumps(details)),
        )
        return
    execute(
        db_conf,
        "insert into adopt_reports (study_id, report_type, details, created)"
        " values (%s, %s, %s, %s)",
        (study_id, report_type, json.dumps(details), created),
    )


def _get(org_id, slug="foo-study", **params):
    return client.get(
        f"/{org_id}/studies/{slug}/strata-progress", headers=HEADERS, params=params
    )


# --------------------------------------------------------------------------
# The shape
# --------------------------------------------------------------------------


def test_every_fact_the_report_holds_reaches_the_caller(org, study):
    """Including the four Go drops: total/lifetime spend, the efficiency
    weight and the counterfactuals. That is the reason this route exists on
    this service rather than the dashboard's being re-pointed at it."""
    _report(study, {"stratum_1": FULL})

    res = _get(org)

    assert res.status_code == 200, res.text
    (report,) = res.json()["data"]
    (stratum,) = report["strata"]

    assert stratum == {
        "id": "stratum_1",
        "current_participants": 32,
        "desired_percentage": 0.5,
        "current_percentage": 0.4,
        "expected_percentage": 0.55,
        "expected_participants": 48.75,
        "current_budget": 12.5,
        "current_price_per_participant": 1.25,
        "total_spent": 40.0,
        "lifetime_spent": 90.5,
        "efficiency_weight": 0.8,
        "counterfactual_spend_to_fill_sample": 220.0,
        "counterfactual_participants_with_unlimited_budget": 130.5,
        # 0.5 - 0.4 in binary floating point. Deliberately asserted as the raw
        # subtraction rather than 0.1: the Go route rounds to two places first
        # and this one does not, and that difference is the point.
        "percentage_deviation_from_goal": abs(0.5 - 0.4),
    }


def test_created_is_iso_8601_in_utc(org, study):
    _report(study, {"s": FULL})

    (report,) = _get(org).json()["data"]

    assert report["created"].endswith("+00:00")
    assert datetime.fromisoformat(report["created"]).tzinfo is not None


def test_strata_are_sorted_by_id_so_two_runs_can_be_compared(org, study):
    _report(study, {"b": FULL, "a": FULL, "c": FULL})

    (report,) = _get(org).json()["data"]

    assert [s["id"] for s in report["strata"]] == ["a", "b", "c"]


def test_deviation_is_computed_on_the_raw_percentages(org, study):
    """Go rounds `desired` and `current` to two places and subtracts the
    rounded pair, which is a display decision. Rounding here would mean an
    agent could not recover the real number from what it was given."""
    _report(
        study,
        {"s": {**FULL, "desired_percentage": 0.3334, "current_percentage": 0.3331}},
    )

    (report,) = _get(org).json()["data"]

    assert report["strata"][0]["percentage_deviation_from_goal"] == pytest.approx(
        0.0003
    )


# --------------------------------------------------------------------------
# Missing facts
# --------------------------------------------------------------------------


def test_a_report_missing_a_fact_defaults_rather_than_500ing(org, study):
    """A report is JSONB written by whatever `budget.py` was deployed at the
    time. `efficiency_weight` and the counterfactuals all postdate the earliest
    rows, so this is history, not a hypothetical."""
    _report(study, {"old": {"current_participants": 3, "current_budget": 7.0}})

    res = _get(org)

    assert res.status_code == 200, res.text
    (stratum,) = res.json()["data"][0]["strata"]

    assert stratum["current_participants"] == 3
    assert stratum["current_budget"] == 7.0
    assert stratum["efficiency_weight"] == 0.0
    assert stratum["total_spent"] == 0.0
    # Null, not zero: the optimizer did not compute one, and zero would read as
    # "nothing more to spend".
    assert stratum["counterfactual_spend_to_fill_sample"] is None


def test_a_fact_that_is_present_but_null_defaults_rather_than_500ing(org, study):
    """A stored `null` is not the same as an absent key, and only the absent one
    is what pydantic defaults. Without the explicit `is not None` filter this
    422s out of the model and reaches the caller as a 500 on a row nobody can
    fix -- the report is already written."""
    _report(study, {"s": {"current_budget": None, "current_participants": 2}})

    res = _get(org)

    assert res.status_code == 200, res.text
    (stratum,) = res.json()["data"][0]["strata"]
    assert stratum["current_budget"] == 0.0
    assert stratum["current_participants"] == 2


def test_a_missing_fact_is_logged_once_for_the_report(org, study, caplog):
    """Once per REPORT. A row written before a fact existed is missing it for
    every stratum in it, and a 200-stratum study would otherwise put 200
    identical lines in the log."""
    _report(study, {f"s{i}": {"current_participants": i} for i in range(5)})

    with caplog.at_level("WARNING"):
        assert _get(org).status_code == 200

    warnings = [r for r in caplog.records if "strata-progress" in r.getMessage()]
    assert len(warnings) == 1
    assert "efficiency_weight" in warnings[0].getMessage()


def test_a_fact_missing_from_only_one_stratum_is_still_reported(org, study, caplog):
    """The UNION of what each stratum lacks, not the intersection. A partially
    written report -- one stratum short of a fact the others carry -- is exactly
    the interesting case, and an intersection would say nothing about it."""
    _report(
        study,
        {
            "whole": FULL,
            "partial": {k: v for k, v in FULL.items() if k != "total_spent"},
        },
    )

    with caplog.at_level("WARNING"):
        assert _get(org).status_code == 200

    warnings = [r for r in caplog.records if "strata-progress" in r.getMessage()]
    assert len(warnings) == 1
    assert "total_spent" in warnings[0].getMessage()


def test_a_complete_report_logs_nothing(org, study, caplog):
    """The counterfactuals are absent from most healthy reports -- `budget.py`
    appends them only when a constraint binds -- so they are excluded from the
    check. A warning that fired on almost every request would be a warning
    nobody reads."""
    _report(
        study,
        {"s": {k: v for k, v in FULL.items() if not k.startswith("counterfactual_")}},
    )

    with caplog.at_level("WARNING"):
        assert _get(org).status_code == 200

    assert [r for r in caplog.records if "strata-progress" in r.getMessage()] == []


def test_an_unknown_fact_in_the_report_is_ignored_not_an_error(org, study):
    """A fact added to `report_facts` later must not 500 every reader that
    predates it -- the same rule as a missing one, in the other direction."""
    _report(study, {"s": {**FULL, "some_fact_from_the_future": 1.0}})

    res = _get(org)

    assert res.status_code == 200, res.text
    assert "some_fact_from_the_future" not in res.json()["data"][0]["strata"][0]


# --------------------------------------------------------------------------
# history
# --------------------------------------------------------------------------


def test_the_newest_report_is_the_only_one_by_default(org, study):
    now = datetime.now(timezone.utc)
    _report(study, {"s": {**FULL, "current_budget": 1.0}}, created=now - timedelta(2))
    _report(study, {"s": {**FULL, "current_budget": 2.0}}, created=now - timedelta(1))
    _report(study, {"s": {**FULL, "current_budget": 3.0}}, created=now)

    data = _get(org).json()["data"]

    assert len(data) == 1
    assert data[0]["strata"][0]["current_budget"] == 3.0


def test_history_returns_that_many_reports_newest_first(org, study):
    now = datetime.now(timezone.utc)
    for i, budget in enumerate([1.0, 2.0, 3.0]):
        _report(
            study,
            {"s": {**FULL, "current_budget": budget}},
            created=now - timedelta(days=3 - i),
        )

    data = _get(org, history=2).json()["data"]

    assert [r["strata"][0]["current_budget"] for r in data] == [3.0, 2.0]


def test_history_asking_for_more_than_exists_returns_what_exists(org, study):
    _report(study, {"s": FULL})

    assert len(_get(org, history=50).json()["data"]) == 1


@pytest.mark.parametrize("history", [0, -1, 201, 100000])
def test_history_out_of_range_is_422(org, study, history):
    _report(study, {"s": FULL})

    assert _get(org, history=history).status_code == 422


def test_history_is_bounded_by_the_handler_not_only_by_query(org, study):
    """`Query(ge=1, le=200)` only runs when FastAPI parses a query string, and
    `POST /mcp` calls this handler directly. Without the handler's own check a
    negative history would reach psycopg as `LIMIT -1`."""
    import asyncio

    from fastapi import HTTPException

    from .deps import User
    from .strata_progress import strata_progress_endpoint

    _report(study, {"s": FULL})

    with pytest.raises(HTTPException) as e:
        asyncio.run(strata_progress_endpoint(org, "foo-study", User(user_id=USER), -1))

    assert e.value.status_code == 422


# --------------------------------------------------------------------------
# Not found
# --------------------------------------------------------------------------


def test_a_study_with_no_report_is_404_naming_the_slug(org, study):
    """Not `{"data": []}`, which is what `segments-progress` and
    `cost-over-time` answer next door: an agent asking for the current
    allocation cannot tell "no plan has ever run" from "the plan allocated
    nothing", and those want opposite actions. The slug, not the id, because an
    agent is never handed a study id."""
    res = _get(org)

    assert res.status_code == 404
    assert res.json()["detail"] == "No adopt report found for study foo-study"


def test_reports_of_another_type_do_not_count_as_a_plan_run(org, study):
    """`plan_study` writes three report rows. Only `FACEBOOK_ADOPT` is the
    per-stratum one, and the other two have entirely different shapes."""
    _report(study, {"data": []}, report_type="cost_over_time")
    _report(study, {"data": []}, report_type="respondents_over_time")

    assert _get(org).status_code == 404


def test_another_studys_report_is_not_this_studys(org, study):
    """`adopt_reports` is one table for every study in the deployment, so the
    `study_id` predicate is the only thing keeping one study's allocation out of
    another's answer. Two studies in the SAME org, so nothing but that predicate
    can be doing the work."""
    res = query(
        db_conf,
        "insert into studies (user_id, org_id, name, slug)"
        " values (%s, %s, %s, %s) returning id",
        (USER, org, "other study", "other-study"),
        as_dict=True,
    )
    other_study = str(list(res)[0]["id"])
    _report(other_study, {"theirs": FULL})

    assert _get(org).status_code == 404

    _report(study, {"ours": FULL})
    (report,) = _get(org).json()["data"]
    assert [s["id"] for s in report["strata"]] == ["ours"]


def test_a_study_in_an_org_you_are_not_in_is_404(org, study):
    other_org = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (other_org, "x"))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (other_org, OTHER),
    )
    _report(study, {"s": FULL})

    res = _get(other_org)

    assert res.status_code == 404
    assert "Study not found" in res.json()["detail"]


def test_a_malformed_org_id_is_404_not_500(org, study):
    """`orgs_lookup.org_id` is UUID, so an unparseable org id blows up in the
    driver unless the handler rejects it first. It has to be indistinguishable
    from a real org the caller is not in: telling them apart would make this
    route an oracle for which org UUIDs exist."""
    _report(study, {"s": FULL})

    res = _get("not-a-uuid")

    assert res.status_code == 404, res.text
    assert "Organization not found" in res.json()["detail"]


def test_an_unknown_slug_is_404(org, study):
    _report(study, {"s": FULL})

    assert _get(org, slug="no-such-study").status_code == 404


# --------------------------------------------------------------------------
# Scopes, over the real middleware
# --------------------------------------------------------------------------


@pytest.fixture
def no_auth0():
    """Force the API-key half of `verify_tokens`, so a real scoped key is what
    authenticates rather than the stubbed Auth0 path."""
    with patch("adopt.server.auth.verify_token") as m:
        m.side_effect = DifferentAuthError("not an auth0 token")
        yield m


def test_a_stats_read_key_reaches_this_route(org, study, no_auth0):
    _report(study, {"s": FULL})
    token, _ = generate_api_token(user_id=USER, name="stats", scopes=["stats:read"])

    res = client.get(
        f"/{org}/studies/foo-study/strata-progress",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200, res.text
    assert res.json()["data"][0]["strata"][0]["id"] == "s"


def test_a_studies_read_key_is_denied_and_told_which_scope(org, study, no_auth0):
    """The same distinction `recruitment-stats` draws: study structure is not
    respondent counts and spend."""
    _report(study, {"s": FULL})
    token, _ = generate_api_token(user_id=USER, name="ro", scopes=["studies:read"])

    res = client.get(
        f"/{org}/studies/foo-study/strata-progress",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 403
    assert "stats:read" in res.json()["detail"]
