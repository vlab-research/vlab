"""Tests for the connected-accounts routes (`server/accounts.py`).

Phase C of `planning/mcp-full-coverage.md`.

The properties worth asserting, and why each one is here:

- **the secret never appears in a response body**, on any type, on any route,
  including every error branch. That is the whole reason this port exists
  rather than pointing an agent at the Go `/accounts`, which returns `details`
  verbatim to the browser. Asserted exhaustively rather than spot-checked, the
  same way `test_meta.py` asserts it for the Facebook token.
- the upsert replaces in ONE transaction, and leaves exactly one row.
- the two refusals (`facebook`, `api_key`) are 400s that say where to go
  instead, because a silent accept would store a credential that fails much
  later somewhere else.
- an unknown or misspelled credential field is a 422, never a dropped key: a
  credential missing the one field that matters is a 401 from a third party
  hours later.
- cross-user isolation: another user's account is invisible to the list, and
  deleting it is a 404 rather than a 403, so this is not an oracle for whether
  someone else's credential exists.
- API-token rows and legacy tombstones, which live in the same table, are NOT
  accounts and must not leak into the listing or be deletable through it.
"""

import os
import uuid
from datetime import datetime, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
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

from . import accounts as acc  # noqa: E402
from . import api_keys as ak  # noqa: E402
from .auth import DifferentAuthError, generate_api_token  # noqa: E402

USER = "test|accounts"
OTHER_USER = "test|accounts-other"

# Distinctive so "is the secret in this response?" is an exact substring test
# with no chance of a coincidental match.
SECRET = "SUPER-SECRET-CREDENTIAL-4f7a"


def _make_app() -> FastAPI:
    app = FastAPI()
    # First-added is innermost, exactly as in server.py.
    ak.add_scope_enforcement(app)
    app.include_router(acc.router)
    app.include_router(ak.router)
    return app


APP = _make_app()
client = TestClient(APP, raise_server_exceptions=False)


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
    """Every token here is a vlab API key, never an Auth0 one; `verify_tokens`
    tries Auth0 first, which would fetch a JWKS over the network."""
    with patch("adopt.server.auth.verify_token") as m:
        m.side_effect = DifferentAuthError("not an auth0 token")
        yield m


def _token(user_id=USER, scopes=None, name=None):
    token, _ = generate_api_token(
        user_id=user_id, name=name or str(uuid.uuid4()), scopes=scopes
    )
    return {"Authorization": f"Bearer {token}"}


def _row(user_id, entity, key, details):
    execute(
        db_conf,
        "insert into credentials (user_id, entity, key, details) values (%s,%s,%s,%s)",
        (user_id, entity, key, orjson.dumps(details).decode("utf8")),
    )


def _stored(user_id=USER, entity=None):
    """The user's credential rows, WITHOUT the rows minting a key leaves behind.

    `generate_api_token` persists an `api_token` row of its own, so every test
    that authenticates with a freshly minted key has one; counting rows without
    excluding it would be counting the test's own scaffolding. Pass `entity` to
    look at exactly one kind, including those.
    """
    if entity is not None:
        q = (
            "select entity, key, details, created from credentials "
            "where user_id = %s and entity = %s order by key"
        )
        vals = (user_id, entity)
    else:
        q = (
            "select entity, key, details, created from credentials "
            "where user_id = %s and entity != ALL(%s) order by entity, key"
        )
        vals = (user_id, [ak.API_TOKEN_ENTITY, ak.REVOKED_ENTITY])

    return list(query(db_conf, q, vals, as_dict=True))


# --------------------------------------------------------------------------
# Listing
# --------------------------------------------------------------------------

# One row of every shape the table can hold for a user, so that "no secret
# leaks" is asserted over the whole surface rather than over one provider.
EVERY_TYPE = {
    "typeform": {"key": SECRET},
    "fly": {"api_key": SECRET},
    "qualtrics": {"api_key": SECRET},
    "alchemer": {"api_token": SECRET, "api_token_secret": SECRET},
    "facebook": {"access_token": SECRET, "expires_in": 5184000, "token_type": "bearer"},
    "facebook_ad_user": {"access_token": SECRET},
    "api_key": {"token": SECRET, "id": "the-jti"},
}


def _seed_every_type(user_id=USER):
    for entity, details in EVERY_TYPE.items():
        _row(user_id, entity, f"{entity}-cred", details)


def test_list_returns_name_type_and_created_and_never_a_secret():
    _seed_every_type()

    res = client.get("/users/accounts", headers=_token())

    assert res.status_code == 200, res.text
    assert SECRET not in res.text
    rows = res.json()["data"]
    assert len(rows) == len(EVERY_TYPE)
    for row in rows:
        assert set(row) == {"name", "auth_type", "created", "id"}
        assert row["created"] is not None


@pytest.mark.parametrize("entity", sorted(EVERY_TYPE))
def test_no_credential_field_leaks_for_any_type(entity):
    """Per type, so a provider added to the allowlist without a stripping rule
    fails here rather than in production."""
    _row(USER, entity, "c", EVERY_TYPE[entity])

    body = client.get("/users/accounts", headers=_token()).json()["data"]

    assert body[0]["name"] == "c"
    assert SECRET not in orjson.dumps(body).decode("utf8")


def test_an_api_key_account_carries_its_id_but_not_its_token():
    """`details.id` is the minted key's `jti` -- not a secret, and the field
    that makes the bookkeeping row useful at all. `details.token` is."""
    _row(USER, "api_key", "agent", {"token": SECRET, "id": "jti-123"})

    row = client.get("/users/accounts", headers=_token()).json()["data"][0]

    assert row["id"] == "jti-123"
    assert SECRET not in orjson.dumps(row).decode("utf8")


def test_other_types_report_no_id():
    _row(USER, "typeform", "tf", {"key": SECRET})

    row = client.get("/users/accounts", headers=_token()).json()["data"][0]

    assert row["id"] is None


def test_list_is_sorted_by_type_then_name():
    _row(USER, "typeform", "b", {"key": "x"})
    _row(USER, "typeform", "a", {"key": "x"})
    _row(USER, "fly", "z", {"api_key": "x"})

    rows = client.get("/users/accounts", headers=_token()).json()["data"]

    assert [(r["auth_type"], r["name"]) for r in rows] == [
        ("fly", "z"),
        ("typeform", "a"),
        ("typeform", "b"),
    ]


def test_list_filters_by_auth_type():
    _seed_every_type()

    rows = client.get(
        "/users/accounts", params={"auth_type": "typeform"}, headers=_token()
    ).json()["data"]

    assert [r["auth_type"] for r in rows] == ["typeform"]


def test_an_unknown_filter_is_an_empty_list_not_an_error():
    """ "you have no Qualtrics accounts" and "Qualtrics is not a thing" have the
    same fix -- add one -- so they get the same answer."""
    _seed_every_type()

    res = client.get(
        "/users/accounts", params={"auth_type": "nonsense"}, headers=_token()
    )

    assert res.status_code == 200
    assert res.json()["data"] == []


def test_api_tokens_and_tombstones_are_not_accounts():
    """They live in the same table and are `list_api_keys`'s business. Listing
    them here would report the same key twice under two shapes, and offer a
    DELETE that looks like revocation and is not."""
    _row(USER, ak.API_TOKEN_ENTITY, "agent", {"jti": "j", "name": "agent"})
    _row(USER, ak.REVOKED_ENTITY, "old", {})
    _row(USER, "typeform", "tf", {"key": SECRET})

    rows = client.get("/users/accounts", headers=_token()).json()["data"]

    assert [r["auth_type"] for r in rows] == ["typeform"]


def test_filtering_cannot_reach_a_row_the_listing_hides():
    """The filter is ANDed with the allowlist, not substituted for it."""
    _row(USER, ak.API_TOKEN_ENTITY, "agent", {"jti": "j"})

    rows = client.get(
        "/users/accounts",
        params={"auth_type": ak.API_TOKEN_ENTITY},
        headers=_token(),
    ).json()["data"]

    assert rows == []


def test_list_is_empty_for_a_user_with_nothing():
    assert client.get("/users/accounts", headers=_token()).json()["data"] == []


# --------------------------------------------------------------------------
# Creating
# --------------------------------------------------------------------------

VALID = {
    "typeform": {"key": SECRET},
    "fly": {"api_key": SECRET},
    "qualtrics": {"api_key": SECRET},
    "alchemer": {"api_token": SECRET, "api_token_secret": SECRET},
}


@pytest.mark.parametrize("auth_type", sorted(VALID))
def test_create_stores_the_credential_and_echoes_no_secret(auth_type):
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "main", "auth_type": auth_type, "credentials": VALID[auth_type]},
    )

    assert res.status_code == 201, res.text
    assert SECRET not in res.text
    assert res.json()["data"]["name"] == "main"
    assert res.json()["data"]["auth_type"] == auth_type

    stored = _stored()
    assert len(stored) == 1
    assert stored[0]["entity"] == auth_type
    assert stored[0]["details"] == VALID[auth_type]


def test_create_response_shape_matches_the_list_shape():
    """A create that answered with a different shape than the list would make a
    caller parse two things."""
    made = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "m", "auth_type": "fly", "credentials": {"api_key": "k"}},
    ).json()["data"]

    listed = client.get("/users/accounts", headers=_token()).json()["data"][0]

    assert set(made) == set(listed)
    assert made["name"] == listed["name"]
    assert made["auth_type"] == listed["auth_type"]


def test_create_upserts_and_leaves_exactly_one_row():
    """Posting a name that exists REPLACES it -- `unique_entity_key_per_user`
    means an insert could not have succeeded anyway, and there is no update
    route on either service."""
    for secret in ("first", "second"):
        res = client.post(
            "/users/accounts",
            headers=_token(),
            json={
                "name": "main",
                "auth_type": "typeform",
                "credentials": {"key": secret},
            },
        )
        assert res.status_code == 201, res.text

    stored = _stored()
    assert len(stored) == 1
    assert stored[0]["details"] == {"key": "second"}


def test_the_upsert_is_atomic_so_a_failed_insert_keeps_the_old_row():
    """The difference from the Go handler, which issues the DELETE and the
    INSERT as two loose statements: a failure between them leaves the user with
    NO credential under a name a study still points at.

    Forced by making the INSERT raise. If the two statements were not in one
    transaction the DELETE would have committed on its own and the row would be
    gone; because they are, it rolls back.
    """
    import psycopg

    # Minted OUTSIDE the patch: `generate_api_token` writes a credentials row
    # of its own, and it would be caught by the sabotage below.
    headers = _token()
    client.post(
        "/users/accounts",
        headers=headers,
        json={"name": "main", "auth_type": "typeform", "credentials": {"key": "old"}},
    )

    real_execute = psycopg.Cursor.execute

    def boom(self, *args, **kwargs):
        # Let the DELETE through, blow up on the INSERT. `RETURNING created` is
        # what makes this `upsert_account`'s insert and no other.
        if "RETURNING created" in str(args[0] if args else ""):
            raise RuntimeError("insert failed")
        return real_execute(self, *args, **kwargs)

    with patch.object(psycopg.Cursor, "execute", boom):
        res = client.post(
            "/users/accounts",
            headers=headers,
            json={
                "name": "main",
                "auth_type": "typeform",
                "credentials": {"key": "new"},
            },
        )

    assert res.status_code == 500
    stored = _stored()
    assert len(stored) == 1
    assert stored[0]["details"] == {"key": "old"}


def test_two_types_may_share_a_name():
    """`(user_id, entity, key)` is the address, so `main` under typeform and
    `main` under fly are two accounts."""
    for auth_type, creds in (("typeform", {"key": "a"}), ("fly", {"api_key": "b"})):
        client.post(
            "/users/accounts",
            headers=_token(),
            json={"name": "main", "auth_type": auth_type, "credentials": creds},
        )

    assert len(_stored()) == 2


def test_facebook_is_refused_with_the_reason():
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={
            "name": "fb",
            "auth_type": "facebook",
            "credentials": {"access_token": SECRET},
        },
    )

    assert res.status_code == 400
    assert "OAuth" in res.json()["detail"]
    assert "dashboard" in res.json()["detail"]
    assert _stored() == []


def test_api_key_accounts_are_refused_and_point_at_the_mint_route():
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={
            "name": "agent",
            "auth_type": "api_key",
            "credentials": {"token": SECRET, "id": "x"},
        },
    )

    assert res.status_code == 400
    assert "/users/api-key" in res.json()["detail"]
    assert _stored() == []


def test_an_unknown_auth_type_names_the_creatable_ones():
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "x", "auth_type": "surveymonkey", "credentials": {}},
    )

    assert res.status_code == 400
    for creatable in acc.CREATABLE:
        assert creatable in res.json()["detail"]


@pytest.mark.parametrize(
    "auth_type,credentials",
    [
        ("typeform", {}),
        ("typeform", {"key": ""}),
        ("typeform", {"keys": "x"}),
        ("typeform", {"key": "x", "extra": "y"}),
        ("fly", {"key": "x"}),
        ("alchemer", {"api_token": "x"}),
        ("alchemer", {"api_token": "x", "api_token_secret": ""}),
    ],
)
def test_a_credential_that_does_not_match_the_shape_is_a_422(auth_type, credentials):
    """An unknown key is REFUSED, never dropped: a credential missing the one
    field that matters fails hours later as a 401 from a third party, with
    nothing pointing back here."""
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "x", "auth_type": auth_type, "credentials": credentials},
    )

    assert res.status_code == 422, res.text
    assert _stored() == []


def test_the_422_detail_carries_the_field_location():
    """FastAPI's per-field shape, so a client parsing `loc` off any other 422
    on this service can parse it off this one."""
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "x", "auth_type": "alchemer", "credentials": {"api_token": "t"}},
    )

    detail = res.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"][:2] == ["body", "credentials"]
    assert "api_token_secret" in detail[0]["loc"]


def test_a_blank_name_is_rejected():
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "   ", "auth_type": "fly", "credentials": {"api_key": "k"}},
    )

    assert res.status_code == 422
    assert _stored() == []


def test_the_name_is_stored_trimmed():
    """So that `credentials_key: "main"` in a conf finds an account added as
    `" main "`; the Go route stores the name untrimmed and the lookup is exact."""
    client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": " main ", "auth_type": "fly", "credentials": {"api_key": "k"}},
    )

    assert _stored()[0]["key"] == "main"


def test_an_unknown_top_level_field_is_refused():
    res = client.post(
        "/users/accounts",
        headers=_token(),
        json={
            "name": "x",
            "auth_type": "fly",
            "credentials": {"api_key": "k"},
            "authType": "fly",
        },
    )

    assert res.status_code == 422


# --------------------------------------------------------------------------
# Deleting
# --------------------------------------------------------------------------


def test_delete_removes_the_row_and_answers_204():
    _row(USER, "typeform", "tf", {"key": SECRET})

    res = client.delete("/users/accounts/typeform/tf", headers=_token())

    assert res.status_code == 204
    assert res.text == ""
    assert _stored() == []


def test_deleting_something_that_is_not_there_is_a_404():
    res = client.delete("/users/accounts/typeform/nope", headers=_token())

    assert res.status_code == 404
    assert "typeform" in res.json()["detail"]


def test_delete_is_addressed_by_type_and_name_together():
    """The same name under two types is two accounts, so deleting one must
    leave the other."""
    _row(USER, "typeform", "main", {"key": "a"})
    _row(USER, "fly", "main", {"api_key": "b"})

    assert (
        client.delete("/users/accounts/fly/main", headers=_token()).status_code == 204
    )

    assert [r["entity"] for r in _stored()] == ["typeform"]


def test_a_facebook_account_is_deletable():
    """The dashboard allows it. The cost -- a study whose
    `general.credentials_key` names it stops being able to reconcile -- is in
    the tool and CLI descriptions, not enforced here."""
    _row(USER, "facebook", "fb", {"access_token": SECRET})

    assert (
        client.delete("/users/accounts/facebook/fb", headers=_token()).status_code
        == 204
    )


def test_an_api_token_row_cannot_be_deleted_through_the_accounts_route():
    """Revocation is `DELETE /users/api-keys/{id}`, keyed on the jti. A path
    that looked like it revoked a key and merely 404'd would be worse than one
    that says so."""
    _row(USER, ak.API_TOKEN_ENTITY, "agent", {"jti": "j"})

    res = client.delete(
        f"/users/accounts/{ak.API_TOKEN_ENTITY}/agent", headers=_token()
    )

    assert res.status_code == 400
    assert "/users/api-keys" in res.json()["detail"]
    assert len(_stored(entity=ak.API_TOKEN_ENTITY)) == 2  # the seeded row, and
    # the row `_token()` minted to authenticate this very request.


# --------------------------------------------------------------------------
# Ownership
# --------------------------------------------------------------------------


def test_another_users_accounts_are_invisible():
    _row(OTHER_USER, "typeform", "theirs", {"key": SECRET})
    _row(USER, "fly", "mine", {"api_key": "k"})

    rows = client.get("/users/accounts", headers=_token()).json()["data"]

    assert [r["name"] for r in rows] == ["mine"]


def test_deleting_another_users_account_is_a_404_and_leaves_it_alone():
    """404 rather than 403, so this is not an oracle for whether someone else
    has a credential by that name."""
    _row(OTHER_USER, "typeform", "theirs", {"key": SECRET})

    res = client.delete("/users/accounts/typeform/theirs", headers=_token())

    assert res.status_code == 404
    assert len(_stored(OTHER_USER)) == 1


def test_one_users_upsert_does_not_touch_anothers_same_named_account():
    _row(OTHER_USER, "typeform", "main", {"key": "theirs"})

    client.post(
        "/users/accounts",
        headers=_token(),
        json={"name": "main", "auth_type": "typeform", "credentials": {"key": "mine"}},
    )

    assert _stored(OTHER_USER)[0]["details"] == {"key": "theirs"}
    assert _stored(USER)[0]["details"] == {"key": "mine"}


# --------------------------------------------------------------------------
# Scopes
# --------------------------------------------------------------------------


def test_an_auth_read_key_can_list_but_not_create_or_delete():
    """`auth` is never implicitly granted and `write` is not implied by
    `read`; this is the pair that makes a read-only credentials key useful."""
    headers = _token(scopes=["auth:read"])

    assert client.get("/users/accounts", headers=headers).status_code == 200

    created = client.post(
        "/users/accounts",
        headers=headers,
        json={"name": "x", "auth_type": "fly", "credentials": {"api_key": "k"}},
    )
    assert created.status_code == 403
    assert "auth:write" in created.json()["detail"]

    deleted = client.delete("/users/accounts/fly/x", headers=headers)
    assert deleted.status_code == 403


def test_an_auth_write_key_can_do_all_three():
    """`write` implies `read` on the same resource, here as everywhere."""
    headers = _token(scopes=["auth:write"])

    assert client.get("/users/accounts", headers=headers).status_code == 200
    assert (
        client.post(
            "/users/accounts",
            headers=headers,
            json={"name": "x", "auth_type": "fly", "credentials": {"api_key": "k"}},
        ).status_code
        == 201
    )
    assert client.delete("/users/accounts/fly/x", headers=headers).status_code == 204


@pytest.mark.parametrize(
    "path,method",
    [
        ("/users/accounts", "get"),
        ("/users/accounts", "post"),
        ("/users/accounts/fly/x", "delete"),
    ],
)
def test_a_studies_key_is_denied_and_told_which_scope(path, method):
    """A key that can author studies must not be able to read, replace or
    delete the researcher's third-party credentials."""
    headers = _token(scopes=["studies:write"])

    # No body: the middleware answers before the route parses one, which is
    # exactly the property being asserted -- a denied key never reaches the
    # handler. (`TestClient.delete` does not take `json=` either.)
    res = getattr(client, method)(path, headers=headers)

    assert res.status_code == 403, res.text
    assert "auth:" in res.json()["detail"]


def test_an_unscoped_key_is_unrestricted_here_too():
    headers = _token(scopes=None)

    assert client.get("/users/accounts", headers=headers).status_code == 200


# --------------------------------------------------------------------------
# The stripping function, directly
# --------------------------------------------------------------------------


def test_a_provider_added_without_a_stripping_rule_is_stripped_bare():
    """Allowlist, not denylist: `_public_row` returns nothing beyond the three
    common fields unless a type is deliberately given more."""
    row = acc._public_row(
        {
            "key": "n",
            "entity": "something-new",
            "created": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "details": {"secret": SECRET, "account_id": "123"},
        }
    )

    assert row == {
        "name": "n",
        "auth_type": "something-new",
        "created": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
