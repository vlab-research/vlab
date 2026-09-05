"""Tests for the read-only Meta Graph proxy (`meta.py`).

Phase 2 of planning/agent-study-authoring.md §8.

WHERE THE MOCK BOUNDARY IS, and why it is there rather than higher up.

`FacebookAdsApi.call` is patched — the single method that puts bytes on the
wire — and nothing above it. So every test drives the real router, the real
`get_current_user`, the real scope middleware, the real credential SQL against
the real schema, and the real `facebook.state.get_api` session construction
(`appsecret_proof` included). Only the HTTP request to graph.facebook.com is
fake. Mocking `_api_for` instead would have been easier and would have stopped
testing three of the four things that can actually break.

The properties worth asserting, and why each is here:

- the request Meta receives is the one the dashboard sends today — path, and
  `fields` in particular, because `fields` is the contract (§"THE CONTRACT IS
  THE DASHBOARD'S" in meta.py) and a dropped field silently changes what a
  study deploys;
- cursors are followed, and truncation is announced rather than silent;
- a missing / ambiguous / unknown credential fails loudly with something the
  caller can act on, rather than 500ing or picking;
- a Meta rejection keeps its code and message and never becomes a bare 500;
- **the access token never appears in a response body**, on any route, on any
  path through the code including every error branch. That is the whole reason
  the proxy exists, so it is asserted exhaustively rather than spot-checked.
"""

import os
import uuid
from datetime import datetime, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import orjson
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..db import execute

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"
# `facebook.state.get_api` reads these at call time. The proxy builds a real
# session with them, so they have to exist for the test to reach the mocked
# `call` at all.
os.environ["FACEBOOK_APP_ID"] = "test-app-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-app-secret"

from facebook_business.api import FacebookAdsApi  # noqa: E402
from facebook_business.exceptions import FacebookRequestError  # noqa: E402

from . import api_keys as ak  # noqa: E402
from . import meta  # noqa: E402
from .auth import DifferentAuthError, generate_api_token  # noqa: E402

USER = "test|meta-proxy"
OTHER_USER = "test|meta-proxy-other"

# Distinctive so that "is the token in this response?" is an exact substring
# test with no chance of a coincidental match.
TOKEN = "SUPER-SECRET-FB-TOKEN-8b1f"
OTHER_TOKEN = "SECOND-SECRET-FB-TOKEN-3c9a"


def _make_app() -> FastAPI:
    app = FastAPI()
    # First-added is innermost, exactly as in server.py.
    ak.add_scope_enforcement(app)
    app.include_router(meta.router)
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
    """Every token in this module is a vlab API key, never an Auth0 one.

    `verify_tokens` tries Auth0 first, which would fetch a JWKS over the
    network. Raising DifferentAuthError is how a non-Auth0 token behaves.
    """
    with patch("adopt.server.auth.verify_token") as m:
        m.side_effect = DifferentAuthError("not an auth0 token")
        yield m


def _org(*members) -> str:
    org_id = str(uuid.uuid4())
    # `orgs.name` is UNIQUE, so two orgs in one test need two names.
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, org_id))
    for uid in members:
        execute(
            db_conf,
            "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
            (org_id, uid),
        )
    return org_id


def _credential(user_id: str, entity: str, key: str, details: Dict[str, Any]):
    execute(
        db_conf,
        "insert into credentials (user_id, entity, key, details)"
        " values (%s, %s, %s, %s)",
        (user_id, entity, key, orjson.dumps(details).decode("utf8")),
    )


def _key(user_id: str = USER, scopes: Optional[List[str]] = None, name: str = "k"):
    token, _ = generate_api_token(user_id=user_id, name=name, scopes=scopes)
    return {"Authorization": f"Bearer {token}"}


def _setup(scopes: Optional[List[str]] = None):
    """One org the caller belongs to, one Facebook credential, one API key."""
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    return org_id, _key(scopes=scopes)


# --------------------------------------------------------------------------
# The mocked Graph boundary
# --------------------------------------------------------------------------


class _Response:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


class _Graph:
    """Records the calls made, replays canned bodies.

    A body may be an exception instance, in which case it is raised — that is
    how the Meta-error paths are driven without a network.
    """

    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, api_self, method, path, params=None, **kwargs):
        self.calls.append(
            {
                "method": method,
                # meta.py always passes a tuple of path segments; joining is
                # what the SDK would do to build the URL.
                "path": "/".join(str(p) for p in path),
                "params": dict(params or {}),
                # The session is where the token lives. Captured so the leak
                # test can prove the token really was in play.
                "session_params": dict(api_self._session.requests.params),
            }
        )
        body = self.bodies.pop(0) if self.bodies else {"data": []}
        if isinstance(body, BaseException):
            raise body
        return _Response(body)


def _graph(*bodies):
    g = _Graph(bodies)

    # A plain function, not the recorder itself: setting a non-function object
    # as a class attribute skips the descriptor protocol, so `api.call(...)`
    # would be invoked with no `self` and the argument positions would all
    # shift by one.
    def _call(api_self, method, path, params=None, **kwargs):
        return g(api_self, method, path, params=params, **kwargs)

    return patch.object(FacebookAdsApi, "call", _call), g


def _page(data, next_url=None, after="CURSOR"):
    paging: Dict[str, Any] = {"cursors": {"before": "B", "after": after}}
    if next_url:
        paging["next"] = next_url
    return {"data": data, "paging": paging}


def _page_without_cursors(data, next_url):
    """A page carrying `paging.next` but no `paging.cursors`.

    Meta normally sends both; some edges do not. See `_after_from_url`.
    """
    return {"data": data, "paging": {"next": next_url}}


def _fb_error(http_status: int, code: int, message: str, subcode=None, type_="OAuth"):
    error: Dict[str, Any] = {"message": message, "code": code, "type": type_}
    if subcode is not None:
        error["error_subcode"] = subcode
    return FacebookRequestError(
        message="Call was not successful",
        request_context={
            "method": "GET",
            "path": "https://graph.facebook.com/v22.0/me/adaccounts",
            # The SDK stringifies request_context into str(e). The token is on
            # the SESSION's params, not here — but a careless implementation
            # that echoed str(e) would still leak everything about the request,
            # so this carries a marker the leak test looks for.
            "params": {"fields": "name,id", "access_token": TOKEN},
        },
        http_status=http_status,
        http_headers={},
        body=orjson.dumps({"error": error}).decode("utf8"),
    )


# --------------------------------------------------------------------------
# Happy paths — one per route, asserting the request Meta receives
# --------------------------------------------------------------------------


def test_adaccounts_sends_the_dashboards_request():
    org_id, headers = _setup()
    ctx, g = _graph(_page([{"id": "act_1", "account_id": "1", "name": "Acct"}]))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 200, res.text
    assert res.json()["data"] == [{"id": "act_1", "account_id": "1", "name": "Acct"}]

    call = g.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "me/adaccounts"
    # `fetchAdAccounts`, dashboard/src/helpers/api.ts:487.
    assert call["params"]["fields"] == "name,id,account_id"
    assert call["params"]["limit"] == meta.DEFAULT_LIMIT
    # The token reached Meta on the session, which is the only place it belongs.
    assert call["session_params"]["access_token"] == TOKEN


def test_campaigns_accepts_bare_and_prefixed_account_ids():
    org_id, headers = _setup()

    for account, expected in (("1234", "act_1234"), ("act_1234", "act_1234")):
        ctx, g = _graph(_page([{"id": "23", "name": "Template"}]))
        with ctx:
            res = client.get(
                f"/{org_id}/meta/campaigns",
                params={"account": account},
                headers=headers,
            )
        assert res.status_code == 200, res.text
        assert g.calls[0]["path"] == f"{expected}/campaigns"
        # `fetchCampaigns`, api.ts:517.
        assert g.calls[0]["params"]["fields"] == "name,id"


def test_adsets_include_targeting_because_extract_needs_it():
    org_id, headers = _setup()
    adset = {"id": "77", "name": "geo-lagos", "targeting": {"age_min": 18}}
    ctx, g = _graph(_page([adset]))

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adsets", params={"campaign": "23"}, headers=headers
        )

    assert res.status_code == 200, res.text
    assert g.calls[0]["path"] == "23/adsets"
    # `fetchAdsets`, api.ts:549. `targeting` is the entire input to
    # adopt.authoring.extract.extract_from_adset; dropping it would make the
    # proxy useless for the job it was built for.
    assert g.calls[0]["params"]["fields"] == "name,id,targeting"
    assert res.json()["data"][0]["targeting"] == {"age_min": 18}


def test_ads_nest_the_creative_exactly_as_the_dashboard_receives_it():
    org_id, headers = _setup()
    ad = {"id": "99", "name": "ad-a", "creative": {"id": "5", "name": "cre"}}
    ctx, g = _graph(_page([ad]))

    with ctx:
        res = client.get(
            f"/{org_id}/meta/ads", params={"campaign": "23"}, headers=headers
        )

    assert res.status_code == 200, res.text
    assert g.calls[0]["path"] == "23/ads"
    # `fetchAds`, api.ts:583-598 — the exact expansion, in order. This string is
    # what determines the contents of a stored creative `template`.
    assert g.calls[0]["params"]["fields"] == (
        "id,name,creative{id,name,actor_id,asset_feed_spec,"
        "degrees_of_freedom_spec,effective_instagram_media_id,"
        "effective_object_story_id,instagram_user_id,object_story_spec,"
        "contextual_multi_ads,thumbnail_url}"
    )
    assert res.json()["data"][0]["creative"] == {"id": "5", "name": "cre"}


def test_ads_can_be_addressed_by_adset():
    org_id, headers = _setup()
    ctx, g = _graph(_page([]))

    with ctx:
        res = client.get(f"/{org_id}/meta/ads", params={"adset": "77"}, headers=headers)

    assert res.status_code == 200, res.text
    assert g.calls[0]["path"] == "77/ads"


@pytest.mark.parametrize(
    "params", [{}, {"campaign": "23", "adset": "77"}], ids=["neither", "both"]
)
def test_ads_require_exactly_one_parent(params):
    org_id, headers = _setup()
    ctx, _ = _graph()

    with ctx:
        res = client.get(f"/{org_id}/meta/ads", params=params, headers=headers)

    assert res.status_code == 400
    assert "exactly one" in res.json()["detail"]


def test_ad_creative_returns_the_blob_that_becomes_a_template():
    org_id, headers = _setup()
    creative = {"id": "5", "name": "cre", "object_story_spec": {"page_id": "1"}}
    ctx, g = _graph({"id": "99", "name": "ad-a", "creative": creative})

    with ctx:
        res = client.get(f"/{org_id}/meta/ads/99/creative", headers=headers)

    assert res.status_code == 200, res.text
    assert res.json()["data"] == creative
    assert g.calls[0]["path"] == "99"


def test_ad_without_a_creative_is_404_not_a_null_template():
    org_id, headers = _setup()
    ctx, _ = _graph({"id": "99", "name": "ad-a"})

    with ctx:
        res = client.get(f"/{org_id}/meta/ads/99/creative", headers=headers)

    # A 200 with `{"data": null}` would let an agent store `template: null` and
    # discover the problem hours later, at ad-create time.
    assert res.status_code == 404
    assert "no creative" in res.json()["detail"]


def test_credentials_listing_names_the_keys():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    _credential(USER, "facebook_ad_user", "vlab", {"access_token": OTHER_TOKEN})
    # A non-Facebook credential, and a Facebook-shaped one with no token: both
    # are excluded, for different reasons.
    _credential(USER, "typeform", "tf", {"access_token": "nope"})
    _credential(USER, "facebook", "Broken", {"token": "wrong-field-name"})

    res = client.get(f"/{org_id}/meta/credentials", headers=_key())

    assert res.status_code == 200, res.text
    keys = {c["key"]: c["entity"] for c in res.json()["data"]}
    assert keys == {"Facebook": "facebook", "vlab": "facebook_ad_user"}


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------


def test_cursors_are_followed_server_side():
    org_id, headers = _setup()
    ctx, g = _graph(
        _page([{"id": "1"}], next_url="https://graph/next", after="C1"),
        _page([{"id": "2"}], next_url="https://graph/next", after="C2"),
        _page([{"id": "3"}], after="C3"),
    )

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    body = res.json()
    assert [d["id"] for d in body["data"]] == ["1", "2", "3"]
    assert body["paging"] == {"after": None, "truncated": False, "pages_fetched": 3}

    # The resume token is sent as `after`, NOT as `cursor`. The dashboard sends
    # `cursor`, which Graph ignores — its "load more" silently re-fetches page
    # one (api.ts:495). Reproducing the contract does not extend to that bug.
    assert "after" not in g.calls[0]["params"]
    assert g.calls[1]["params"]["after"] == "C1"
    assert g.calls[2]["params"]["after"] == "C2"


def test_truncation_is_announced_and_resumable():
    org_id, headers = _setup()
    ctx, g = _graph(
        *[
            _page([{"id": str(i)}], next_url="https://graph/next", after=f"C{i}")
            for i in range(meta.MAX_PAGES + 3)
        ]
    )

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    body = res.json()
    assert len(g.calls) == meta.MAX_PAGES
    assert len(body["data"]) == meta.MAX_PAGES
    # Silence here would be the dangerous failure: an agent builds a study from
    # a partial ad-set list and nothing says so.
    assert body["paging"]["truncated"] is True
    assert body["paging"]["after"] == f"C{meta.MAX_PAGES - 1}"

    # ...and that cursor resumes.
    ctx2, g2 = _graph(_page([{"id": "next"}], after="D"))
    with ctx2:
        res2 = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"after": body["paging"]["after"]},
            headers=headers,
        )
    assert res2.status_code == 200
    assert g2.calls[0]["params"]["after"] == f"C{meta.MAX_PAGES - 1}"


def test_a_truncated_result_is_never_left_without_a_resume_cursor():
    """`truncated: true` with `after: null` is the one unrecoverable answer.

    A page can carry `paging.next` without `paging.cursors`. Reading the cursor
    only out of `cursors.after` would then tell the caller "this list is
    incomplete" and hand them nothing to continue with.
    """
    org_id, headers = _setup()
    ctx, g = _graph(
        *[
            _page_without_cursors(
                [{"id": str(i)}],
                f"https://graph.facebook.com/v22.0/me/adaccounts"
                f"?limit=100&after=FROMURL{i}",
            )
            for i in range(meta.MAX_PAGES + 2)
        ]
    )

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    body = res.json()
    assert body["paging"]["truncated"] is True
    assert body["paging"]["after"] == f"FROMURL{meta.MAX_PAGES - 1}"
    # ...and it was used to walk the pages, not just reported at the end.
    assert g.calls[1]["params"]["after"] == "FROMURL0"


def test_cursors_after_wins_over_the_next_url():
    """The URL is a fallback, not a replacement — `cursors.after` is canonical."""
    org_id, headers = _setup()
    page = _page([{"id": "1"}], next_url="https://graph/x?after=FROMURL", after="C1")
    ctx, g = _graph(page, _page([{"id": "2"}], after="C2"))

    with ctx:
        client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert g.calls[1]["params"]["after"] == "C1"


def test_a_next_url_with_no_after_reports_a_null_cursor_rather_than_raising():
    org_id, headers = _setup()
    ctx, _ = _graph(
        *[
            _page_without_cursors([{"id": str(i)}], "https://graph/next?offset=10")
            for i in range(meta.MAX_PAGES + 1)
        ]
    )

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    # Honest, and no worse than before: the caller is told the list is partial
    # and that we have no cursor for it.
    assert res.status_code == 200, res.text
    assert res.json()["paging"] == {
        "after": None,
        "truncated": True,
        "pages_fetched": meta.MAX_PAGES,
    }


def test_after_from_url_is_total():
    assert meta._after_from_url(None) is None
    assert meta._after_from_url("") is None
    assert meta._after_from_url("https://graph/x?after=ABC") == "ABC"
    assert meta._after_from_url("https://graph/x?limit=2&after=ABC&pretty=0") == "ABC"
    assert meta._after_from_url("https://graph/x?offset=10") is None
    assert meta._after_from_url("not a url at all") is None
    # Percent-encoded cursors are what Meta actually sends.
    assert meta._after_from_url("https://graph/x?after=QVFIU%3D") == "QVFIU="


def test_limit_is_bounded():
    org_id, headers = _setup()
    ctx, _ = _graph()

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"limit": meta.MAX_LIMIT + 1},
            headers=headers,
        )

    assert res.status_code == 422


# --------------------------------------------------------------------------
# Credential resolution
# --------------------------------------------------------------------------


def test_no_facebook_credential_is_an_actionable_400():
    org_id = _org(USER)
    ctx, g = _graph()

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=_key())

    assert res.status_code == 400
    detail = res.json()["detail"]
    # Fail fast and loud: it must say what is missing AND that only a human can
    # fix it, because the OAuth exchange is Auth0-only.
    assert "no connected Facebook credential" in detail
    assert "API key" in detail
    # Nothing was asked of Meta.
    assert g.calls == []


def test_two_credentials_refuse_to_guess_and_name_both():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    _credential(USER, "facebook_ad_user", "vlab", {"access_token": OTHER_TOKEN})
    ctx, g = _graph()

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=_key())

    assert res.status_code == 409
    detail = res.json()["detail"]
    assert "'Facebook'" in detail and "'vlab'" in detail
    assert "credentials_key" in detail
    assert g.calls == []


def test_credentials_key_selects_the_token():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    _credential(USER, "facebook_ad_user", "vlab", {"access_token": OTHER_TOKEN})
    ctx, g = _graph(_page([]))

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"credentials_key": "vlab"},
            headers=_key(),
        )

    assert res.status_code == 200, res.text
    assert g.calls[0]["session_params"]["access_token"] == OTHER_TOKEN


def test_unknown_credentials_key_is_404_listing_what_exists():
    org_id, headers = _setup()
    ctx, _ = _graph()

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"credentials_key": "nope"},
            headers=headers,
        )

    assert res.status_code == 404
    assert "Available: Facebook." in res.json()["detail"]


def test_a_non_facebook_credential_cannot_be_named_by_credentials_key():
    """A typeform token must not be shipped to graph.facebook.com.

    `credentials` holds tokens for other providers under the same
    `(user_id, key)` shape, and several of them also store a field called
    `access_token`. This is the caller's own credential, so it is not a
    cross-tenant leak — it is a credential handed to a third party with no
    business seeing it, and it made the 404's "Available:" list contradict what
    the lookup actually accepted.
    """
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    _credential(USER, "typeform", "my-typeform", {"access_token": "TYPEFORM-TOKEN"})
    ctx, g = _graph()

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"credentials_key": "my-typeform"},
            headers=_key(),
        )

    assert res.status_code == 404
    # The error names only what the lookup would actually have accepted.
    assert "Available: Facebook." in res.json()["detail"]
    assert "my-typeform" not in res.json()["detail"].split("Available:")[1]
    # And nothing was sent to Meta.
    assert g.calls == []
    assert "TYPEFORM-TOKEN" not in res.text


def test_another_users_credential_is_not_reachable():
    org_id = _org(USER, OTHER_USER)
    _credential(OTHER_USER, "facebook", "TheirAccount", {"access_token": OTHER_TOKEN})
    ctx, g = _graph()

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adaccounts",
            params={"credentials_key": "TheirAccount"},
            headers=_key(),
        )

    # Same org, and still not visible: `credentials` are user-scoped, and the
    # proxy reads with the CALLING user's token, never an org-mate's.
    assert res.status_code == 404
    assert g.calls == []


# --------------------------------------------------------------------------
# Org membership and id validation
# --------------------------------------------------------------------------


def test_non_member_gets_404_not_403():
    _org(USER)
    other_org = _org(OTHER_USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    ctx, g = _graph()

    with ctx:
        res = client.get(f"/{other_org}/meta/adaccounts", headers=_key())

    assert res.status_code == 404
    assert g.calls == []


def test_malformed_org_id_is_404_not_a_driver_error():
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    ctx, _ = _graph()

    with ctx:
        res = client.get("/not-a-uuid/meta/adaccounts", headers=_key())

    assert res.status_code == 404


@pytest.mark.parametrize(
    "path,params",
    [
        ("/meta/adsets", {"campaign": "me/adaccounts"}),
        ("/meta/ads", {"campaign": "../../me"}),
        ("/meta/campaigns", {"account": "me"}),
    ],
)
def test_ids_are_validated_before_they_reach_a_url_path(path, params):
    org_id, headers = _setup()
    ctx, g = _graph()

    with ctx:
        res = client.get(f"/{org_id}{path}", params=params, headers=headers)

    # Ids are interpolated into a URL PATH, so an unvalidated one silently
    # retargets the request at a different Graph edge.
    assert res.status_code == 400
    assert g.calls == []


def test_creative_route_validates_the_ad_id():
    org_id, headers = _setup()
    ctx, g = _graph()

    with ctx:
        res = client.get(f"/{org_id}/meta/ads/me/creative", headers=headers)

    assert res.status_code == 400
    assert g.calls == []


# --------------------------------------------------------------------------
# Meta errors
# --------------------------------------------------------------------------


def test_meta_4xx_passes_its_status_code_and_message_through():
    org_id, headers = _setup()
    ctx, _ = _graph(
        _fb_error(400, 190, "Error validating access token: Session has expired.")
    )

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "Session has expired" in detail["message"]
    # Structured, so an agent can branch on the code rather than parse prose.
    assert detail["meta_error"]["code"] == 190
    assert detail["meta_error"]["http_status"] == 400


def test_meta_404_is_a_404():
    org_id, headers = _setup()
    ctx, _ = _graph(_fb_error(404, 803, "Unknown object", type_="GraphMethodException"))

    with ctx:
        res = client.get(
            f"/{org_id}/meta/adsets", params={"campaign": "23"}, headers=headers
        )

    assert res.status_code == 404
    assert res.json()["detail"]["meta_error"]["code"] == 803


@pytest.mark.parametrize("status", [429, 500, 503])
def test_meta_throttling_and_outages_are_502_not_500(status):
    org_id, headers = _setup()
    ctx, _ = _graph(_fb_error(status, 17, "User request limit reached"))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    # Never a bare 500: the distinction between "we broke" and "Meta broke"
    # is the whole of an on-call engineer's first question.
    assert res.status_code == 502
    assert res.json()["detail"]["meta_error"]["code"] == 17


def test_a_network_failure_is_502_not_500():
    org_id, headers = _setup()
    ctx, _ = _graph(ConnectionError("connection reset by peer"))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 502
    assert "Could not reach the Meta Graph API" in res.json()["detail"]["message"]
    assert res.json()["detail"]["meta_error"] is None


def test_a_non_dict_body_from_meta_is_502():
    org_id, headers = _setup()
    ctx, _ = _graph("not json at all")

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 502


# --------------------------------------------------------------------------
# Scopes
# --------------------------------------------------------------------------


def test_a_key_without_meta_read_is_denied():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    headers = _key(scopes=["studies:write", "optimize:read"], name="narrow")
    ctx, g = _graph(_page([]))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 403
    assert "meta:read" in res.json()["detail"]
    # Denied before anything talked to Meta or read a credential.
    assert g.calls == []


def test_a_key_with_meta_read_is_allowed():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    headers = _key(scopes=["meta:read"], name="metaonly")
    ctx, _ = _graph(_page([{"id": "act_1"}]))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    assert res.status_code == 200, res.text


def test_a_key_with_no_scopes_claim_is_unrestricted():
    org_id, headers = _setup(scopes=None)
    ctx, _ = _graph(_page([{"id": "act_1"}]))

    with ctx:
        res = client.get(f"/{org_id}/meta/adaccounts", headers=headers)

    # The Phase 0 compatibility rule: an absent scopes claim means
    # unrestricted, so no existing key breaks when a new resource is added.
    assert res.status_code == 200, res.text


def test_meta_write_is_not_served_by_anything():
    org_id, headers = _setup(scopes=["meta:read"])
    res = client.post(f"/{org_id}/meta/adaccounts", headers=headers)
    assert res.status_code in (403, 405)


def test_no_token_at_all_is_401():
    org_id = _org(USER)
    res = client.get(f"/{org_id}/meta/adaccounts")
    assert res.status_code == 403  # HTTPBearer with no header
    res = client.get(
        f"/{org_id}/meta/adaccounts", headers={"Authorization": "Bearer garbage"}
    )
    assert res.status_code == 401


# --------------------------------------------------------------------------
# The token must never come back
# --------------------------------------------------------------------------


def _every_route(org_id):
    return [
        (f"/{org_id}/meta/credentials", {}),
        (f"/{org_id}/meta/adaccounts", {}),
        (f"/{org_id}/meta/campaigns", {"account": "1234"}),
        (f"/{org_id}/meta/adsets", {"campaign": "23"}),
        (f"/{org_id}/meta/ads", {"campaign": "23"}),
        (f"/{org_id}/meta/ads/99/creative", {}),
    ]


@pytest.mark.parametrize(
    "body",
    [
        # success
        _page([{"id": "act_1", "creative": {"id": "5"}}]),
        # Meta rejects — the branch where a lazy implementation would echo
        # str(FacebookRequestError), whose text interpolates request_context.
        _fb_error(400, 190, "Error validating access token"),
        _fb_error(500, 1, "An unknown error occurred"),
        # the network fell over
        ConnectionError("reset"),
    ],
    ids=["ok", "meta-4xx", "meta-5xx", "network"],
)
def test_the_access_token_never_appears_in_a_response(body):
    """The single property the whole proxy exists to provide.

    Asserted across every route and every failure branch, because the leak that
    matters is the one on the path nobody thought about. `appsecret_proof` is
    checked too: it is an HMAC of the token and is equally not the caller's.
    """
    org_id, headers = _setup()

    for path, params in _every_route(org_id):
        ctx, _ = _graph(body, body, body, body)
        with ctx:
            res = client.get(path, params=params, headers=headers)

        assert TOKEN not in res.text, f"{path} leaked the access token"
        assert "appsecret_proof" not in res.text, f"{path} leaked appsecret_proof"
        for value in res.headers.values():
            assert TOKEN not in value


def test_the_credentials_listing_never_returns_details():
    org_id = _org(USER)
    _credential(
        USER,
        "facebook",
        "Facebook",
        {"access_token": TOKEN, "expires_in": 5183944, "token_type": "bearer"},
    )

    res = client.get(f"/{org_id}/meta/credentials", headers=_key())

    assert res.status_code == 200
    assert TOKEN not in res.text
    # Only the three fields a caller needs, not a projection of `details`.
    assert set(res.json()["data"][0]) == {"key", "entity", "created"}


def test_the_ambiguity_error_names_credentials_without_their_tokens():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})
    _credential(USER, "facebook_ad_user", "vlab", {"access_token": OTHER_TOKEN})

    res = client.get(f"/{org_id}/meta/adaccounts", headers=_key())

    assert res.status_code == 409
    assert TOKEN not in res.text
    assert OTHER_TOKEN not in res.text


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------


def test_normalize_account_id():
    assert meta.normalize_account_id("123") == "act_123"
    assert meta.normalize_account_id("act_123") == "act_123"
    for bad in ("", "me", "act_", "act_12a", "12/34", "act_123?x=1"):
        with pytest.raises(Exception):
            meta.normalize_account_id(bad)


def test_created_is_serialised_not_a_datetime():
    org_id = _org(USER)
    _credential(USER, "facebook", "Facebook", {"access_token": TOKEN})

    res = client.get(f"/{org_id}/meta/credentials", headers=_key())
    created = res.json()["data"][0]["created"]

    assert isinstance(created, str)
    assert datetime.fromisoformat(created).tzinfo is not None
    assert created <= datetime.now(timezone.utc).isoformat()
