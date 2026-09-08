"""`POST /mcp` -- the same MCP tools, served by the conf service itself.

Phase 4 of `planning/agent-study-authoring.md` §16; `planning/mcp.md` records
what shipped. The tools are `sdk/mcp_tools.py`, registered by the one function
both transports call, so this module adds a mount, a backend and a scope check
and nothing else. It is deliberately the ONLY file that imports both sides.

WHY THIS EXISTS ALONGSIDE `vlab mcp`
------------------------------------

`vlab mcp` is the same tools over stdio, and it is the better answer whenever
the caller can run Python: the researcher's key never leaves their machine, and
every tool goes through the service's real routes, so the scope enforcement is
the middleware's rather than a second copy of it. This transport is for clients
that cannot install anything -- they point at a URL and send a bearer token.

WHAT "IN PROCESS" COSTS, AND WHAT PAYS FOR IT
---------------------------------------------

`InProcessBackend` calls the FastAPI route *handlers* directly. Not the HTTP
routes -- a request that re-entered its own app would be a second event-loop
round trip per tool call for no gain -- and not the underlying database and Meta
code either, which would be a reimplementation of every handler's ownership
check, org check and error mapping. The handlers are plain `async def`s whose
only injected dependency is the authenticated `User`, so calling them is exactly
what the route does minus the transport.

The transport is where scopes are enforced, though. `scope_enforcement_middleware`
classifies by PATH, and every tool call arrives on the same path, so it can say
nothing useful about a request here; that is why `/mcp` is a *delegated* route in
`api_keys.DELEGATED_PATHS` (any authenticated key reaches it) and why
`mcp_tools.TOOL_SCOPES` is the real check, evaluated per call against the key's
own scopes with `api_keys.scopes_allow` -- the same function the routes use, so
`write` implies `read` and an absent scopes claim is unrestricted. A tool with no
entry in that table is denied, never allowed by default.

STATELESS
---------

`StreamableHTTPSessionManager(stateless=True)`: a fresh transport per request,
no session id, no event store, nothing to resume. The service runs several
replicas behind one ingress with no affinity, so a session pinned to a replica
would be a session that half the requests could not find. It also means the
`initialize` handshake is not required before a `tools/call`, which is what
makes a bare `POST /mcp` from a script work.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.requests import Request
from starlette.routing import Route

from ..sdk.client import http_error
from ..sdk.mcp_tools import TOOL_SCOPES, ScopeError, ToolEnv, build_server, use
from .api_keys import scopes_allow, scopes_for_token
from .deps import User, get_current_user

# The path. One constant, because `api_keys.DELEGATED_PATHS` has to agree with
# it: if the mount moves and the classification does not, every scoped key
# starts getting a 403 from the middleware instead of reaching a tool.
MCP_PATH = "/mcp"


# --------------------------------------------------------------------------
# The in-process backend
# --------------------------------------------------------------------------


def _wire_errors(fn):
    """Turn a handler's `HTTPException` into the exception the wire would raise.

    A tool must not be able to tell which transport it is on. `get_study_id`
    raises `HTTPException(404)` whether it is reached through a route or
    called directly, and a tool that caught `NotFoundError` on one transport and
    `HTTPException` on the other would be two implementations again.
    """

    async def wrapped(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except HTTPException as e:
            raise http_error(
                e.status_code, e.detail, "IN-PROCESS", f"{MCP_PATH}:{fn.__name__}"
            ) from e

    return wrapped


class InProcessBackend:
    """`VlabClient`'s surface, answered by calling the route handlers.

    Method for method and return shape for return shape with `VlabClient`,
    including where it unwraps the `{"data": ...}` envelope and where it does
    not: `meta_credentials` unwraps, `meta_adaccounts` keeps the envelope for
    its `paging`. A tool sees the same values either way, which is the whole
    contract.

    Handlers are imported inside the methods, not at module scope, because
    `server.py` imports THIS module to mount the route. The import is also
    expensive -- `server.py` pulls in `adopt.malaria` and so cvxpy -- and the
    process that serves `/mcp` has paid for it already by the time a tool runs.
    """

    def __init__(self, user: User, token: Optional[str] = None) -> None:
        self.user = user

        # THE CALLER'S RAW BEARER TOKEN, and it is load-bearing for exactly one
        # method: `create_api_key`.
        #
        # Every other handler here needs only the authenticated `User`. The
        # mint route needs more -- it ATTENUATES, so it has to know the scopes
        # of the key doing the minting, and it gets them by calling
        # `scopes_for_token` on the credentials FastAPI injected. `User` does
        # not carry scopes (`deps.py` builds it from `sub` alone), so without
        # the token this path would have to recompute attenuation from
        # something else, which is a second copy of the security rule that
        # matters most: an unrestricted key may mint anything, and a scoped key
        # must not mint beyond itself, identically on both transports.
        #
        # So the token is carried and handed straight back to the handler,
        # which then does byte for byte what the HTTP route does. It is the
        # same token that arrived in this request's `Authorization` header and
        # it lives no longer than the request; `scopes_for_token` is cached, so
        # the second call is a cache hit rather than a second verification.
        #
        # `None` is allowed so that a caller with no token (tests, and any
        # future in-process user of this class) gets a clear 403 from
        # `create_api_key` rather than a `TypeError`, and so that every other
        # method keeps working without one.
        self.token = token

    # -- discovery ---------------------------------------------------------

    @_wire_errors
    async def list_orgs(self) -> List[Dict[str, Any]]:
        from .studies import list_orgs_endpoint

        return (await list_orgs_endpoint(self.user))["data"]

    @_wire_errors
    async def list_studies(
        self,
        org_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        from .studies import DEFAULT_STUDIES_LIMIT, list_studies_endpoint

        # The defaults are FastAPI's `Query(...)` defaults, which only apply
        # when the framework parses a query string -- calling the handler
        # directly would otherwise pass the `Query` objects themselves into
        # psycopg. Same reason `meta_adaccounts` below spells out DEFAULT_LIMIT.
        body = await list_studies_endpoint(
            org_id,
            self.user,
            limit if limit is not None else DEFAULT_STUDIES_LIMIT,
            offset if offset is not None else 0,
        )
        return body["data"]

    # -- studies -----------------------------------------------------------

    @_wire_errors
    async def create_study(self, org_id: str, name: str) -> Dict[str, Any]:
        from .studies import CreateStudyRequest, create_study_endpoint

        body = await create_study_endpoint(
            org_id, CreateStudyRequest(name=name), self.user
        )
        return body["data"]

    @_wire_errors
    async def get_confs(self, org_id: str, slug: str) -> Dict[str, Any]:
        from .server import get_all_confs

        body = await get_all_confs(org_id, slug, self.user)
        return body["data"]

    @_wire_errors
    async def post_conf(
        self, org_id: str, slug: str, url_segment: str, config: Any
    ) -> Dict[str, Any]:
        from .server import CONF_POST_HANDLERS

        handler = CONF_POST_HANDLERS.get(url_segment)
        if handler is None:
            # The same answer the router gives for a path it does not serve,
            # rather than a 500 from a KeyError.
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No such conf section: {url_segment}. One of: "
                    + ", ".join(sorted(CONF_POST_HANDLERS))
                ),
            )

        route, adapter = handler
        # The route annotates the STRICT model, which forbids unknown keys, and
        # FastAPI is what parses the body into it on the HTTP path. Doing it
        # here is what reproduces the 422 -- and reproducing it matters: a
        # misspelled field has to be REJECTED rather than silently dropped,
        # which is the whole reason the strict twins exist. A `TypeAdapter`
        # rather than the model, because six of the nine sections are LISTS of
        # one.
        try:
            parsed = adapter.validate_python(config)
        except Exception as e:
            raise HTTPException(status_code=422, detail=_field_errors(e)) from e

        return await route(org_id, slug, parsed, self.user)

    @_wire_errors
    async def copy_from(
        self, org_id: str, slug: str, source_slug: str
    ) -> Dict[str, Any]:
        from .server import CopyFromConf, copy_confs_from

        body = await copy_confs_from(
            org_id, slug, CopyFromConf(source_study_slug=source_slug), self.user
        )
        return body["data"]

    # -- optimize ----------------------------------------------------------

    @_wire_errors
    async def plan(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        from .server import optimize_study

        result = await optimize_study(org_id, slug, self.user)
        return [i.model_dump() for i in result.data]

    @_wire_errors
    async def apply(
        self, org_id: str, slug: str, instruction: Dict[str, Any]
    ) -> Dict[str, Any]:
        from .server import OptimizeInstruction, run_instruction

        result = await run_instruction(
            org_id, slug, OptimizeInstruction(**dict(instruction)), self.user
        )
        return result.data.model_dump()

    @_wire_errors
    async def study_errors(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        from .server import get_errors

        result = await get_errors(org_id, slug, self.user)
        # `mode="json"` on every one of these, and it is not cosmetic: the HTTP
        # path serialises `last_seen`/`first_seen` through pydantic's JSON
        # serializer, so a plain `model_dump()` here would hand a tool
        # `datetime` objects on one transport and ISO strings on the other --
        # a difference no test of a single transport could see.
        return result.model_dump(mode="json")["errors"]

    # -- what the study is doing -------------------------------------------

    @_wire_errors
    async def current_data(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        from .server import get_current_data

        result = await get_current_data(org_id, slug, self.user)
        return result.model_dump(mode="json")["data"]

    @_wire_errors
    async def ad_attributions(self, org_id: str, slug: str) -> Dict[str, Any]:
        from .server import get_ad_attributions_json

        return (await get_ad_attributions_json(org_id, slug, self.user))["data"]

    # No `ad_attributions_csv` here, deliberately. `VlabClient` has one because
    # `vlab ad-attributions --csv` writes the server's own rendering of the
    # file; no TOOL asks for it -- a CSV blob is a worse table than a table --
    # so an in-process twin would be code no transport could reach, and the
    # first thing to rot. `mcp_tools`' backend contract says so too.

    @_wire_errors
    async def recruitment_stats(self, org_id: str, slug: str) -> Dict[str, Any]:
        from .server import get_recruitment_stats

        result = await get_recruitment_stats(org_id, slug, self.user)
        return result.model_dump(mode="json")["data"]

    @_wire_errors
    async def respondents_over_time(
        self, org_id: str, slug: str
    ) -> List[Dict[str, Any]]:
        from .server import get_segments_progress

        result = await get_segments_progress(org_id, slug, self.user)
        return result.model_dump(mode="json")["data"]

    @_wire_errors
    async def cost_over_time(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        from .server import get_cost_over_time

        result = await get_cost_over_time(org_id, slug, self.user)
        return result.model_dump(mode="json")["data"]

    # -- reports -----------------------------------------------------------

    @_wire_errors
    async def strata_progress(
        self, org_id: str, slug: str, history: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        from .strata_progress import DEFAULT_HISTORY, strata_progress_endpoint

        # The `Query(...)` default spelled out, for the same reason
        # `list_studies` spells its two out: FastAPI is not parsing a query
        # string here, so an unsupplied `history` would arrive at psycopg as
        # the `Query` object itself.
        body = await strata_progress_endpoint(
            org_id,
            slug,
            self.user,
            history if history is not None else DEFAULT_HISTORY,
        )
        # `mode="json"` so the remote transport hands a tool the same
        # JSON-able values the wire does -- `created` is already a string, but
        # dumping in python mode would leave anything added later as whatever
        # object pydantic holds, and the two transports would diverge silently.
        return body.model_dump(mode="json")["data"]

    # -- the Meta proxy ----------------------------------------------------

    @_wire_errors
    async def meta_credentials(self, org_id: str) -> List[Dict[str, Any]]:
        from .meta import list_credentials

        return (await list_credentials(org_id, self.user))["data"]

    @_wire_errors
    async def meta_adaccounts(
        self,
        org_id: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        from .meta import DEFAULT_LIMIT, list_ad_accounts

        return await list_ad_accounts(
            org_id, self.user, credentials_key, limit or DEFAULT_LIMIT, after
        )

    @_wire_errors
    async def meta_campaigns(
        self,
        org_id: str,
        account: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        from .meta import DEFAULT_LIMIT, list_campaigns

        return await list_campaigns(
            org_id, self.user, account, credentials_key, limit or DEFAULT_LIMIT, after
        )

    @_wire_errors
    async def meta_adsets(
        self,
        org_id: str,
        campaign: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        from .meta import DEFAULT_LIMIT, list_adsets

        return await list_adsets(
            org_id, self.user, campaign, credentials_key, limit or DEFAULT_LIMIT, after
        )

    @_wire_errors
    async def meta_ads(
        self,
        org_id: str,
        campaign: Optional[str] = None,
        adset: Optional[str] = None,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        from .meta import DEFAULT_LIMIT, list_ads

        return await list_ads(
            org_id,
            self.user,
            campaign,
            adset,
            credentials_key,
            limit or DEFAULT_LIMIT,
            after,
        )

    # -- keys --------------------------------------------------------------

    @_wire_errors
    async def list_api_keys(self) -> Dict[str, Any]:
        from .api_keys import list_api_keys

        return (await list_api_keys(self.user)).data.model_dump()

    @_wire_errors
    async def revoke_api_key(self, key_id: str) -> None:
        from .api_keys import revoke_api_key

        await revoke_api_key(key_id, self.user)

    @_wire_errors
    async def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Mint a key, attenuated against THIS caller's key. See `__init__`.

        The handler is called with a reconstructed `HTTPAuthorizationCredentials`
        rather than with pre-computed scopes, so the attenuation it performs is
        the very same code path the HTTP route takes -- `scopes_for_token` on
        the caller's bearer token, then `scopes_allow(..., "auth:write")` and
        `can_grant_scopes`. There is no second implementation of the rule and
        so nothing for the two transports to drift on.
        """
        from .api_keys import CreateApiKeyRequest, create_api_key

        if self.token is None:
            # Fail closed. Without the caller's token there is no way to know
            # what the caller may grant, and "assume unrestricted" would make
            # this transport a scope-escalation route.
            raise HTTPException(
                status_code=403,
                detail=(
                    "Minting a key needs the calling key itself, to attenuate "
                    "against; this backend was built without one."
                ),
            )

        # The request model is constructed inside the try for the same reason
        # `create_account` below does it: FastAPI parses the body into
        # `CreateApiKeyRequest` on the HTTP path, and its `Field(ge=1, le=...)`
        # on `expires_in_days` is enforced by THAT parse. Constructing it bare
        # here would surface `expires_in_days=0` as a raw pydantic
        # `ValidationError` string instead of the 422 the route gives.
        try:
            request = CreateApiKeyRequest(
                name=name, scopes=scopes, expires_in_days=expires_in_days
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=_field_errors(e)) from e

        body = await create_api_key(
            request,
            self.user,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=self.token),
        )
        return body.data.model_dump()

    # -- connected accounts ------------------------------------------------
    #
    # Both readers wrap the handler's dict in the route's `response_model`
    # before returning it, which the HTTP path gets for free from FastAPI. It is
    # not decoration: without it the two transports return different things.
    # `_public_row` omits `id` for every type but `api_key`, so `AccountResource`
    # is what fills it in as `null`, and `created` is a `datetime` in process
    # where the wire has an ISO string. `mode="json"` is what makes the second
    # half true.
    #
    # `_public_row` remains the STRIPPING layer -- it decides what is safe to
    # publish. `AccountResource` is only shape, and adding a field to it would
    # not publish anything `_public_row` had not already put there.

    @_wire_errors
    async def list_accounts(
        self, auth_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        from .accounts import ListAccountsResponse, list_accounts_endpoint

        body = await list_accounts_endpoint(self.user, auth_type)
        return ListAccountsResponse(**body).model_dump(mode="json")["data"]

    @_wire_errors
    async def create_account(
        self, name: str, auth_type: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        from .accounts import (
            CreateAccountRequest,
            CreateAccountResponse,
            create_account_endpoint,
        )

        # The route annotates the strict model and FastAPI is what parses the
        # body into it on the HTTP path, so parsing it here is what reproduces
        # the 422 for a value the model rejects -- a blank name, a name with a
        # `/` in it, an over-long one. Same reason `post_conf` above runs the
        # section's `TypeAdapter` itself.
        #
        # It does NOT reproduce the 422 for an unknown TOP-LEVEL field, and
        # cannot: FastMCP builds the tool's argument schema from this method's
        # signature and drops anything not in it, so an extra key never reaches
        # here to be refused. `extra="forbid"` on the request model still earns
        # its place on the HTTP path, and the unknown-key case inside
        # `credentials` -- the one that matters, because that is where a
        # misspelled provider field would be silently dropped -- IS reproduced,
        # by the per-type model in the handler.
        try:
            parsed = CreateAccountRequest(
                name=name, auth_type=auth_type, credentials=dict(credentials)
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=_field_errors(e)) from e

        body = await create_account_endpoint(parsed, self.user)
        return CreateAccountResponse(**body).model_dump(mode="json")["data"]

    @_wire_errors
    async def delete_account(self, auth_type: str, name: str) -> None:
        from .accounts import delete_account_endpoint

        await delete_account_endpoint(auth_type, name, self.user)


def _field_errors(exc: Exception) -> Any:
    """A pydantic `ValidationError` in FastAPI's 422 `detail` shape.

    So that a client parsing `detail[i].loc` off the HTTP route can parse it off
    a tool error too. `body` first, matching FastAPI, which prefixes `loc` with
    where the value came from.

    THE SUBMITTED VALUE IS STRIPPED (`accounts.scrub_field_errors`). Every error
    this produced used to carry pydantic's `input`, and for a `missing` error
    that is the whole enclosing object -- so `create_account` with a field
    missing echoed the credential the caller had just sent, into a tool result
    and therefore into an agent's context. `loc`, `msg` and `type` are what a
    caller needs to fix the request; the value is what they already have.

    `str(exc)` is deliberately not the fallback for a `ValidationError` either:
    pydantic's `__str__` renders `input_value=...`, which is the same leak by
    another route.
    """
    from .accounts import scrub_field_errors

    errors = getattr(exc, "errors", None)
    if errors is None:
        return "the request body did not validate"
    return scrub_field_errors(errors(), ("body",))


# --------------------------------------------------------------------------
# Scope enforcement, per tool
# --------------------------------------------------------------------------


def authorizer(scopes: Optional[List[str]]):
    """The per-call scope check for one caller's key.

    `scopes is None` means an absent scopes claim, which throughout this scheme
    means unrestricted -- an Auth0 dashboard session, or a key minted without
    scopes. It still cannot call a tool that is not in the table.
    """

    def authorize(tool_name: str) -> None:
        if tool_name not in TOOL_SCOPES:
            # Fail closed. A tool registered without an entry is unreachable
            # here rather than reachable by everyone, which is the direction
            # this mistake should point. `test_mcp_tools` makes it a test
            # failure long before it is a production one.
            raise ScopeError(
                f"{tool_name} has no declared scope and is not callable over "
                "POST /mcp. This is a server-side defect, not a key problem."
            )

        required = TOOL_SCOPES[tool_name]
        if required is None:
            return
        if not scopes_allow(scopes, required):
            raise ScopeError(
                f"This API key is not scoped for {required}, which "
                f"{tool_name} needs. Its scopes are: "
                + (", ".join(scopes) if scopes else "(none)")
            )

    return authorize


# --------------------------------------------------------------------------
# The mount
# --------------------------------------------------------------------------

# Built once, at import. `FastMCP` construction registers the tools and touches
# nothing else -- no socket, no task, no clock -- so it is safe to share, and
# sharing it is what makes the tool list provably the same object the stdio
# transport serves.
_server = build_server(stateless_http=True)

# Where the running session manager lives while the app is up. On the app's
# `state`, not in a module global, because a `StreamableHTTPSessionManager` can
# be `run()` exactly ONCE -- the second call raises -- and a module-level one
# would make the second app built in a process (which is every test after the
# first) permanently broken.
STATE_ATTRIBUTE = "mcp_session_manager"


def tool_server() -> Any:
    """The FastMCP instance behind `/mcp`. For tests and introspection."""
    return _server


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    """The app lifespan. `POST /mcp` does not work without it.

    The session manager owns a task group, and in stateless mode every request
    spawns its server task into it, so it has to be running for as long as the
    app is. Passed to `FastAPI(lifespan=...)` in `server.py`; uvicorn runs it,
    and a `TestClient` runs it only when used as a context manager.
    """
    manager = StreamableHTTPSessionManager(
        app=_server._mcp_server,
        event_store=None,  # stateless: there is nothing to replay
        json_response=False,
        stateless=True,
    )
    async with manager.run():
        setattr(app.state, STATE_ATTRIBUTE, manager)
        try:
            yield
        finally:
            setattr(app.state, STATE_ATTRIBUTE, None)


class MCPEndpoint:
    """Authenticate, bind the tool environment, hand over to the transport.

    A raw ASGI endpoint rather than a FastAPI route: the streamable-HTTP
    transport wants the ASGI triple so it can stream, which means no `Depends`.
    It authenticates by calling `deps.get_current_user` -- the same dependency
    every other route uses -- rather than reproducing what a valid token is.
    """

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        # `Request` here reads headers only; the body is left for the transport.
        request = Request(scope, receive)

        # POST ONLY, AND THIS IS LOAD-BEARING.
        #
        # Streamable HTTP defines three verbs: POST for a request, GET to open a
        # server-to-client SSE stream, DELETE to end a session. In STATELESS mode
        # the last two are meaningless -- there is no session to end, and a GET
        # stream can never carry anything, because nothing on this server sends
        # a client an unsolicited message. The library does not refuse them:
        # `StreamableHTTPServerTransport._handle_get_request` has no session-id
        # guard to fail on when `mcp_session_id` is None, so it opens an
        # `EventSourceResponse` that never receives and never closes. Every such
        # GET then pins a connection, a transport and an anyio task inside the
        # lifespan task group for the life of the worker.
        #
        # That is reachable by ANY authenticated key: `/mcp` is a delegated path
        # (`api_keys.DELEGATED_PATHS`), so the middleware lets a key through
        # before any scope is checked, and `TOOL_SCOPES` is only consulted once a
        # tool is called -- which a GET never does. A key with an empty scopes
        # list, which is denied every tool there is, could exhaust the worker.
        #
        # Checked BEFORE authentication on purpose: `verify_tokens` fetches
        # Auth0's JWKS over the network for an RS256 token, so answering a
        # method this endpoint does not serve should not cost an outbound
        # request. `mount()` also declares `methods=["POST"]`, which makes
        # Starlette answer first; this stays because it is what makes the
        # endpoint safe on its own, however it is mounted.
        if request.method != "POST":
            await _json(
                send,
                405,
                f"{request.method} is not served here. POST /mcp is the whole "
                "transport: it is stateless, so there is no session to DELETE "
                "and a GET stream would have nothing to carry.",
                headers={"Allow": "POST"},
            )
            return

        manager = getattr(request.app.state, STATE_ATTRIBUTE, None)
        if manager is None:
            # Only reachable if the app was built without `lifespan`. A clear
            # 503 beats the `assert self._task_group is not None` inside the
            # session manager, which surfaces as an opaque 500 and points at the
            # request rather than at how the app was assembled.
            await _json(
                send,
                503,
                "The MCP transport is not running: this app was built without "
                "mcp_server.lifespan.",
            )
            return

        header = request.headers.get("authorization") or ""
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            # 403, not 401, because that is what every other route on this
            # service answers: `deps.security` is `HTTPBearer(auto_error=True)`,
            # and FastAPI's HTTPBearer raises 403 "Not authenticated" for a
            # missing header and 403 "Invalid authentication credentials" for a
            # scheme it does not recognise. Arguably both should be 401 with a
            # `WWW-Authenticate` challenge -- but a client that special-cases
            # this endpoint's status because it is the one that differs is worse
            # than a service that is wrong consistently. A token that is present
            # and bad still gets `get_current_user`'s 401 below.
            await _json(
                send,
                403,
                "Not authenticated"
                if not header
                else "Invalid authentication credentials",
            )
            return

        try:
            user = await get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )
        except HTTPException as e:
            await _json(send, e.status_code, e.detail)
            return

        # The token goes to the backend as well as to the authorizer: the mint
        # route attenuates against the calling key's own scopes, and `User`
        # does not carry them. See `InProcessBackend.__init__`.
        env = ToolEnv(
            InProcessBackend(user, token), authorizer(scopes_for_token(token))
        )
        # The session manager spawns the server task from inside this block, and
        # a task keeps its own copy of the context, so the environment survives
        # for as long as the response does.
        with use(env):
            await manager.handle_request(scope, receive, send)


async def _json(
    send: Any, status: int, detail: Any, headers: Optional[Dict[str, str]] = None
) -> None:
    extra = dict(headers or {})
    if status == 401:
        extra.setdefault("WWW-Authenticate", "Bearer")
    response = JSONResponse(
        status_code=status,
        content={"detail": detail},
        headers=extra or None,
    )
    await response(
        {"type": "http", "headers": []}, _no_receive, send  # type: ignore[arg-type]
    )


async def _no_receive() -> Dict[str, Any]:  # pragma: no cover -- never awaited
    return {"type": "http.disconnect"}


def mount(app: Any) -> None:
    """Add `POST /mcp` to the app. One line for `server.py` to call.

    A Starlette `Route` with an ASGI endpoint, not `app.mount`: a mount would
    also claim `/mcp/anything`, and the delegated-path classification in
    `api_keys` is an exact path.

    `methods=["POST"]` is belt and braces with the check inside `MCPEndpoint`,
    the same way `meta.py`'s `require_scope` dependency is belt and braces with
    the scope middleware. This is the half that answers first -- Starlette's own
    plain-text 405 -- and the endpoint's own check is the half that survives
    being mounted some other way. Starlette honours `methods` here because a
    class INSTANCE is not a function: it is treated as an ASGI app, and the
    method set is applied by the router rather than ignored.
    """
    app.router.routes.append(Route(MCP_PATH, endpoint=MCPEndpoint(), methods=["POST"]))
