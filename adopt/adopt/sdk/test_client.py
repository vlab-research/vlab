"""Tests for `sdk/client.py`.

WHERE THE BOUNDARY IS

Most of these drive the REAL FastAPI app through Starlette's `TestClient`,
injected as the client's `session`. That is the whole reason `session` is a
constructor argument: a route that changes its path, its status or its response
shape breaks these tests, where a mocked `requests` would have let it through.
It also means the round trip that matters most -- POST a section, read it back,
and find the two comparable -- is exercised against the real
`model_dump()`/`orjson` storage path rather than against an assumption about
it.

The error-rendering tests use a fake session instead, because the shapes worth
covering (Meta's `detail` object, a non-JSON body from an ingress) cannot be
produced by this app at all.
"""

import os
import uuid
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ..db import execute

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from ..server.server import app  # noqa: E402
from .client import (  # noqa: E402
    ConflictError,
    NotAuthenticatedError,
    NotFoundError,
    ServerError,
    TransportError,
    UnprocessableError,
    VlabClient,
    VlabHTTPError,
)

USER = "test|sdk-client"

MESSENGER = {
    "type": "messenger",
    "name": "main",
    "initial_shortcode": "abc123",
    "welcome_message": "hello",
    "button_text": "Start",
}


@pytest.fixture(autouse=True)
def clean_db():
    _reset_db()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    yield


@pytest.fixture(autouse=True)
def any_token_is_our_user():
    """`verify_token` is the Auth0 half; stubbing it is how every server test
    in this repo authenticates without a JWKS fetch."""
    with patch("adopt.server.auth.verify_token") as m:
        m.return_value = {"sub": USER}
        yield m


@pytest.fixture
def client():
    return VlabClient(
        api_key="token",
        base_url="http://testserver",
        session=TestClient(app, raise_server_exceptions=False),
    )


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


# ---------------------------------------------------------------------------
# Studies
# ---------------------------------------------------------------------------


def test_create_study_returns_the_slug(client, org):
    study = client.create_study(org, "HPV Nigeria 2026")
    assert study["slug"] == "hpv-nigeria-2026"
    assert study["name"] == "HPV Nigeria 2026"
    assert study["id"]


def test_the_slug_is_not_predictable_and_must_be_read_off_the_response(client, org):
    """Apostrophes are DELETED, not replaced. A client computing the slug
    itself would compute `nandan-s-study` and address nothing."""
    assert client.create_study(org, "Nandan's study")["slug"] == "nandans-study"


def test_a_duplicate_name_is_a_conflict_error(client, org):
    client.create_study(org, "HPV")
    with pytest.raises(ConflictError) as e:
        client.create_study(org, "HPV")
    assert e.value.status_code == 409


def test_an_org_you_are_not_in_is_a_not_found_error(client):
    with pytest.raises(NotFoundError):
        client.create_study(str(uuid.uuid4()), "HPV")


def test_confs_on_a_fresh_study_is_an_empty_dict(client, org):
    """`agent-api.md` §2.3 says this raises a 500 for a study with no confs.
    It does not: `db.get_all_study_confs` builds a dict comprehension over an
    empty result set, and its `except IndexError` is unreachable. Pinned here
    because `vlab pull` on a new study depends on it."""
    slug = client.create_study(org, "HPV")["slug"]
    assert client.get_confs(org, slug) == {}


def test_a_section_round_trips_through_the_real_storage_path(client, org):
    """POST, read back, and find the two comparable AFTER normalisation.

    The property the whole diff rests on, and it is not plain equality: the
    server stores `model_dump()`, which fills `additional_metadata` and
    `ref_mode` that the body never carried. `normalise_section` is what makes
    the two comparable, and this exercises it against the real
    `model_dump()` and the real orjson serialisation rather than against an
    assumption about them.
    """
    from .study import normalise_section

    slug = client.create_study(org, "HPV")["slug"]

    client.post_conf(org, slug, "destinations", [MESSENGER])
    stored = client.get_confs(org, slug)["destinations"]

    assert stored != [MESSENGER]  # defaults were filled in
    assert normalise_section("destinations", stored) == normalise_section(
        "destinations", [MESSENGER]
    )


def test_a_datetime_survives_the_round_trip_as_a_comparable_string(client, org):
    """`mode="json"` in `model_dump_section` exists for this: the stored value
    went through orjson, so `start_date` comes back as an ISO string. Comparing
    a `datetime` object against it would make every recruitment conf differ
    from itself, and push would rewrite it on every run."""
    from .study import normalise_section

    slug = client.create_study(org, "HPV")["slug"]
    recruitment = {
        "ad_campaign_name": "hpv",
        "objective": "OUTCOME_ENGAGEMENT",
        "optimization_goal": "LINK_CLICKS",
        "min_budget": 100,
        "budget": 10000,
        "max_sample": 1000,
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-03-01T00:00:00",
    }

    client.post_conf(org, slug, "recruitment", recruitment)
    stored = client.get_confs(org, slug)["recruitment"]

    assert normalise_section("recruitment", stored) == normalise_section(
        "recruitment", recruitment
    )


def test_the_server_fills_defaults_and_the_response_says_what_was_stored(client, org):
    slug = client.create_study(org, "HPV")["slug"]

    written = client.post_conf(
        org,
        slug,
        "general",
        {
            "name": "x",
            "credentials_key": "Facebook",
            "credentials_entity": "facebook",
            "ad_account": "123",
            "opt_window": 48,
        },
    )

    assert written["conf"]["extra_metadata"] == {}


def test_data_sources_posts_hyphenated_and_stores_underscored(client, org):
    """Two of the nine differ, and reading back with the hyphen finds nothing."""
    slug = client.create_study(org, "HPV")["slug"]

    client.post_conf(
        org,
        slug,
        "data-sources",
        [{"name": "fly", "source": "typeform", "credentials_key": "tf"}],
    )

    assert "data_sources" in client.get_confs(org, slug)


def test_a_bad_section_is_an_unprocessable_error_with_field_errors(client, org):
    slug = client.create_study(org, "HPV")["slug"]

    with pytest.raises(UnprocessableError) as e:
        client.post_conf(org, slug, "general", {"name": "x"})

    assert e.value.status_code == 422
    locs = {tuple(fe["loc"]) for fe in e.value.field_errors}
    assert ("body", "ad_account") in locs
    # The rendering drops the leading "body" segment: the caller knows where it
    # put the value, and `body -> ad_account` reads worse than `ad_account`.
    assert any(line.startswith("ad_account:") for line in e.value.detail_lines())


def test_posting_to_a_study_that_does_not_exist_is_a_500_not_a_404(client, org):
    """Inherited, and worth pinning: the insert's study subselect yields NULL
    against a NOT NULL column, so psycopg raises and nothing catches it. Read
    it as "confirm the slug", not as "transient"."""
    with pytest.raises(ServerError) as e:
        client.post_conf(org, "no-such-study", "destinations", [MESSENGER])
    assert e.value.status_code == 500


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_returns_the_whole_envelope_including_known_gaps(client, org):
    slug = client.create_study(org, "HPV")["slug"]

    body = client.validate(org, slug)

    assert body["data"]["valid"] is False  # nothing written yet
    assert body["known_gaps"]  # what the verdict did NOT cover


def test_validate_overlays_proposed_sections_without_writing_them(client, org):
    slug = client.create_study(org, "HPV")["slug"]

    client.validate(org, slug, {"destinations": [MESSENGER]})

    assert client.get_confs(org, slug) == {}


def test_an_invalid_study_is_a_200_and_a_report_not_an_exception(client, org):
    """The report is the answer, not the outcome. A client that raised here
    could not tell "your study is wrong" from "your request is wrong"."""
    slug = client.create_study(org, "HPV")["slug"]
    body = client.validate(org, slug, {"strata": [{"nonsense": 1}]})
    assert body["data"]["valid"] is False
    assert any(e["code"] == "section.invalid" for e in body["data"]["errors"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_the_bearer_header_is_sent(client, org):
    with patch.object(client.session, "request", wraps=client.session.request) as m:
        client.create_study(org, "HPV")
    assert m.call_args.kwargs["headers"]["Authorization"] == "Bearer token"


def test_no_key_sends_no_authorization_header():
    """So that `GET /health` and a misconfigured environment produce a clean
    401 rather than `Bearer None`."""
    c = VlabClient(api_key=None, base_url="http://testserver")
    assert "Authorization" not in c._headers()


def test_an_unusable_token_is_a_not_authenticated_error(org):
    c = VlabClient(
        api_key="nope",
        base_url="http://testserver",
        session=TestClient(app, raise_server_exceptions=False),
    )
    with patch("adopt.server.auth.verify_token") as m:
        from ..server.auth import DifferentAuthError

        m.side_effect = DifferentAuthError("not auth0")
        with pytest.raises(NotAuthenticatedError) as e:
            c.create_study(org, "HPV")

    assert e.value.status_code == 401
    assert "Could not validate credentials" in str(e.value)


# ---------------------------------------------------------------------------
# Plan and apply, with the Meta boundary mocked
# ---------------------------------------------------------------------------


def test_plan_returns_the_instruction_list(client, org):
    slug = client.create_study(org, "HPV")["slug"]

    from ..facebook.update import Instruction

    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = [Instruction("campaign", "create", {"name": "hpv"})]
        instructions = client.plan(org, slug)

    assert instructions == [
        {"node": "campaign", "action": "create", "params": {"name": "hpv"}, "id": None}
    ]


def test_a_configuration_failure_reaches_the_caller_as_a_server_error(client, org):
    """The optimize routes are the one place a run-time configuration failure
    is reported in the response body, so the message must survive."""
    slug = client.create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as m:
        m.side_effect = Exception("Config Problem: destination nope is not configured")
        with pytest.raises(ServerError) as e:
            client.plan(org, slug)

    assert "destination nope" in str(e.value)


def test_apply_posts_the_instruction_verbatim(client, org):
    slug = client.create_study(org, "HPV")["slug"]
    instruction = {
        "node": "adset",
        "action": "create",
        "params": {"name": "men"},
        "id": None,
    }

    with patch("adopt.server.server.run_single_instruction") as m:
        m.return_value = {
            "timestamp": "2026-01-01T00:00:00",
            "instruction": instruction,
        }
        result = client.apply(org, slug, instruction)

    assert result["instruction"] == instruction
    assert m.call_args[0][3].model_dump() == instruction


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def test_list_api_keys(client, org):
    body = client.list_api_keys()
    assert body["keys"] == []
    assert body["legacy_revocations"] == []


def test_revoking_a_key_that_is_not_yours_is_a_not_found_error(client):
    """404 rather than 403, so this cannot be used to find out whether someone
    else's key exists."""
    with pytest.raises(NotFoundError):
        client.revoke_api_key(str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Error rendering, on shapes this app cannot produce
# ---------------------------------------------------------------------------


class _Response:
    def __init__(self, status_code, body=None, text=None):
        self.status_code = status_code
        self._body = body
        self.text = text if text is not None else __import__("json").dumps(body or {})
        self.headers = {}

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


class _Session:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def request(self, *a, **kw):
        if self.error:
            raise self.error
        return self.response


def _client(response=None, error=None):
    return VlabClient(
        api_key="k", base_url="http://x", session=_Session(response, error)
    )


def test_a_meta_error_object_keeps_its_codes_and_stays_inspectable():
    """`detail` is an OBJECT on the Meta proxy, not a string. Flattening it
    would throw away the `code` a caller looks up."""
    detail = {
        "message": "Meta rejected the request: Session has expired.",
        "meta_error": {
            "code": 190,
            "subcode": None,
            "type": "OAuth",
            "message": "…",
            "http_status": 400,
        },
    }
    c = _client(_Response(400, {"detail": detail}))

    with pytest.raises(VlabHTTPError) as e:
        c.meta_adaccounts("org")

    assert e.value.detail["meta_error"]["code"] == 190
    rendered = e.value.detail_lines()[0]
    assert "Session has expired" in rendered
    assert "code=190" in rendered
    assert "type=OAuth" in rendered


def test_a_body_that_is_not_json_is_still_legible():
    """An ingress error page, say. Better than a bare status."""
    c = _client(_Response(502, None, text="<html>502 Bad Gateway</html>"))
    with pytest.raises(ServerError) as e:
        c.get_confs("org", "slug")
    assert "502 Bad Gateway" in str(e.value)


def test_a_transport_failure_is_its_own_type():
    """Distinct from ServerError: a 502 means vlab answered and said Meta is
    unhappy; this means nothing answered."""
    c = _client(error=OSError("connection refused"))
    with pytest.raises(TransportError) as e:
        c.get_confs("org", "slug")
    assert "connection refused" in str(e.value)


def test_a_204_returns_none_rather_than_failing_to_parse_an_empty_body():
    c = _client(_Response(204, None, text=""))
    assert c.revoke_api_key("abc") is None


def test_none_query_parameters_are_dropped():
    """So optional parameters can be passed positionally at every call site
    without building the dict conditionally."""
    session = _Session(_Response(200, {"data": []}))
    c = VlabClient(api_key="k", base_url="http://x", session=session)

    seen = {}

    def request(method, url, **kw):
        seen.update(kw)
        return _Response(200, {"data": []})

    session.request = request
    c.meta_ads("org", campaign="123")

    assert seen["params"] == {"campaign": "123"}


def test_a_path_segment_cannot_escape_its_place():
    """A slug is `[a-z0-9-]` in practice, so this is the identity on real
    input. It exists for the ill-formed input: an unencoded `/` would silently
    address a different route."""
    seen = {}

    def request(method, url, **kw):
        seen["url"] = url
        return _Response(200, {"data": {}})

    session = _Session()
    session.request = request
    c = VlabClient(api_key="k", base_url="http://x", session=session)
    c.get_confs("org", "a/b")

    assert seen["url"] == "http://x/org/studies/a%2Fb/confs"


def test_describe_renders_one_line_per_field_error():
    detail = [
        {"loc": ["body", "ad_account"], "msg": "Field required", "type": "missing"},
        {"loc": ["body", 0, "name"], "msg": "Field required", "type": "missing"},
    ]
    c = _client(_Response(422, {"detail": detail}))

    with pytest.raises(UnprocessableError) as e:
        c.get_confs("org", "slug")

    text = str(e.value)
    assert "ad_account: Field required" in text
    assert "[0].name: Field required" in text
