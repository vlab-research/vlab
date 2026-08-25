"""Tests for GET /{org_id}/studies/{slug}/ad-attributions.csv.

The endpoint exists to make one sentence true for a researcher:

    left-join your fly export on `ad_id` and you get your old metadata columns
    back, under the same names.

Which is only true because the frozen blob is key-for-key the dict the dotted
ref used to carry. So these tests care mostly about column names and about
which rows appear — the two things that would quietly break the join.
"""

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
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

from .csv_export import (
    ad_attributions_csv,
    ad_attributions_table,
    column_name,
    metadata_columns,
)
from .server import app

client = TestClient(app)

user_id = "test|111"


def _create_user(uid):
    execute(db_conf, "insert into users (id) values (%s)", (uid,))


def _create_org(uid, name):
    org_id = uuid.uuid4()
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, name))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, uid),
    )
    return org_id


def _create_study(uid, org_id, slug):
    q = """
    insert into studies (user_id, org_id, name, slug)
    values (%s, %s, %s, %s)
    returning id
    """
    res = query(db_conf, q, (uid, org_id, slug, slug), as_dict=True)
    return list(res)[0]["id"]


def _setup(slug="foo-study"):
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")
    study_id = _create_study(user_id, org_id, slug)
    headers = {"Authorization": "Bearer verysecret"}
    return org_id, study_id, headers


def _insert_attribution(study_id, ad_id, metadata, stratum_id="stratum-1"):
    q = """
    insert into ad_attributions
        (network, ad_id, study_id, stratum_id, creative_name, shortcode,
         metadata, resolved_from)
    values ('facebook', %s, %s, %s, 'Smiling', 'mnchweek', %s, 'ad_id')
    """
    execute(db_conf, q, (ad_id, study_id, stratum_id, json.dumps(metadata)))


def _parse(body):
    return list(csv.DictReader(io.StringIO(body)))


# ---------------------------------------------------------------------------
# The pure renderer
# ---------------------------------------------------------------------------


def test_metadata_keys_become_columns_under_their_own_names():
    # The join story depends on this exactly: the researcher's stratum
    # vocabulary passes through untouched.
    rows = [
        {
            "ad_id": "ad-1",
            "network": "facebook",
            "created": datetime(2026, 8, 16, tzinfo=timezone.utc),
            "metadata": {"creative": "Smiling", "gender": "women", "form": "mnchweek"},
        }
    ]

    parsed = _parse(ad_attributions_csv(rows))

    assert list(parsed[0].keys()) == [
        "ad_id",
        "network",
        "ref_token",
        "creative",
        "gender",
        "form",
        "created",
    ]
    assert parsed[0]["creative"] == "Smiling"
    assert parsed[0]["gender"] == "women"
    assert parsed[0]["form"] == "mnchweek"


def test_ad_id_leads_and_created_trails():
    rows = [{"ad_id": "ad-1", "network": "facebook", "created": None, "metadata": {"g": "w"}}]
    header = ad_attributions_csv(rows).splitlines()[0]
    assert header.startswith("ad_id,network,ref_token,")
    assert header.endswith(",created")


def test_columns_are_the_union_across_rows():
    # Uniform within a study in practice, but a conf edit mid-flight leaves
    # rows frozen under both shapes -- and append-only means both survive. A
    # renderer that trusted the first row would drop the newer keys silently.
    rows = [
        {"ad_id": "ad-1", "network": "facebook", "created": None, "metadata": {"gender": "women"}},
        {"ad_id": "ad-2", "network": "facebook", "created": None, "metadata": {"gender": "men", "Age": "old"}},
    ]

    assert metadata_columns(rows) == ["gender", "Age"]

    parsed = _parse(ad_attributions_csv(rows))
    assert parsed[0]["Age"] == ""
    assert parsed[1]["Age"] == "old"


def test_a_metadata_key_that_collides_with_a_row_column_is_prefixed():
    # Two columns of the same name is the kind of thing nobody notices until
    # the analysis is already wrong.
    rows = [
        {
            "ad_id": "ad-1",
            "network": "facebook",
            "created": None,
            "metadata": {"ad_id": "not-the-real-one", "gender": "women"},
        }
    ]

    assert column_name("ad_id") == "metadata_ad_id"
    assert column_name("gender") == "gender"

    parsed = _parse(ad_attributions_csv(rows))
    assert parsed[0]["ad_id"] == "ad-1"
    assert parsed[0]["metadata_ad_id"] == "not-the-real-one"


def test_empty_study_still_emits_a_header():
    assert ad_attributions_csv([]).strip() == "ad_id,network,ref_token,created"


def test_values_needing_quoting_survive_the_round_trip():
    rows = [
        {
            "ad_id": "ad-1",
            "network": "facebook",
            "created": None,
            "metadata": {"place": 'Bauchi, "North"', "note": "a\nb"},
        }
    ]

    parsed = _parse(ad_attributions_csv(rows))
    assert parsed[0]["place"] == 'Bauchi, "North"'
    assert parsed[0]["note"] == "a\nb"


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_endpoint_returns_csv_for_the_study(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _setup()

    _insert_attribution(study_id, "ad-1", {"creative": "Smiling", "gender": "women"})

    res = client.get(f"/{org_id}/studies/foo-study/ad-attributions.csv", headers=headers)

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "foo-study-ad-attributions.csv" in res.headers["content-disposition"]

    parsed = _parse(res.text)
    assert len(parsed) == 1
    assert parsed[0]["ad_id"] == "ad-1"
    assert parsed[0]["network"] == "facebook"
    assert parsed[0]["creative"] == "Smiling"
    assert parsed[0]["gender"] == "women"


@patch("adopt.server.auth.verify_token")
def test_endpoint_includes_ads_that_no_longer_exist_on_facebook(verify_mock):
    """The append-only rule, visible at the export.

    Reconciliation deletes ads that fall out of the desired set, but page posts
    persist and can be reshared indefinitely, so respondents keep arriving from
    deleted ads. A CSV of only live ads would silently lack rows the researcher
    needs, and those respondents would look unattributed.

    Nothing in the read path filters on liveness -- there is no liveness column
    to filter on, by design -- so this test pins that no one adds one.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _setup()

    _insert_attribution(study_id, "still-running", {"gender": "women"})
    _insert_attribution(study_id, "long-deleted", {"gender": "men"})

    res = client.get(f"/{org_id}/studies/foo-study/ad-attributions.csv", headers=headers)

    assert res.status_code == 200
    ad_ids = {r["ad_id"] for r in _parse(res.text)}
    assert ad_ids == {"still-running", "long-deleted"}


@patch("adopt.server.auth.verify_token")
def test_endpoint_is_scoped_to_the_requested_study(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")
    mine = _create_study(user_id, org_id, "mine")
    theirs = _create_study(user_id, org_id, "theirs")
    headers = {"Authorization": "Bearer verysecret"}

    _insert_attribution(mine, "my-ad", {"gender": "women"})
    _insert_attribution(theirs, "their-ad", {"gender": "men"})

    res = client.get(f"/{org_id}/studies/mine/ad-attributions.csv", headers=headers)

    assert res.status_code == 200
    assert {r["ad_id"] for r in _parse(res.text)} == {"my-ad"}


@patch("adopt.server.auth.verify_token")
def test_endpoint_404s_for_a_study_the_user_does_not_own(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    _create_user(user_id)
    org_id = _create_org(user_id, "test org")

    other = "test|222"
    _create_user(other)
    other_org = _create_org(other, "other org")
    other_study = _create_study(other, other_org, "not-mine")
    _insert_attribution(other_study, "secret-ad", {"gender": "women"})

    headers = {"Authorization": "Bearer verysecret"}
    res = client.get(f"/{org_id}/studies/not-mine/ad-attributions.csv", headers=headers)

    assert res.status_code == 404


@patch("adopt.server.auth.verify_token")
def test_endpoint_returns_a_header_only_csv_for_a_study_with_no_ads(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, _, headers = _setup()

    res = client.get(f"/{org_id}/studies/foo-study/ad-attributions.csv", headers=headers)

    assert res.status_code == 200
    assert res.text.strip() == "ad_id,network,ref_token,created"


@patch("adopt.server.auth.verify_token")
def test_the_csv_columns_match_the_frozen_blob_keys(verify_mock):
    """The invariant that makes the join honest, end to end.

    Whatever keys were frozen at ad-creation time are exactly the non-row
    columns the researcher gets -- including `creative` and `form`, which exist
    only because the frozen blob is the ref's dict rather than stratum.metadata.
    """
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _setup()

    frozen = {
        "creative": "Static English - Girls",
        "form": "mnchweek",
        "gender": "women",
        "Age": "Like Parents",
        "Region": "South East",
    }
    _insert_attribution(study_id, "ad-1", frozen)

    res = client.get(f"/{org_id}/studies/foo-study/ad-attributions.csv", headers=headers)

    parsed = _parse(res.text)
    columns = set(parsed[0].keys()) - {"ad_id", "network", "ref_token", "created"}

    assert columns == set(frozen)
    for key, value in frozen.items():
        assert parsed[0][key] == value


# ---------------------------------------------------------------------------
# The same rendering as a table
# ---------------------------------------------------------------------------


def test_the_table_and_the_file_show_the_same_shape():
    """One definition, two renderings.

    The columns are a union across rows in first-seen order, so a table
    deriving them separately would show a different shape from the file
    downloaded seconds later.
    """
    rows = [
        {"ad_id": "ad-1", "network": "facebook", "created": None, "metadata": {"gender": "women"}},
        {"ad_id": "ad-2", "network": "facebook", "created": None, "metadata": {"gender": "men", "Age": "old"}},
    ]

    table = ad_attributions_table(rows)
    parsed = _parse(ad_attributions_csv(rows))

    assert table["columns"] == list(parsed[0].keys())
    assert table["rows"] == parsed


def test_the_table_carries_every_row_including_deleted_ads():
    rows = [
        {"ad_id": "live", "network": "facebook", "created": None, "metadata": {"gender": "women"}},
        {"ad_id": "long-deleted", "network": "facebook", "created": None, "metadata": {"gender": "men"}},
    ]

    table = ad_attributions_table(rows)

    assert [r["ad_id"] for r in table["rows"]] == ["live", "long-deleted"]


def test_an_empty_study_still_names_its_columns():
    table = ad_attributions_table([])

    assert table["columns"] == ["ad_id", "network", "ref_token", "created"]
    assert table["rows"] == []


@patch("adopt.server.auth.verify_token")
def test_the_json_endpoint_returns_the_same_rows_as_the_csv(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _setup()

    _insert_attribution(study_id, "ad-1", {"creative": "Smiling", "gender": "women"})

    res = client.get(f"/{org_id}/studies/foo-study/ad-attributions", headers=headers)
    csv_res = client.get(
        f"/{org_id}/studies/foo-study/ad-attributions.csv", headers=headers
    )

    table = res.json()["data"]

    assert table["columns"] == list(_parse(csv_res.text)[0].keys())
    assert table["rows"] == _parse(csv_res.text)


@patch("adopt.server.auth.verify_token")
def test_the_json_endpoint_is_scoped_to_the_requested_study(verify_mock):
    _reset_db()
    verify_mock.return_value = {"sub": user_id}
    org_id, study_id, headers = _setup("mine")
    theirs = _create_study(user_id, org_id, "theirs")

    _insert_attribution(study_id, "ad-mine", {"gender": "women"})
    _insert_attribution(theirs, "ad-theirs", {"gender": "men"})

    res = client.get(f"/{org_id}/studies/mine/ad-attributions", headers=headers)

    assert [r["ad_id"] for r in res.json()["data"]["rows"]] == ["ad-mine"]
