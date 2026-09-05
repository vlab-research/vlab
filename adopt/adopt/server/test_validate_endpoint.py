"""Tests for `POST /{org}/studies/{slug}/validate` (`server/validate.py`).

The library's own behaviour is covered exhaustively in
`adopt/authoring/test_validate.py`; these tests are about the wrapper. What can
break here, and is therefore what is asserted:

- the stored confs actually reach the validator, in the shape it expects;
- the overlay replaces sections rather than merging into them;
- an invalid study is a 200 with `valid: false`, not a 4xx;
- **nothing is written** — the whole promise of the endpoint;
- a study the caller cannot see is a 404, not "everything is missing";
- the scope is `studies:read`, on a POST.

The app is assembled the way `server.py` assembles it (scope enforcement added
first, so it is innermost) rather than importing `server.app`, so a failure
here points at this router and not at some other route's import.
"""

import os
import uuid
from copy import deepcopy
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from typing import List, Optional
from unittest.mock import patch

import orjson
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from ..authoring.test_validate import valid_study  # noqa: E402
from . import api_keys as ak  # noqa: E402
from . import validate as validate_module  # noqa: E402
from .auth import DifferentAuthError, generate_api_token  # noqa: E402

USER = "test|validate"
OTHER_USER = "test|validate-other"
SLUG = "foo-study"


def _make_app() -> FastAPI:
    app = FastAPI()
    # First-added is innermost, exactly as in server.py.
    ak.add_scope_enforcement(app)
    app.include_router(validate_module.router)
    return app


client = TestClient(_make_app(), raise_server_exceptions=False)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_db():
    _reset_db()
    ak.clear_api_key_cache()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    execute(db_conf, "insert into users (id) values (%s)", (OTHER_USER,))
    yield
    ak.clear_api_key_cache()


@pytest.fixture(autouse=True)
def no_auth0():
    """Every token here is a vlab API key. Auth0 verification would hit a JWKS."""
    with patch("adopt.server.auth.verify_token") as m:
        m.side_effect = DifferentAuthError("not an auth0 token")
        yield m


def _org(*members) -> str:
    org_id = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, org_id))
    for uid in members:
        execute(
            db_conf,
            "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
            (org_id, uid),
        )
    return org_id


def _study(user_id: str, org_id: str, slug: str) -> str:
    res = query(
        db_conf,
        "insert into studies (user_id, org_id, name, slug)"
        " values (%s, %s, %s, %s) returning id",
        (user_id, org_id, slug, slug),
        as_dict=True,
    )
    return list(res)[0]["id"]


def _write_confs(study_id: str, sections: dict) -> None:
    for conf_type, conf in sections.items():
        execute(
            db_conf,
            "insert into study_confs (study_id, conf_type, conf)"
            " values (%s, %s, %s)",
            (study_id, conf_type, orjson.dumps(conf).decode("utf8")),
        )


def _key(user_id: str = USER, scopes: Optional[List[str]] = None, name: str = "k"):
    token, _ = generate_api_token(user_id=user_id, name=name, scopes=scopes)
    return {"Authorization": f"Bearer {token}"}


def _setup(sections: Optional[dict] = None, scopes: Optional[List[str]] = None):
    """An org, a study with `sections` stored, and a key for the caller."""
    org_id = _org(USER)
    study_id = _study(USER, org_id, SLUG)
    if sections is not None:
        _write_confs(study_id, sections)
    return org_id, study_id, _key(scopes=scopes)


def _conf_row_count() -> int:
    return list(query(db_conf, "select count(*) as n from study_confs", as_dict=True))[
        0
    ]["n"]


def _post(org_id, headers, body=None, slug=SLUG):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return client.post(f"/{org_id}/studies/{slug}/validate", **kwargs)


# --------------------------------------------------------------------------
# Stored-only
# --------------------------------------------------------------------------


def test_a_complete_stored_study_validates_with_no_body():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers)

    assert res.status_code == 200
    report = res.json()["data"]
    assert report == {"valid": True, "errors": [], "warnings": []}


def test_an_empty_body_object_is_the_same_as_no_body():
    org_id, _, headers = _setup(valid_study())

    assert _post(org_id, headers, {}).json() == _post(org_id, headers).json()
    assert _post(org_id, headers, {"sections": {}}).json() == _post(
        org_id, headers
    ).json()


def test_a_study_with_no_confs_at_all_reports_every_required_section():
    org_id, _, headers = _setup({})

    res = _post(org_id, headers)

    assert res.status_code == 200
    report = res.json()["data"]
    assert report["valid"] is False
    assert {e["section"] for e in report["errors"]} == {
        "general",
        "recruitment",
        "destinations",
        "creatives",
        "audiences",
        "strata",
    }


def test_an_invalid_stored_study_is_200_with_valid_false():
    # A report, not a rejection: the caller's request was fine, the answer is
    # just "no". A 4xx would mean they asked wrongly.
    sections = deepcopy(valid_study())
    sections["strata"][0]["creatives"] = ["does-not-exist"]
    org_id, _, headers = _setup(sections)

    res = _post(org_id, headers)

    assert res.status_code == 200
    report = res.json()["data"]
    assert report["valid"] is False
    assert [e["code"] for e in report["errors"]] == ["stratum.creative_unknown"]
    assert report["errors"][0]["path"] == "strata[0].creatives[0]"


def test_warnings_do_not_make_a_study_invalid_over_the_wire():
    sections = deepcopy(valid_study())
    sections["strata"][0]["audiences"] = ["built-in-ads-manager"]
    org_id, _, headers = _setup(sections)

    report = _post(org_id, headers).json()["data"]

    assert report["valid"] is True
    assert [w["code"] for w in report["warnings"]] == ["stratum.audience_unknown"]


def test_only_the_latest_row_per_conf_type_is_validated():
    # study_confs is append-only and a POST is the update (§1.1). The endpoint
    # must see what a reader sees, which is the newest row per conf type.
    org_id, study_id, headers = _setup(valid_study())

    superseded = deepcopy(valid_study()["strata"])
    superseded[0]["creatives"] = ["does-not-exist"]
    _write_confs(study_id, {"strata": superseded})

    report = _post(org_id, headers).json()["data"]
    assert [e["code"] for e in report["errors"]] == ["stratum.creative_unknown"]


def test_the_response_carries_the_known_gaps():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers)

    gaps = res.json()["known_gaps"]
    assert any("Meta-side" in g for g in gaps)


# --------------------------------------------------------------------------
# Overlay
# --------------------------------------------------------------------------


def test_a_proposed_section_is_validated_against_the_stored_rest():
    org_id, _, headers = _setup(valid_study())

    proposed = deepcopy(valid_study()["strata"])
    proposed[0]["creatives"] = ["does-not-exist"]

    res = _post(org_id, headers, {"sections": {"strata": proposed}})

    assert res.status_code == 200
    report = res.json()["data"]
    assert report["valid"] is False
    assert [e["code"] for e in report["errors"]] == ["stratum.creative_unknown"]

    # And the stored study is still fine — the overlay is not a write.
    assert _post(org_id, headers).json()["data"]["valid"] is True


def test_a_proposal_can_fix_a_broken_stored_study():
    # The forward direction, and the one an agent actually wants: check the fix
    # before writing it.
    sections = deepcopy(valid_study())
    sections["strata"][0]["creatives"] = ["does-not-exist"]
    org_id, _, headers = _setup(sections)

    assert _post(org_id, headers).json()["data"]["valid"] is False

    res = _post(org_id, headers, {"sections": {"strata": valid_study()["strata"]}})
    assert res.json()["data"]["valid"] is True


def test_the_overlay_replaces_a_section_rather_than_merging_into_it():
    # Whole-section replacement, because that is what a POST does. If this were
    # a deep merge, dropping a stratum in a proposal would leave it in place
    # and the report would describe a study no write could produce.
    org_id, _, headers = _setup(valid_study())

    one_stratum = [deepcopy(valid_study()["strata"][0])]
    one_stratum[0]["creatives"] = ["frowning"]

    res = _post(org_id, headers, {"sections": {"strata": one_stratum}})

    # "smiling" is now unused, which is not an error; the point is that the
    # second stored stratum is gone rather than merged back in.
    assert res.json()["data"]["valid"] is True


def test_an_explicit_null_section_asks_what_breaks_without_it():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers, {"sections": {"recruitment": None}})

    report = res.json()["data"]
    assert report["valid"] is False
    assert [(e["code"], e["section"]) for e in report["errors"]] == [
        ("section.missing", "recruitment")
    ]


def test_a_proposed_section_that_does_not_parse_is_reported_not_rejected():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers, {"sections": {"strata": [{"id": "men"}]}})

    assert res.status_code == 200
    assert all(
        e["code"] == "section.invalid" for e in res.json()["data"]["errors"]
    )


def test_a_body_that_is_not_a_sections_object_is_a_422():
    # The request itself being wrong, as opposed to the study being wrong.
    org_id, _, headers = _setup(valid_study())

    assert _post(org_id, headers, {"sections": "not an object"}).status_code == 422


def test_an_unknown_section_name_in_a_proposal_is_a_warning():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers, {"sections": {"stratas": []}})

    report = res.json()["data"]
    assert report["valid"] is True
    assert [w["code"] for w in report["warnings"]] == ["section.unrecognized"]


# --------------------------------------------------------------------------
# It writes nothing
# --------------------------------------------------------------------------


def test_validating_writes_no_study_confs_row():
    # The endpoint's whole promise. study_confs is append-only, so a validate
    # that wrote would silently become the study's current configuration.
    org_id, _, headers = _setup(valid_study())
    before = _conf_row_count()

    _post(org_id, headers)
    _post(org_id, headers, {"sections": {"strata": valid_study()["strata"]}})
    _post(org_id, headers, {"sections": {"strata": [{"id": "broken"}]}})

    assert _conf_row_count() == before


def test_validating_writes_nothing_anywhere():
    # Broader than the row count above, because `GET /{org}/optimize/{slug}` —
    # the closest pre-existing thing to a "preview" — writes an adopt_reports
    # row and two time-series reports (§11.3). This one does not.
    org_id, _, headers = _setup(valid_study())

    def _counts():
        return {
            table: list(
                query(db_conf, f"select count(*) as n from {table}", as_dict=True)
            )[0]["n"]
            for table in ("study_confs", "adopt_reports", "studies", "credentials")
        }

    before = _counts()
    _post(org_id, headers)
    assert _counts() == before


# --------------------------------------------------------------------------
# Study lookup
# --------------------------------------------------------------------------


def test_a_missing_study_is_a_404():
    org_id, _, headers = _setup(valid_study())

    res = _post(org_id, headers, slug="no-such-study")

    assert res.status_code == 404
    assert "no-such-study" in res.json()["detail"]


def test_another_users_study_is_a_404_not_an_empty_report():
    # Without the get_study_id call, get_all_study_confs would return {} and the
    # caller would get a 200 saying "every section is missing" for a study that
    # exists and is not theirs — leaking nothing, but answering the wrong
    # question and telling them to write confs they cannot write.
    other_org = _org(OTHER_USER)
    other_study = _study(OTHER_USER, other_org, "private-study")
    _write_confs(other_study, valid_study())

    _org(USER)
    headers = _key(name="mine")

    res = _post(other_org, headers, slug="private-study")
    assert res.status_code == 404


def test_a_malformed_org_id_is_a_404_not_a_500():
    _, _, headers = _setup(valid_study())

    res = _post("not-a-uuid", headers)

    assert res.status_code == 404
    assert "Organization not found" in res.json()["detail"]


# --------------------------------------------------------------------------
# Auth and scopes
# --------------------------------------------------------------------------


def test_no_token_is_a_403():
    org_id, _, _ = _setup(valid_study())

    assert client.post(f"/{org_id}/studies/{SLUG}/validate").status_code == 403


def test_a_studies_read_key_may_validate_despite_the_post():
    # The point of the `validate` special case in `required_scope`: this writes
    # nothing, so a read-only key must be able to check its own study.
    org_id, _, _ = _setup(valid_study())
    headers = _key(scopes=["studies:read"], name="readonly")

    assert _post(org_id, headers).status_code == 200


def test_a_studies_write_key_may_validate_because_write_implies_read():
    org_id, _, _ = _setup(valid_study())
    headers = _key(scopes=["studies:write"], name="writer")

    assert _post(org_id, headers).status_code == 200


def test_a_key_without_studies_scope_is_denied():
    org_id, _, _ = _setup(valid_study())
    headers = _key(scopes=["meta:read", "optimize:read"], name="narrow")

    res = _post(org_id, headers)

    assert res.status_code == 403
    assert "studies:read" in res.json()["detail"]


def test_a_key_with_no_scopes_claim_is_unrestricted():
    # The Phase 0 compatibility rule: no scopes claim means unrestricted, so no
    # existing key breaks when a route is added.
    org_id, _, headers = _setup(valid_study(), scopes=None)

    assert _post(org_id, headers).status_code == 200


def test_the_scope_is_pinned_to_read_regardless_of_method():
    assert ak.required_scope("POST", f"/{uuid.uuid4()}/studies/x/validate") == (
        "studies:read"
    )
    # And the neighbouring paths are untouched by the special case.
    assert ak.required_scope("POST", f"/{uuid.uuid4()}/studies/x/confs") == (
        "studies:write"
    )
