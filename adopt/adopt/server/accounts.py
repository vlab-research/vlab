"""Connected accounts: the named third-party credentials a study refers to.

Phase C of `planning/mcp-full-coverage.md`. Port of the Go dashboard API's
`/accounts` (`api/internal/server/handler/accounts/`), which is Auth0-only,
onto the conf service, which accepts a vlab API key -- so an agent can find
out, and create, the `credentials_key` a `data-sources` entry needs, instead of
asking a human to click through the dashboard's Accounts page.

WHAT AN ACCOUNT IS
------------------

One row in `credentials`, mapped the way the Go service maps it
(`api/internal/storage/account.go`, whose comment is the spec):

    authType  ->  entity      the provider: typeform, fly, alchemer, ...
    name      ->  key         the caller's own label for this credential
    creds     ->  details     the JSONB secret
    userId    ->  user_id     the owner

`unique_entity_key_per_user UNIQUE(user_id, entity, key)` is what makes
`(auth_type, name)` the address of an account, and it is why the create route
is an upsert rather than a plain insert.

The NAME is the point. `data-sources[].credentials_key` and, for Facebook,
`general.credentials_key` are that `key` -- so a study cannot extract responses
or reconcile ads until a credential of the right name exists, and until this
module there was no API-key-reachable way to find out what names existed
(`meta_credentials` answered it for Facebook alone) or to make one.

WHAT IS NEVER RETURNED
----------------------

The secret. Not on the list, not on the create response, not in an error. The
Go route returns `details` verbatim to the browser -- every token, in a list
response -- and that is exactly the behaviour this port does NOT reproduce: an
API key reaches this service, agents hold API keys, and an agent that lists
accounts should not thereby be handed every third-party token the researcher
owns. `list_facebook_credentials` and `meta.list_credentials` already made that
choice for Facebook; this is the same choice for every provider.

WHAT IS REFUSED, AND WHY
------------------------

* `facebook` -- the token has to come out of Meta's OAuth code exchange, which
  needs a browser and a human (`POST /facebook/token` on the Go service).
  Accepting a `facebook` account here would let a caller store any string as a
  Facebook token, and the failure would surface hours later as an
  unauthenticated Graph call from the optimizer. Facebook connect stays
  human-only; `agent-api.md` §7 item 2.
* `api_key` -- an `api_key` account is what the dashboard writes AFTER minting a
  vlab key, as a record of it. Minting is `POST /users/api-key`
  (`create_api_key`), which returns the token once; writing the account row by
  hand would store a token this service already refuses to store for its own
  keys (only a `jti` is persisted -- `api_keys.py`, "THE MODEL"). Deleting such
  a row is allowed, because it is a bookkeeping row: note that deleting it does
  NOT revoke the key. `revoke_api_key` does.

Both refusals are 400s that name the alternative, rather than silent drops.
"""

import asyncio
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .db import ACCOUNT_ENTITIES, delete_account, list_accounts, upsert_account
from .deps import User, get_current_user

router = APIRouter()


# --------------------------------------------------------------------------
# The credential shapes, per auth type
# --------------------------------------------------------------------------

# Ported field for field from `inference/sources/types/*.go` (the structs the
# extraction workers actually unmarshal a `details` blob into) and from
# `api/internal/types/account.go`. Those files carry a "NOTE: This is an API
# interface that is depended on externally" warning for a reason: a credential
# stored under a key the worker does not read is a data source that silently
# never extracts.
#
# `extra="forbid"` so a misspelled field is a 422 rather than a credential that
# is missing the one key that matters. That is the same decision the strict conf
# twins make (`study_conf_strict.py`), for the same reason: the table has no
# delete and a bad write can only be written over.
#
# Every field is `min_length=1`: an empty secret is never what anybody meant,
# and it would produce a 401 from the third party rather than an error here.


class _StrictCreds(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TypeformCredentials(_StrictCreds):
    """`sourcetypes.TypeformCredentials`. A personal access token."""

    key: str = Field(min_length=1)


class FlyCredentials(_StrictCreds):
    """`sourcetypes.FlyCredentials`."""

    api_key: str = Field(min_length=1)


class QualtricsCredentials(_StrictCreds):
    """`sourcetypes.QualtricsCredentials`."""

    api_key: str = Field(min_length=1)


class AlchemerCredentials(_StrictCreds):
    """`sourcetypes.AlchemerCreds`. Both halves are required by the API."""

    api_token: str = Field(min_length=1)
    api_token_secret: str = Field(min_length=1)


# The auth types this route will WRITE. Deliberately not the same set as
# `db.ACCOUNT_ENTITIES`, which is what it will LIST: `facebook`,
# `facebook_ad_user` and `api_key` rows are real accounts that belong in a
# listing and must not be creatable here. See the module docstring.
CREATABLE: Dict[str, Any] = {
    "typeform": TypeformCredentials,
    "fly": FlyCredentials,
    "qualtrics": QualtricsCredentials,
    "alchemer": AlchemerCredentials,
}

# The 400s for the two refused types, worded so the caller knows where to go
# instead. Kept as data rather than as branches so that the list route, the
# create route and the tool description cannot drift apart on what is refused.
REFUSED: Dict[str, str] = {
    "facebook": (
        "A Facebook account cannot be created through the API. The access "
        "token has to come from Meta's OAuth code exchange, which needs a "
        "browser and a human: connect it on the dashboard's Accounts page, "
        "then `list_accounts` (or `meta_credentials`) will show its name. "
        "Storing an arbitrary string as a Facebook token would fail later, "
        "from inside the optimizer, as an unexplained Graph rejection."
    ),
    "api_key": (
        "An 'api_key' account is the dashboard's record of a vlab API key, "
        "written after minting one. Mint a key with POST /users/api-key "
        "(the `create_api_key` tool, or `vlab keys create`) -- it returns the "
        "token once. This service never stores an API key's token, only its "
        "id, so writing one here would store a secret it deliberately does not "
        "keep for its own keys."
    ),
}


# --------------------------------------------------------------------------
# Request and response models
# --------------------------------------------------------------------------


class CreateAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    auth_type: str
    # Validated against the per-type model in the handler, not here: which
    # model applies depends on a sibling field, and a discriminated union would
    # have had to name the discriminator `auth_type` inside `credentials`,
    # which is not the shape the Go route or the dashboard uses.
    credentials: Dict[str, Any]

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v


class AccountResource(BaseModel):
    """One account, WITHOUT its secret. See `_public_row`."""

    name: str
    auth_type: str
    created: Optional[datetime] = None
    # Only ever set for `api_key` accounts; see `_public_row`.
    id: Optional[str] = None


class ListAccountsResponse(BaseModel):
    data: List[AccountResource]


class CreateAccountResponse(BaseModel):
    data: AccountResource


# --------------------------------------------------------------------------
# Stripping
# --------------------------------------------------------------------------


def _public_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """One `credentials` row as the non-secret fields of an account.

    The default is NOTHING beyond `name`, `auth_type` and `created` -- allowlist,
    not denylist. Every field of every credential shape above is a secret
    (typeform `key`, fly/qualtrics `api_key`, alchemer's two, Facebook's
    `access_token`), so there is nothing else to show and no per-type branch to
    get wrong. A provider added later is stripped bare until somebody
    deliberately adds it here, which is the direction that mistake should point.

    The ONE exception is `api_key`, whose `details.id` is the minted key's
    `jti`. That is not a secret -- `list_api_keys` returns it as `id`, and it is
    what `revoke_api_key` takes -- and it is the field that makes an `api_key`
    account row useful at all: without it the row is a name with nothing behind
    it. Its sibling `details.token` IS the secret and is never read here.

    Facebook rows deliberately get nothing extra either, so that this and
    `GET /{org}/meta/credentials` describe a Facebook credential the same way.
    (`details.expires_in` is non-secret, but it is a duration measured from an
    issue time the row does not record -- `created` is when the row was
    inserted, which the Go path and a re-connect both move -- so publishing it
    would read as an expiry date and not be one.)
    """
    details = row.get("details") or {}
    public: Dict[str, Any] = {
        "name": row["key"],
        "auth_type": row["entity"],
        "created": row.get("created"),
    }

    if row["entity"] == "api_key":
        key_id = details.get("id")
        public["id"] = str(key_id) if key_id is not None else None

    return public


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
#
# All three live under `/users/...`, so `api_keys.required_scope` already
# classifies them `auth:read` / `auth:write` by the method, with no branch of
# its own -- the same way `/users/api-key` and `/users/api-keys` are classified.
# `test_api_keys.py` pins that for these three paths.
#
# `auth` is the right resource and not a new one: an account IS a credential,
# `auth` is the resource that is never implicitly granted (`api_keys.py`,
# "SCOPES"), and a key that can read a study has no business enumerating the
# researcher's third-party credentials.
#
# There is no org segment because the table has no usable one: `credentials.org_id`
# exists and is never populated (see `db.list_accounts`). Ownership is
# `user_id = user.user_id`, in SQL, on every query.


@router.get("/users/accounts", response_model=ListAccountsResponse)
async def list_accounts_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    auth_type: Optional[str] = Query(
        default=None, description="Only accounts of this type."
    ),
):
    """The caller's connected accounts. NEVER their secrets. Needs `auth:read`.

    Sorted by `(auth_type, name)`. `?auth_type=` filters; an unknown one is an
    empty list rather than an error, because "you have no typeform accounts"
    and "typeform is not a thing" are the same actionable answer -- add one.
    """

    def _work():
        rows = list_accounts(user.user_id, auth_type)
        return {"data": [_public_row(r) for r in rows]}

    # `psycopg` is synchronous and every other read on this service that is not
    # trivially fast goes to a thread. Same reason `meta.list_credentials` does.
    return await asyncio.to_thread(_work)


@router.post("/users/accounts", status_code=201, response_model=CreateAccountResponse)
async def create_account_endpoint(
    body: CreateAccountRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    """Connect an account, or replace one of the same name. Needs `auth:write`.

    UPSERT, exactly as the Go route is: posting a name that already exists
    under the same `auth_type` REPLACES that credential. There is no separate
    update route on either service, and `unique_entity_key_per_user` means an
    insert could not have succeeded anyway.

    The replace is one transaction here where Go's is two loose statements; see
    `db.upsert_account` for why that difference is worth having.
    """
    name = body.name.strip()
    auth_type = body.auth_type

    if auth_type in REFUSED:
        raise HTTPException(status_code=400, detail=REFUSED[auth_type])

    model = CREATABLE.get(auth_type)
    if model is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown auth_type: {auth_type!r}. Creatable types are: "
                + ", ".join(sorted(CREATABLE))
                + ". Facebook and api_key accounts exist but are not creatable "
                "here; ask for one of those by name to be told why."
            ),
        )

    try:
        credentials = model(**body.credentials)
    except Exception as e:
        # 422 with the field errors, the shape every other body-parse failure on
        # this service produces. NOT 400: a caller distinguishing "the auth type
        # is wrong" from "the credential fields are wrong" is distinguishing two
        # different fixes.
        raise HTTPException(status_code=422, detail=_field_errors(e)) from e

    def _work():
        try:
            return upsert_account(
                user.user_id, auth_type, name, credentials.model_dump()
            )
        except psycopg.errors.ForeignKeyViolation as e:
            # `studies.credentials_key_exists` references `credentials(user_id,
            # entity, key)`, so the DELETE half of the upsert fails if a legacy
            # `studies` row still names this credential in its (vestigial)
            # `credentials_key` column. The modern create path leaves that
            # column NULL (`db.create_study`), so this is a legacy-row case
            # only -- but a 500 would say nothing about what to do.
            raise HTTPException(
                status_code=409,
                detail=(
                    f"The credential '{name}' cannot be replaced: a study row "
                    "still references it by its legacy `credentials_key` "
                    "column. Create it under a different name."
                ),
            ) from e

    created = await asyncio.to_thread(_work)

    # The same non-secret shape the list route returns, built from what was
    # sent rather than read back: a create that answered with a different shape
    # than the list would make a caller parse two things.
    return {
        "data": _public_row(
            {"key": name, "entity": auth_type, "created": created, "details": {}}
        )
    }


@router.delete("/users/accounts/{auth_type}/{name}", status_code=204)
async def delete_account_endpoint(
    auth_type: str,
    name: str,
    user: Annotated[User, Depends(get_current_user)],
):
    """Delete one account by `(auth_type, name)`. 204, or 404. Needs `auth:write`.

    Facebook accounts ARE deletable, which the dashboard also allows. It is
    worth knowing what it costs: a study whose `general.credentials_key` names
    the deleted credential can no longer authenticate to Meta, so the next
    reconcile fails, and re-creating it needs the dashboard's OAuth flow again.

    404 -- never 403 -- when there is no such row of YOURS, so this cannot be
    used to find out whether another user has an account by that name.
    """
    if auth_type not in ACCOUNT_ENTITIES:
        # 400 rather than 404: a type that is not an account type at all is a
        # typo in the request, not a missing row, and answering 404 would also
        # make `DELETE /users/accounts/api_token/agent` look like a revocation
        # that simply missed. Key revocation is `DELETE /users/api-keys/{id}`.
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown account type: {auth_type!r}. One of: "
                + ", ".join(sorted(ACCOUNT_ENTITIES))
                + ". To revoke a vlab API key use DELETE /users/api-keys/{id}."
            ),
        )

    def _work():
        try:
            return delete_account(user.user_id, auth_type, name)
        except psycopg.errors.ForeignKeyViolation as e:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"The credential '{name}' cannot be deleted: a study row "
                    "still references it by its legacy `credentials_key` "
                    "column."
                ),
            ) from e

    if not await asyncio.to_thread(_work):
        raise HTTPException(
            status_code=404,
            detail=f"No {auth_type} account named '{name}'.",
        )

    # No return: FastAPI serialises a returned None into a body, and a 204 must
    # not carry one. Same reason `api_keys.revoke_api_key` is explicit about it.


def _field_errors(exc: Exception) -> Any:
    """A pydantic `ValidationError` in FastAPI's 422 `detail` shape.

    A copy of `mcp_server._field_errors` in spirit and deliberately not an
    import of it: `server/` must not depend on the MCP module for anything a
    plain HTTP route needs, and this one prefixes `loc` with
    `["body", "credentials"]` because that is where the value actually came
    from in THIS route's body.
    """
    errors = getattr(exc, "errors", None)
    if errors is None:
        return str(exc)
    try:
        return [
            {**e, "loc": ["body", "credentials", *e.get("loc", ())]} for e in errors()
        ]
    except Exception:  # noqa: BLE001 -- never let error reporting raise
        return str(exc)
