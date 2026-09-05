"""Tests for POST /{org_id}/studies on the conf service.

The point of this endpoint is that an API key can now bring a study into
existence and then configure it without a human in the dashboard
(planning/agent-study-authoring.md §2.3). So the test that matters most is
`test_created_study_is_immediately_configurable`: it creates a study through
the new endpoint and then drives a real conf endpoint against it. That is the
direct regression test for the `org_id` bug in `create_campaign_for_user`
(Appendix A.1) — a study row with a NULL `org_id` would be created happily
here and then be invisible to every conf route, because they all reach a study
through `JOIN orgs_lookup ol ON ol.org_id = s.org_id AND s.org_id = %s`.
"""

import os
import uuid
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from ..study_conf import GeneralConf
from .deps import User, get_current_user
from .server import app as real_app
from .studies import router

user_id = "test|111"
other_user_id = "test|222"

# The router is mounted on its own app here rather than on `server.app`,
# because wiring it into server.py is a separate change. `conf_client` below
# drives the real app, so the interop test is not testing a stub.
app = FastAPI()
app.include_router(router)

# Whose key the request is made with. Set by `_as`.
_acting_user = user_id


def _as(uid):
    global _acting_user
    _acting_user = uid


async def _override_current_user():
    return User(user_id=_acting_user)


app.dependency_overrides[get_current_user] = _override_current_user

client = TestClient(app)
conf_client = TestClient(real_app)

HEADERS = {"Authorization": "Bearer verysecret"}


def _create_user(uid):
    execute(db_conf, "insert into users (id) values (%s)", (uid,))


def _create_org(name, *members):
    org_id = uuid.uuid4()
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, name))
    for uid in members:
        execute(
            db_conf,
            "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
            (org_id, uid),
        )
    return org_id


def _setup():
    _reset_db()
    _as(user_id)
    _create_user(user_id)
    return _create_org("test org", user_id)


def _study_rows():
    return list(
        query(
            db_conf,
            "select id, name, slug, user_id, org_id, credentials_key,"
            " credentials_entity from studies",
            as_dict=True,
        )
    )


def _post(org_id, name):
    return client.post(f"/{org_id}/studies", headers=HEADERS, json={"name": name})


# --------------------------------------------------------------------------
# happy path
# --------------------------------------------------------------------------


def test_create_study_returns_201_with_the_go_response_shape():
    org_id = _setup()

    res = _post(org_id, "My First Study")

    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["name"] == "My First Study"
    assert data["slug"] == "my-first-study"
    assert uuid.UUID(data["id"])
    # Go returns created.UnixMilli(); a plausible millisecond timestamp is
    # 13 digits. Guard against accidentally emitting seconds.
    assert data["createdAt"] > 1_500_000_000_000


def test_create_study_writes_org_id_and_leaves_credentials_key_null():
    org_id = _setup()

    _post(org_id, "My First Study")

    rows = _study_rows()
    assert len(rows) == 1
    row = rows[0]
    # THE regression this endpoint exists to avoid. See the module docstring.
    assert row["org_id"] == org_id
    assert row["user_id"] == user_id
    # Appendix A.2: the column is vestigial, the FK is satisfied vacuously,
    # and Facebook credentials come from the general conf instead.
    assert row["credentials_key"] is None
    assert row["credentials_entity"] == "facebook_ad_user"


def test_slug_is_gosimple_compatible():
    org_id = _setup()

    res = _post(org_id, "Café & Straße — Nigeria 2024!")

    assert res.status_code == 201, res.text
    # Recorded from gosimple/slug v1.12.0; test_slugify.py is where the full
    # conformance suite lives, this just proves the endpoint uses it.
    assert res.json()["data"]["slug"] == "cafe-and-strasse-nigeria-2024"


def test_name_is_stored_untrimmed_like_go():
    org_id = _setup()

    res = _post(org_id, "  Spaced Out  ")

    assert res.status_code == 201, res.text
    # Go passes req.StudyName straight through to the insert; only the slug
    # sees a trimmed string. unique_name is on the raw column, so this
    # distinction is load-bearing.
    assert res.json()["data"]["name"] == "  Spaced Out  "
    assert res.json()["data"]["slug"] == "spaced-out"
    assert _study_rows()[0]["name"] == "  Spaced Out  "


# --------------------------------------------------------------------------
# the whole point: the study is usable straight away
# --------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_created_study_is_immediately_configurable(verify_mock):
    org_id = _setup()
    verify_mock.return_value = {"sub": user_id}

    res = _post(org_id, "Agent Created Study")
    assert res.status_code == 201, res.text
    slug = res.json()["data"]["slug"]

    conf = GeneralConf(
        name="foo",
        opt_window=48,
        ad_account="234",
        credentials_key="facebook",
        credentials_entity="facebook",
    ).model_dump()

    # A study created with a NULL org_id would 500 here ("Could not find study
    # for user ...") rather than 201, because create_study_conf's subselect
    # joins on s.org_id = %s.
    res = conf_client.post(
        f"/{org_id}/studies/{slug}/confs/general", headers=HEADERS, json=conf
    )
    assert res.status_code == 201, res.text

    res = conf_client.get(f"/{org_id}/studies/{slug}/confs/general", headers=HEADERS)
    assert res.status_code == 200, res.text
    assert res.json()["data"] == conf


# --------------------------------------------------------------------------
# uniqueness
# --------------------------------------------------------------------------


def test_duplicate_name_is_409():
    org_id = _setup()

    assert _post(org_id, "Same Name").status_code == 201

    res = _post(org_id, "Same Name")
    assert res.status_code == 409
    assert res.json()["detail"] == "The name is already in use."
    assert len(_study_rows()) == 1


def test_different_name_that_slugifies_the_same_is_409():
    org_id = _setup()

    assert _post(org_id, "Smoke Study").status_code == 201

    # Different name, so unique_name is satisfied; identical slug, so
    # unique_slug is not. Go returns 409 for both, and so do we — but the
    # message says why, because "The name is already in use" is baffling when
    # the name demonstrably is not.
    res = _post(org_id, "smoke   study!!")
    assert res.status_code == 409
    assert res.json()["detail"].startswith("The name is already in use")
    assert "smoke-study" in res.json()["detail"]
    assert len(_study_rows()) == 1


def test_uniqueness_is_per_user_not_per_org():
    org_id = _setup()
    _create_user(other_user_id)
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, other_user_id),
    )

    assert _post(org_id, "Shared Org Study").status_code == 201

    # unique_name/unique_slug are UNIQUE(user_id, ...), so a second member of
    # the same org may reuse the name. Two studies then share a slug within
    # one org; that is pre-existing behaviour of the Go endpoint and of the
    # schema, not something this port introduces, and the conf routes resolve
    # by (user, org, slug) so they still address them apart.
    _as(other_user_id)
    res = _post(org_id, "Shared Org Study")
    assert res.status_code == 201, res.text
    assert len(_study_rows()) == 2


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------


def test_blank_name_is_400():
    org_id = _setup()

    for name in ["", "   ", "\t\n"]:
        res = _post(org_id, name)
        assert res.status_code == 400, (name, res.text)
        assert res.json()["detail"] == "The name cannot be empty."

    assert _study_rows() == []


def test_name_over_300_bytes_is_400():
    org_id = _setup()

    assert _post(org_id, "a" * 300).status_code == 201

    res = _post(org_id, "a" * 301)
    assert res.status_code == 400
    assert res.json()["detail"] == "The name cannot be larger than 300 characters."


def test_the_300_cap_counts_bytes_not_characters():
    org_id = _setup()

    # Go's `len(req.StudyName)` is a byte count. 150 two-byte characters is
    # exactly at the cap; 151 is over it, even though it is only 151
    # characters. We reproduce Go rather than the message, so that a name the
    # dashboard rejects is rejected here too.
    assert len("ñ".encode("utf8")) == 2
    assert _post(org_id, "ñ" * 150).status_code == 201
    assert _post(org_id, "ñ" * 151).status_code == 400


def test_name_with_no_usable_characters_is_400():
    org_id = _setup()

    # Deliberate divergence from Go, which would write a row with slug "".
    # See the comment in studies.py: such a study has no addressable URL.
    for name in ["😀😀", "!!!", "---"]:
        res = _post(org_id, name)
        assert res.status_code == 400, (name, res.text)
        assert "letter or number" in res.json()["detail"]

    assert _study_rows() == []


def test_missing_name_field_is_422():
    org_id = _setup()

    res = client.post(f"/{org_id}/studies", headers=HEADERS, json={})
    assert res.status_code == 422


# --------------------------------------------------------------------------
# authorisation
# --------------------------------------------------------------------------


def test_cannot_create_in_an_org_you_do_not_belong_to():
    _setup()
    other_org = _create_org("someone elses org")

    res = _post(other_org, "Trespassing Study")

    assert res.status_code == 404, res.text
    # Nothing was written. The INSERT selects from orgs_lookup, so a
    # non-member matches no rows rather than being rejected after the fact.
    assert _study_rows() == []


def test_membership_is_checked_for_the_acting_user_not_any_user():
    _setup()
    _create_user(other_user_id)
    other_org = _create_org("other org", other_user_id)

    # user_id is not in other_org, though other_user_id is.
    res = _post(other_org, "Trespassing Study")
    assert res.status_code == 404, res.text
    assert _study_rows() == []

    _as(other_user_id)
    assert _post(other_org, "Legitimate Study").status_code == 201


def test_malformed_org_id_is_404_not_500():
    _setup()

    res = _post("not-a-uuid", "Some Study")

    # orgs_lookup.org_id is UUID; without the guard this is an
    # InvalidTextRepresentation from the driver and a 500.
    assert res.status_code == 404, res.text
    assert _study_rows() == []
