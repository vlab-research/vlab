"""Tests for API-key hardening (Phase 0 of planning/agent-study-authoring.md).

The properties worth asserting, and why each one is here:

- mint -> use -> revoke -> rejected: the whole point.
- revoking one key leaves another alive: revocation is per-key, not per-user.
- re-minting the SAME NAME does not resurrect the revoked key: the core `jti`
  property, and the reason the lookup is not keyed on the name.
- an expired key is rejected, by the token's own `exp` AND by its row.
- a legacy (pre-hardening) token still works: the compatibility promise.
- a tombstone for user A does not kill user B's identically-named legacy key:
  the negative cache must be keyed per user, not per name.
- scope enforcement allows and denies; `write` implies `read`; an absent scopes
  claim is unrestricted.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from typing import Annotated, Optional
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from ..db import execute

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"

from . import api_keys as ak  # noqa: E402
from .auth import (  # noqa: E402
    API_KEY_AUDIENCE,
    API_KEY_DOMAIN,
    API_KEY_SECRET,
    NAME_CLAIM,
    DifferentAuthError,
)
from .deps import User, get_current_user  # noqa: E402

user_id = "test|api-keys"
other_user_id = "test|api-keys-other"

# A token that is not one of ours at all. `verify_token` is mocked per test to
# decide whether it authenticates (dashboard session) or raises
# DifferentAuthError (fall through to the API-key verifier).
AUTH0_TOKEN = "verysecret"


# --------------------------------------------------------------------------
# A test app: the router under test plus stubs standing in for the real
# server.py routes, so the path -> scope map is exercised against the paths it
# will actually see. server.py itself is owned by another change and is not
# imported here.
# --------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    # Added first so it is the INNERMOST middleware, which is where it belongs
    # in server.py too (inside CORS, so a 403 still gets CORS headers).
    ak.add_scope_enforcement(app)
    app.include_router(ak.router)

    async def _ok(user: Annotated[User, Depends(get_current_user)]):
        return {"user": user.user_id}

    for path in (
        "/{org_id}/studies/{slug}/confs/general",
        "/{org_id}/studies/{slug}/copy-from",
        "/{org_id}/optimize/{slug}/instruction",
    ):
        app.post(path)(_ok)

    for path in (
        "/{org_id}/studies/{slug}/confs/{conf_type}",
        "/{org_id}/studies/{slug}/ad-attributions",
        "/{org_id}/studies/{slug}/recruitment-stats",
        "/{org_id}/optimize/{slug}",
    ):
        app.get(path)(_ok)

    app.get("/health")(lambda: "OK")

    # A route the scope map does not know about, to assert fail-closed.
    app.get("/{org_id}/studies/{slug}/unclassified")(_ok)

    return app


client = TestClient(_make_app())

ORG = str(uuid.uuid4())


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_db():
    _reset_db()
    # `_reset_db` deletes credentials rows behind the cache's back, so a stale
    # positive entry from a previous test would make a deleted key look live.
    ak.clear_api_key_cache()
    execute(db_conf, "insert into users (id) values (%s)", (user_id,))
    execute(db_conf, "insert into users (id) values (%s)", (other_user_id,))
    yield
    ak.clear_api_key_cache()


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _legacy_token(sub: str, name: str) -> str:
    """A token exactly as `generate_api_token` produced it before hardening.

    Note it DOES carry a jti — that is the whole reason vlab needs an explicit
    version claim where fly could use jti-presence as the discriminator.
    """
    return jwt.encode(
        {
            "iss": API_KEY_DOMAIN,
            "aud": API_KEY_AUDIENCE,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": str(uuid.uuid4()),
            "sub": sub,
            NAME_CLAIM: name,
            "type": "api_key",
        },
        API_KEY_SECRET,
        algorithm="HS256",
    )


def _mint(verify_mock, name: str, scopes=None, expires_in_days: Optional[int] = None):
    """Mint a key as the dashboard would, over Auth0 auth."""
    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}

    body = {"name": name}
    if scopes is not None:
        body["scopes"] = scopes
    if expires_in_days is not None:
        body["expires_in_days"] = expires_in_days

    res = client.post("/users/api-key", headers=_headers(AUTH0_TOKEN), json=body)

    # Every later request in a test uses an API key, so hand the mock back
    # configured to fall through to the API-key verifier.
    verify_mock.side_effect = DifferentAuthError("not an auth0 token")
    return res


# --------------------------------------------------------------------------
# Pure scope logic — no database, no app
# --------------------------------------------------------------------------


def test_scope_grants_write_implies_read():
    assert ak.scope_grants("studies:write", "studies:read")
    assert not ak.scope_grants("studies:read", "studies:write")
    assert ak.scope_grants("studies:read", "studies:read")
    assert not ak.scope_grants("studies:read", "responses:read")
    assert ak.scope_grants("*", "anything:write")
    assert ak.scope_grants("studies:*", "studies:write")
    assert not ak.scope_grants("studies:read", "studies:*")


def test_absent_scopes_claim_is_unrestricted():
    assert ak.normalize_scopes(None) is None
    assert ak.scopes_allow(None, "studies:write")
    assert ak.is_authorized(None, "POST", f"/{ORG}/studies/s/confs/general")

    # An empty list is NOT unrestricted — it denies everything.
    assert ak.normalize_scopes([]) == []
    assert not ak.scopes_allow([], "studies:read")

    # Nor is a malformed claim: it must not be more powerful than a good one.
    assert ak.normalize_scopes(17) == []


def test_required_scope_maps_vlab_paths():
    # The org id is segment 1, so the resource has to be read from segment 2 —
    # a fly-style first-segment lookup would classify everything by a UUID.
    assert (
        ak.required_scope("POST", f"/{ORG}/studies/s/confs/general") == "studies:write"
    )
    assert ak.required_scope("GET", f"/{ORG}/studies/s/confs/general") == "studies:read"
    assert ak.required_scope("POST", f"/{ORG}/studies/s/copy-from") == "studies:write"
    assert (
        ak.required_scope("GET", f"/{ORG}/studies/s/ad-attributions")
        == "responses:read"
    )
    assert (
        ak.required_scope("GET", f"/{ORG}/studies/s/ad-attributions.csv")
        == "responses:read"
    )
    assert (
        ak.required_scope("GET", f"/{ORG}/studies/s/recruitment-stats") == "stats:read"
    )
    assert ak.required_scope("GET", f"/{ORG}/studies/s/cost-over-time") == "stats:read"
    assert ak.required_scope("GET", f"/{ORG}/optimize/s") == "optimize:read"
    assert (
        ak.required_scope("POST", f"/{ORG}/optimize/s/instruction") == "optimize:write"
    )
    assert ak.required_scope("POST", "/users/api-key") == "auth:write"
    assert ak.required_scope("GET", "/users/api-keys") == "auth:read"

    # The Meta Graph proxy (Phase 2). Every route under /{org}/meta, including
    # the nested creative one, classifies on the area segment alone.
    assert ak.required_scope("GET", f"/{ORG}/meta/adaccounts") == "meta:read"
    assert ak.required_scope("GET", f"/{ORG}/meta/campaigns") == "meta:read"
    assert ak.required_scope("GET", f"/{ORG}/meta/adsets") == "meta:read"
    assert ak.required_scope("GET", f"/{ORG}/meta/ads") == "meta:read"
    assert ak.required_scope("GET", f"/{ORG}/meta/ads/123/creative") == "meta:read"
    assert ak.required_scope("GET", f"/{ORG}/meta/credentials") == "meta:read"

    # `meta` is deliberately NOT implied by `studies` — the proxy reads the
    # researcher's whole Meta estate, not this org's study configuration.
    assert not ak.is_authorized(["studies:write"], "GET", f"/{ORG}/meta/adaccounts")
    assert ak.is_authorized(["meta:read"], "GET", f"/{ORG}/meta/adaccounts")
    assert not ak.is_authorized(["meta:read"], "GET", f"/{ORG}/studies/s/confs")

    # Unknown -> None -> denied for a scoped key (fail closed).
    assert ak.required_scope("GET", f"/{ORG}/studies/s/unclassified") is None
    assert not ak.is_authorized(
        ["studies:read"], "GET", f"/{ORG}/studies/s/unclassified"
    )
    # ...but `*` still passes, because `*` means what an absent claim means.
    assert ak.is_authorized(["*"], "GET", f"/{ORG}/studies/s/unclassified")


def test_can_grant_scopes_is_attenuating():
    assert ak.can_grant_scopes(None, ["studies:read"])
    assert ak.can_grant_scopes(None, None)
    assert ak.can_grant_scopes(["studies:write"], ["studies:read"])
    assert not ak.can_grant_scopes(["studies:read"], ["studies:write"])
    # A `requested` of None is a request for FULL ACCESS, not for nothing.
    assert not ak.can_grant_scopes(["studies:write", "auth:write"], None)


def test_validate_scopes_rejects_typos():
    from fastapi import HTTPException

    assert ak.validate_scopes(None) is None
    assert ak.validate_scopes(["studies:read", "studies:read"]) == ["studies:read"]

    with pytest.raises(HTTPException) as e:
        ak.validate_scopes(["studies:reed"])
    assert e.value.status_code == 400

    with pytest.raises(HTTPException):
        ak.validate_scopes([])


# --------------------------------------------------------------------------
# The cache
# --------------------------------------------------------------------------


def test_ttl_cache_caches_negatives_and_expires():
    cache = ak.TtlCache(ttl_seconds=30)

    assert cache.get("k", now=0) is ak.TtlCache._MISS

    # A cached None is a real answer ("known not to exist"), distinguishable
    # from a miss. That distinction is what stops replayed random jtis becoming
    # one database read each.
    cache.set("k", None, now=0)
    assert cache.get("k", now=10) is None
    assert cache.get("k", now=29.9) is None
    assert cache.get("k", now=30) is ak.TtlCache._MISS


def test_ttl_cache_is_bounded():
    cache = ak.TtlCache(ttl_seconds=30, max_entries=3)
    for i in range(5):
        cache.set(f"k{i}", i, now=0)
    assert len(cache) == 3
    assert cache.get("k0", now=0) is ak.TtlCache._MISS
    assert cache.get("k4", now=0) == 4


# --------------------------------------------------------------------------
# Mint / use / revoke
# --------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_mint_response_shape_is_unchanged(verify_mock):
    """The dashboard's generateApiKey consumes data.{name,id,token}."""
    res = _mint(verify_mock, "dashboard-key")
    assert res.status_code == 201

    data = res.json()["data"]
    assert data["name"] == "dashboard-key"
    assert data["token"]
    assert data["id"]
    # Additive, so the existing TypeScript type still parses.
    assert data["scopes"] is None
    assert data["expires_at"]


@patch("adopt.server.auth.verify_token")
def test_mint_use_revoke_rejected(verify_mock):
    res = _mint(verify_mock, "agent")
    token = res.json()["data"]["token"]
    key_id = res.json()["data"]["id"]

    ok = client.get(f"/{ORG}/studies/s/confs/general", headers=_headers(token))
    assert ok.status_code == 200
    assert ok.json()["user"] == user_id

    revoked = client.delete(f"/users/api-keys/{key_id}", headers=_headers(token))
    assert revoked.status_code == 204

    dead = client.get(f"/{ORG}/studies/s/confs/general", headers=_headers(token))
    assert dead.status_code == 401


@patch("adopt.server.auth.verify_token")
def test_revoking_one_key_leaves_the_other_working(verify_mock):
    a = _mint(verify_mock, "key-a").json()["data"]
    b = _mint(verify_mock, "key-b").json()["data"]

    assert (
        client.delete(
            f"/users/api-keys/{a['id']}", headers=_headers(a["token"])
        ).status_code
        == 204
    )

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(a["token"])
        ).status_code
        == 401
    )
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(b["token"])
        ).status_code
        == 200
    )


@patch("adopt.server.auth.verify_token")
def test_reusing_a_name_does_not_resurrect_the_revoked_key(verify_mock):
    """The core jti property.

    Revocation frees the name (the row is deleted, not flagged), so "agent" can
    be minted again — and the old token must stay dead, because validity is
    keyed on the jti and not on the name.
    """
    first = _mint(verify_mock, "agent").json()["data"]

    assert (
        client.delete(
            f"/users/api-keys/{first['id']}", headers=_headers(first["token"])
        ).status_code
        == 204
    )

    second = _mint(verify_mock, "agent").json()["data"]
    assert second["id"] != first["id"]

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(first["token"])
        ).status_code
        == 401
    )
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(second["token"])
        ).status_code
        == 200
    )


@patch("adopt.server.auth.verify_token")
def test_duplicate_live_name_is_a_conflict(verify_mock):
    assert _mint(verify_mock, "agent").status_code == 201
    assert _mint(verify_mock, "agent").status_code == 409


@patch("adopt.server.auth.verify_token")
def test_revoking_someone_elses_key_is_a_404(verify_mock):
    """404 and not 403, so this never confirms another user's key exists."""
    mine = _mint(verify_mock, "mine").json()["data"]

    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": other_user_id}
    res = client.delete(f"/users/api-keys/{mine['id']}", headers=_headers(AUTH0_TOKEN))
    assert res.status_code == 404

    # ...and the key still works.
    verify_mock.side_effect = DifferentAuthError("x")
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(mine["token"])
        ).status_code
        == 200
    )


@patch("adopt.server.auth.verify_token")
def test_list_api_keys(verify_mock):
    _mint(verify_mock, "one", scopes=["studies:read"])
    _mint(verify_mock, "two")

    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}
    res = client.get("/users/api-keys", headers=_headers(AUTH0_TOKEN))
    assert res.status_code == 200

    keys = res.json()["data"]["keys"]
    assert {k["name"] for k in keys} == {"one", "two"}
    by_name = {k["name"]: k for k in keys}
    assert by_name["one"]["scopes"] == ["studies:read"]
    assert by_name["two"]["scopes"] is None
    assert all(k["expired"] is False for k in keys)
    assert all(k["id"] for k in keys)

    # Another user sees none of them.
    verify_mock.return_value = {"sub": other_user_id}
    other = client.get("/users/api-keys", headers=_headers(AUTH0_TOKEN))
    assert other.json()["data"]["keys"] == []


# --------------------------------------------------------------------------
# Expiry
# --------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_expired_token_is_rejected(verify_mock):
    """`exp` in the past: jose rejects it before the row is ever consulted.

    Minted with a negative TTL rather than by waiting, and its row is live, so
    the only thing that can be denying it is the token's own expiry.
    """
    verify_mock.side_effect = DifferentAuthError("x")

    from .auth import generate_api_token

    token, jti = generate_api_token(user_id=user_id, name="stale", ttl_days=-1)
    assert ak._select_api_token_row(jti) is not None

    res = client.get(f"/{ORG}/studies/s/confs/general", headers=_headers(token))
    assert res.status_code == 401


@patch("adopt.server.auth.verify_token")
def test_expired_row_is_rejected_even_when_the_token_is_not(verify_mock):
    """Shortening a key's life by editing its row works without reissuing it."""
    verify_mock.side_effect = DifferentAuthError("x")

    from .auth import generate_api_token

    token, jti = generate_api_token(user_id=user_id, name="short", ttl_days=90)
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(token)).status_code == 200

    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    execute(
        db_conf,
        "update credentials set details = jsonb_set(details, '{expires_at}', %s) "
        "where entity = 'api_token' and api_token_jti = %s",
        (f'"{past}"', jti),
    )
    ak.clear_api_key_cache()

    res = client.get(f"/{ORG}/studies/s/confs/general", headers=_headers(token))
    assert res.status_code == 401


@patch("adopt.server.auth.verify_token")
def test_minted_keys_carry_an_exp(verify_mock):
    res = _mint(verify_mock, "bounded", expires_in_days=7)
    token = res.json()["data"]["token"]

    claims = jwt.get_unverified_claims(token)
    assert "exp" in claims
    ttl = claims["exp"] - claims["iat"]
    assert 6 * 86400 < ttl <= 7 * 86400 + 60


@patch("adopt.server.auth.verify_token")
def test_a_v2_token_with_no_row_is_rejected(verify_mock):
    """Positive validity: a perfectly-signed, unexpired token is not enough.

    This is the property that makes revocation real, asserted directly rather
    than through the revoke endpoint: delete the row by any means and the token
    stops working.
    """
    verify_mock.side_effect = DifferentAuthError("x")

    from .auth import generate_api_token

    token, jti = generate_api_token(user_id=user_id, name="orphan")
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(token)).status_code == 200

    execute(db_conf, "delete from credentials where api_token_jti = %s", (jti,))
    ak.clear_api_key_cache()

    res = client.get(f"/{ORG}/studies/s/confs/general", headers=_headers(token))
    assert res.status_code == 401


# --------------------------------------------------------------------------
# Legacy compatibility
# --------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_legacy_token_with_no_row_and_no_exp_still_works(verify_mock):
    """The compatibility promise: no production key breaks on deploy day.

    A legacy token carries a jti (vlab always minted one) but no version claim
    and no row, and is accepted anyway. It is also unrestricted, because it has
    no scopes claim.
    """
    verify_mock.side_effect = DifferentAuthError("x")
    token = _legacy_token(user_id, "old-key")

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/{ORG}/optimize/s/instruction", headers=_headers(token)
        ).status_code
        == 200
    )


@patch("adopt.server.auth.verify_token")
def test_legacy_token_is_revocable_by_name(verify_mock):
    token = _legacy_token(user_id, "leaked")

    verify_mock.side_effect = DifferentAuthError("x")
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )

    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}
    res = client.post(
        "/users/api-keys/legacy-revocations",
        headers=_headers(AUTH0_TOKEN),
        json={"name": "leaked"},
    )
    assert res.status_code == 201

    verify_mock.side_effect = DifferentAuthError("x")
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 401
    )


@patch("adopt.server.auth.verify_token")
def test_legacy_revocation_does_not_leak_across_users(verify_mock):
    """The negative cache is keyed per user, not per name.

    Two users may each hold a legacy key called "agent". One revoking theirs
    must not deny the other's — a name-only cache key would do exactly that,
    and the failure would be invisible until someone's key stopped working.
    """
    mine = _legacy_token(user_id, "agent")
    theirs = _legacy_token(other_user_id, "agent")

    verify_mock.side_effect = DifferentAuthError("x")
    # Warm the cache for BOTH before revoking, so a leak would be a cache leak
    # and not just a query bug.
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(mine)).status_code == 200
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(theirs)).status_code == 200

    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}
    assert (
        client.post(
            "/users/api-keys/legacy-revocations",
            headers=_headers(AUTH0_TOKEN),
            json={"name": "agent"},
        ).status_code
        == 201
    )

    verify_mock.side_effect = DifferentAuthError("x")
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(mine)).status_code == 401
    assert client.get(f"/{ORG}/optimize/s", headers=_headers(theirs)).status_code == 200


@patch("adopt.server.auth.verify_token")
def test_tombstone_does_not_block_a_new_v2_key_of_the_same_name(verify_mock):
    """A v2 key is validated by jti and never consults tombstones."""
    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}
    client.post(
        "/users/api-keys/legacy-revocations",
        headers=_headers(AUTH0_TOKEN),
        json={"name": "agent"},
    )

    fresh = _mint(verify_mock, "agent").json()["data"]
    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(fresh["token"])
        ).status_code
        == 200
    )


# --------------------------------------------------------------------------
# Scope enforcement, end to end
# --------------------------------------------------------------------------


@patch("adopt.server.auth.verify_token")
def test_read_scope_allows_reads_and_denies_writes(verify_mock):
    token = _mint(verify_mock, "reader", scopes=["studies:read"]).json()["data"][
        "token"
    ]

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 403
    )


@patch("adopt.server.auth.verify_token")
def test_write_scope_implies_read(verify_mock):
    token = _mint(verify_mock, "writer", scopes=["studies:write"]).json()["data"][
        "token"
    ]

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )


@patch("adopt.server.auth.verify_token")
def test_studies_scope_does_not_grant_responses(verify_mock):
    """The distinction the plan asks for: study structure without respondents."""
    token = _mint(verify_mock, "author", scopes=["studies:write"]).json()["data"][
        "token"
    ]

    assert (
        client.get(
            f"/{ORG}/studies/s/confs/general", headers=_headers(token)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/{ORG}/studies/s/ad-attributions", headers=_headers(token)
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/{ORG}/studies/s/recruitment-stats", headers=_headers(token)
        ).status_code
        == 403
    )
    # Nor does it let the key spend money.
    assert (
        client.post(
            f"/{ORG}/optimize/s/instruction", headers=_headers(token)
        ).status_code
        == 403
    )


@patch("adopt.server.auth.verify_token")
def test_unscoped_key_is_unrestricted(verify_mock):
    token = _mint(verify_mock, "full").json()["data"]["token"]

    for method, path in (
        ("get", f"/{ORG}/studies/s/confs/general"),
        ("post", f"/{ORG}/studies/s/confs/general"),
        ("get", f"/{ORG}/studies/s/ad-attributions"),
        ("post", f"/{ORG}/optimize/s/instruction"),
        ("get", f"/{ORG}/studies/s/unclassified"),
    ):
        res = getattr(client, method)(path, headers=_headers(token))
        assert res.status_code == 200, (method, path, res.status_code)


@patch("adopt.server.auth.verify_token")
def test_scoped_key_is_denied_on_an_unclassified_route(verify_mock):
    """Fail closed: a route nobody classified is unreachable for scoped keys."""
    token = _mint(verify_mock, "reader", scopes=["studies:read"]).json()["data"][
        "token"
    ]
    assert (
        client.get(
            f"/{ORG}/studies/s/unclassified", headers=_headers(token)
        ).status_code
        == 403
    )


@patch("adopt.server.auth.verify_token")
def test_scoped_key_cannot_mint_or_list_keys(verify_mock):
    """`auth` is never implicitly granted."""
    token = _mint(verify_mock, "agent", scopes=["studies:write"]).json()["data"][
        "token"
    ]

    assert (
        client.post(
            "/users/api-key", headers=_headers(token), json={"name": "escalation"}
        ).status_code
        == 403
    )
    assert client.get("/users/api-keys", headers=_headers(token)).status_code == 403


@patch("adopt.server.auth.verify_token")
def test_minting_is_attenuating(verify_mock):
    """A key may only mint a key no more powerful than itself."""
    parent = _mint(
        verify_mock, "parent", scopes=["studies:write", "auth:write"]
    ).json()["data"]["token"]

    # Narrower: fine.
    ok = client.post(
        "/users/api-key",
        headers=_headers(parent),
        json={"name": "child", "scopes": ["studies:read"]},
    )
    assert ok.status_code == 201

    # Wider: refused.
    wider = client.post(
        "/users/api-key",
        headers=_headers(parent),
        json={"name": "greedy", "scopes": ["responses:read"]},
    )
    assert wider.status_code == 403

    # Unscoped means FULL ACCESS, so a scoped key cannot mint one.
    unscoped = client.post(
        "/users/api-key", headers=_headers(parent), json={"name": "unscoped"}
    )
    assert unscoped.status_code == 403


@patch("adopt.server.auth.verify_token")
def test_unknown_scope_is_rejected_at_mint(verify_mock):
    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}
    res = client.post(
        "/users/api-key",
        headers=_headers(AUTH0_TOKEN),
        json={"name": "typo", "scopes": ["studies:reed"]},
    )
    assert res.status_code == 400
    assert "unknown scope" in res.json()["detail"]


@patch("adopt.server.auth.verify_token")
def test_auth0_sessions_are_never_scope_restricted(verify_mock):
    """An RS256 dashboard session has no scopes claim, so nothing changes for it."""
    verify_mock.side_effect = None
    verify_mock.return_value = {"sub": user_id}

    assert (
        client.post(
            f"/{ORG}/studies/s/confs/general", headers=_headers(AUTH0_TOKEN)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/{ORG}/studies/s/unclassified", headers=_headers(AUTH0_TOKEN)
        ).status_code
        == 200
    )


def test_health_is_reachable_without_a_token():
    assert client.get("/health").status_code == 200
