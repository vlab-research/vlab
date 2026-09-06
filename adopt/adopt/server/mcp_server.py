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

    def __init__(self, user: User) -> None:
        self.user = user

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


def _field_errors(exc: Exception) -> Any:
    """A pydantic `ValidationError` in FastAPI's 422 `detail` shape.

    So that a client parsing `detail[i].loc` off the HTTP route can parse it off
    a tool error too. Anything that is not a `ValidationError` falls back to its
    message rather than being reshaped into a lie.
    """
    errors = getattr(exc, "errors", None)
    if errors is None:
        return str(exc)
    try:
        # `body` first, matching FastAPI, which prefixes `loc` with where the
        # value came from.
        return [{**e, "loc": ["body", *e.get("loc", ())]} for e in errors()]
    except Exception:  # noqa: BLE001 -- never let error reporting raise
        return str(exc)


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
        method, _, token = header.partition(" ")
        if method.lower() != "bearer" or not token:
            await _json(send, 401, "Not authenticated")
            return

        try:
            user = await get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )
        except HTTPException as e:
            await _json(send, e.status_code, e.detail)
            return

        env = ToolEnv(InProcessBackend(user), authorizer(scopes_for_token(token)))
        # The session manager spawns the server task from inside this block, and
        # a task keeps its own copy of the context, so the environment survives
        # for as long as the response does.
        with use(env):
            await manager.handle_request(scope, receive, send)


async def _json(send: Any, status: int, detail: Any) -> None:
    response = JSONResponse(
        status_code=status,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
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
    """
    app.router.routes.append(Route(MCP_PATH, endpoint=MCPEndpoint()))
