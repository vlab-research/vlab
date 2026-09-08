"""Tests for `POST /mcp` -- the remote MCP transport (`server/mcp_server.py`).

Three things are being asserted, and they are of different kinds.

1. **Scopes.** This transport is the only place in the service where a request's
   authorization is decided by something other than its path, so the per-tool
   check is the whole security story: a key lacking a scope must get a TOOL
   error naming it (not a transport error, which tells an agent nothing it can
   act on), a key with no scopes claim must pass, the pure tools must pass for
   anyone, and a tool with no entry in `TOOL_SCOPES` must be denied. These need
   no database and run everywhere.

2. **Drift.** The tool list and the descriptions have to be identical over stdio
   and over HTTP. They are the same module, so this can only fail if somebody
   registers something transport-specifically -- which is exactly the mistake
   worth a test, because it would be invisible until an agent used the other
   front door.

3. **The runbook.** create -> push -> validate -> plan through `POST /mcp` with
   a scoped API key, against the real app and the real database. Mocked at the
   one boundary the app's own tests mock: `run_study_opt`, which would otherwise
   talk to Meta.
"""

import asyncio
import json
import os
import uuid
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

from ..db import execute

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"
os.environ["FACEBOOK_APP_ID"] = "test-app-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-app-secret"

from ..sdk import mcp_tools as mt  # noqa: E402
from ..sdk.test_mcp_tools import study  # noqa: E402
from . import api_keys as ak  # noqa: E402
from . import mcp_server as ms  # noqa: E402
from .auth import DifferentAuthError, generate_api_token  # noqa: E402
from .deps import User  # noqa: E402

USER = "test|mcp"


# --------------------------------------------------------------------------
# Driving the transport
# --------------------------------------------------------------------------


def rpc(client: TestClient, method: str, params: Any = None, token: str = "tok"):
    """One JSON-RPC call over streamable HTTP. Returns the decoded `result`.

    Stateless, so there is no `initialize` handshake and no session id: each
    POST is a whole conversation. That is the property that lets a client with
    no MCP library at all use this endpoint, and it is worth exercising rather
    than hiding behind the client library.
    """
    body: Dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params

    response = client.post(
        "/mcp",
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            # Both, per the streamable-HTTP spec: the server picks, and this one
            # answers with SSE.
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
    )
    return response


def result_of(response) -> Dict[str, Any]:
    assert response.status_code == 200, response.text
    for line in response.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: ") :])
            assert "error" not in payload, payload["error"]
            return payload["result"]
    raise AssertionError(f"no SSE data frame in: {response.text!r}")


def call_tool(client: TestClient, name: str, arguments: Dict[str, Any], token="tok"):
    """Returns `(payload, is_error)`. A tool error is a RESULT, not a fault."""
    result = result_of(
        rpc(client, "tools/call", {"name": name, "arguments": arguments}, token)
    )
    text = result["content"][0]["text"]
    if result.get("isError"):
        return text, True
    return json.loads(text), False


# --------------------------------------------------------------------------
# A bare app, for everything that does not need the database
# --------------------------------------------------------------------------


@pytest.fixture
def stub_client():
    """`/mcp` on an otherwise empty app, with authentication stubbed.

    Deliberately not `server.app`: these tests are about the transport and the
    scope check, and importing the whole service would make a failure here
    ambiguous between the two. The scope enforcement middleware IS added,
    because whether the delegated classification lets a scoped key through is
    one of the things being asserted.
    """

    def make(scopes: Optional[List[str]]):
        app = FastAPI(lifespan=ms.lifespan)
        ak.add_scope_enforcement(app)
        ms.mount(app)

        async def as_our_user(credentials):
            return User(user_id=USER)

        return app, as_our_user, scopes

    return make


class _NoBackend:
    """Any call reaching a backend from a scope test is a test that is not
    asserting what it says it is."""

    def __getattr__(self, name):
        raise AssertionError(f"a denied tool reached the backend: {name}")


def with_scopes(stub_client, scopes: Optional[List[str]]):
    app, as_our_user, _ = stub_client(scopes)
    patches = (
        patch("adopt.server.mcp_server.get_current_user", side_effect=as_our_user),
        patch("adopt.server.mcp_server.scopes_for_token", return_value=scopes),
        patch("adopt.server.mcp_server.InProcessBackend", lambda user: _NoBackend()),
    )
    return app, patches


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------


def test_no_token_at_all_is_a_403_like_every_other_route(stub_client):
    """403, not 401, because `deps.security` is `HTTPBearer(auto_error=True)`
    and that is what FastAPI's HTTPBearer answers for a missing header. Being
    wrong consistently beats being the one endpoint a client has to special-case.
    """
    app, patches = with_scopes(stub_client, None)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        response = client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_a_non_bearer_scheme_is_a_403(stub_client):
    app, patches = with_scopes(stub_client, None)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Authorization": "Basic abc"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid authentication credentials"


# --------------------------------------------------------------------------
# POST only
# --------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "delete", "put", "patch"])
def test_only_post_is_served(stub_client, method):
    """The fix for a real denial of service, not a tidiness rule.

    Streamable HTTP defines GET (open a server-to-client SSE stream) and DELETE
    (end a session) alongside POST. In STATELESS mode both are meaningless --
    and the library does not say so: `_handle_get_request` has no session-id
    guard to fail on when `mcp_session_id` is None, so it opens an
    `EventSourceResponse` that can never receive anything and never closes. Each
    one pins a connection, a transport and an anyio task in the lifespan task
    group for the life of the worker.

    `/mcp` is a delegated path, so ANY authenticated key reaches the endpoint
    before a scope is looked at, and a GET never calls a tool so `TOOL_SCOPES`
    never runs. A key scoped to nothing at all -- denied every tool there is --
    could have exhausted the worker.

    A `timeout` on the request, because the failure mode being guarded against
    is a hang: without the fix this test does not fail, it stops.
    """
    app, patches = with_scopes(stub_client, [])
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        response = getattr(client, method)(
            "/mcp",
            headers={
                "Authorization": "Bearer tok",
                "Accept": "text/event-stream",
            },
            timeout=10,
        )

    assert response.status_code == 405
    assert "POST" in response.headers.get("allow", "")


@pytest.mark.parametrize("method", ["get", "delete"])
def test_an_unauthenticated_other_verb_is_405_before_any_token_work(
    stub_client, method
):
    """Method first, authentication second, deliberately: `verify_tokens`
    fetches Auth0's JWKS over the NETWORK for an RS256 token, and answering a
    verb this endpoint does not serve must not cost an outbound request."""
    app, patches = with_scopes(stub_client, None)
    with patches[0] as get_user, patches[1], patches[2], TestClient(app) as client:
        response = getattr(client, method)(
            "/mcp", headers={"Accept": "text/event-stream"}, timeout=10
        )

    assert response.status_code == 405
    assert get_user.call_count == 0


def test_the_endpoint_refuses_a_get_even_when_mounted_without_methods():
    """`mount()` declares `methods=["POST"]` so Starlette answers first, but the
    endpoint has to be safe on its own -- that is the half that survives being
    mounted some other way."""
    app = FastAPI(lifespan=ms.lifespan)
    app.router.routes.append(Route("/mcp", endpoint=ms.MCPEndpoint()))

    with TestClient(app) as client:
        response = client.get(
            "/mcp",
            headers={"Authorization": "Bearer x", "Accept": "text/event-stream"},
            timeout=10,
        )

    assert response.status_code == 405
    assert response.headers.get("allow") == "POST"
    assert "stateless" in response.json()["detail"]


def test_the_transport_answers_503_when_the_lifespan_did_not_run():
    """A bare `TestClient(app)` does not run the lifespan, so the session
    manager's task group does not exist. Without this guard that surfaces as an
    `AssertionError` inside the library and a 500 -- which reads as a bug in the
    caller's request rather than in how the app was built."""
    app = FastAPI(lifespan=ms.lifespan)
    ms.mount(app)

    client = TestClient(app, raise_server_exceptions=False)  # no `with`
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Authorization": "Bearer x"},
    )

    assert response.status_code == 503


# --------------------------------------------------------------------------
# §16.3: scopes, per tool
# --------------------------------------------------------------------------


def test_a_key_lacking_the_scope_gets_a_tool_error_naming_it(stub_client):
    """Not a 403. An agent that gets a transport error learns only that
    something is wrong; one that is told "apply_instruction needs
    optimize:write" can say what to ask a human for."""
    app, patches = with_scopes(stub_client, ["studies:read"])
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        message, is_error = call_tool(
            client, "apply_instruction", {"org": "o", "slug": "s", "index": 0}
        )

    assert is_error
    assert "optimize:write" in message


def test_write_implies_read_here_as_it_does_on_the_routes(stub_client):
    app, patches = with_scopes(stub_client, ["studies:write"])
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        message, is_error = call_tool(client, "pull_study", {"org": "o", "slug": "s"})

    # It got past the scope check and into the (deliberately absent) backend.
    assert is_error
    assert "reached the backend: get_confs" in message


def test_a_key_with_no_scopes_claim_is_unrestricted(stub_client):
    """The rule that stops every key issued before scopes existed from
    breaking. It holds here too, or the remote transport would be stricter than
    the routes."""
    app, patches = with_scopes(stub_client, None)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        message, is_error = call_tool(
            client, "apply_instruction", {"org": "o", "slug": "s", "index": 0}
        )

    assert "not scoped" not in message


@pytest.mark.parametrize("scopes", [None, [], ["studies:read"], ["meta:read"]])
def test_the_pure_tools_pass_for_any_key(stub_client, scopes):
    """`compile_strata` and `extract_targeting` read nothing and write nothing,
    so gating them would be a permission with nothing behind it -- and an
    empty scopes list, which denies everything else, must still reach them."""
    app, patches = with_scopes(stub_client, scopes)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        payload, is_error = call_tool(
            client, "compile_strata", {"variables": [], "finish_question_ref": "q"}
        )

    assert not is_error
    assert payload["strata"] == []


def test_a_tool_with_no_scope_entry_is_denied_even_for_an_unrestricted_key():
    """Fail closed. A tool registered without a decision about its scope has to
    be unreachable, not reachable by everyone."""
    authorize = ms.authorizer(None)

    with pytest.raises(mt.ScopeError, match="no declared scope"):
        authorize("a_tool_nobody_classified")


def test_an_empty_scopes_list_denies_every_scoped_tool():
    authorize = ms.authorizer([])

    for name, scope in mt.TOOL_SCOPES.items():
        if scope is None:
            authorize(name)  # pure: allowed
            continue
        with pytest.raises(mt.ScopeError):
            authorize(name)


def test_mcp_is_a_delegated_path_in_the_middleware():
    """Without this, `required_scope` maps `/mcp` to no resource and the
    fail-closed middleware denies the whole endpoint to every scoped key --
    before any tool is reached and with a message about a path rather than a
    tool."""
    assert "/mcp" in ak.DELEGATED_PATHS
    assert ms.MCP_PATH in ak.DELEGATED_PATHS

    assert ak.is_authorized(["studies:read"], "POST", "/mcp")
    # And it is an EXACT path: the delegation does not extend to anything
    # mounted under it later.
    assert not ak.is_authorized(["studies:read"], "POST", "/mcp/anything")


def test_the_authorizer_uses_the_same_scope_algebra_as_the_routes():
    """`scopes_allow`, not a second implementation of `write` implies `read`."""
    assert ms.authorizer(["optimize:*"])("apply_instruction") is None
    assert ms.authorizer(["*"])("apply_instruction") is None
    with pytest.raises(mt.ScopeError):
        ms.authorizer(["optimize:read"])("apply_instruction")


def test_mounting_mcp_does_not_disturb_the_rest_of_the_app():
    """A raw ASGI `Route` appended to a FastAPI router is not an `APIRoute`, and
    FastAPI's schema generation walks the router. If it choked on one, the
    casualty would be `/openapi.json` and `/docs` -- for every other route, on a
    change that was supposed to add one inert endpoint."""
    from .server import app

    client = TestClient(app)

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/health").status_code == 200

    # And `/mcp` is absent from it, which is expected rather than a bug: the
    # OpenAPI document describes the REST surface, and MCP describes itself
    # through `tools/list`. §6b of documentation/agent-api.md says so.
    assert "/mcp" not in schema.json()["paths"]


# --------------------------------------------------------------------------
# The scope table against the routes it claims to reproduce
# --------------------------------------------------------------------------

ORG = "9d3d0f6a-0f0f-4b2a-9b7e-000000000001"

# Every tool that is backed by a route, and the request that route serves. The
# two pure tools are absent because there is no route to compare them to.
#
# `validate_study` runs in process and touches nothing, but it is scoped as the
# `POST .../validate` endpoint is: the endpoint exists, an agent may reasonably
# use either, and a tool that needed a NARROWER scope than the endpoint doing
# the same job would be a distinction with no meaning behind it.
ROUTE_BACKED_TOOLS = {
    # Discovery. `/orgs` is the one path here that is not org-scoped, which is
    # why `required_scope` needed a branch of its own for it; the assertion
    # below is what pins the tool to whatever that branch decided.
    "list_orgs": ("GET", "/orgs"),
    "list_studies": ("GET", f"/{ORG}/studies"),
    "create_study": ("POST", f"/{ORG}/studies"),
    "pull_study": ("GET", f"/{ORG}/studies/hpv/confs"),
    "diff_study": ("GET", f"/{ORG}/studies/hpv/confs"),
    "validate_study": ("POST", f"/{ORG}/studies/hpv/validate"),
    "push_study": ("POST", f"/{ORG}/studies/hpv/confs/general"),
    "copy_study_from": ("POST", f"/{ORG}/studies/hpv/copy-from"),
    "plan_study": ("GET", f"/{ORG}/optimize/hpv"),
    "apply_instruction": ("POST", f"/{ORG}/optimize/hpv/instruction"),
    # The study page, tool for tool. Three different resources, which is the
    # point of pinning them: `errors` and `current-data` live under
    # `/optimize/` and are therefore `optimize`, `ad-attributions` is
    # `responses`, and the three report reads are `stats`. Nothing about the
    # tool names says that, and a wrong guess here would hand a `stats:read`
    # key the optimizer's view.
    "study_errors": ("GET", f"/{ORG}/optimize/hpv/errors"),
    "current_data": ("GET", f"/{ORG}/optimize/hpv/current-data"),
    "ad_attributions": ("GET", f"/{ORG}/studies/hpv/ad-attributions"),
    "recruitment_stats": ("GET", f"/{ORG}/studies/hpv/recruitment-stats"),
    "respondents_over_time": ("GET", f"/{ORG}/studies/hpv/segments-progress"),
    "cost_over_time": ("GET", f"/{ORG}/studies/hpv/cost-over-time"),
    "meta_credentials": ("GET", f"/{ORG}/meta/credentials"),
    "meta_adaccounts": ("GET", f"/{ORG}/meta/adaccounts"),
    "meta_campaigns": ("GET", f"/{ORG}/meta/campaigns"),
    "meta_adsets": ("GET", f"/{ORG}/meta/adsets"),
    "meta_ads": ("GET", f"/{ORG}/meta/ads"),
    "list_api_keys": ("GET", "/users/api-keys"),
    "revoke_api_key": ("DELETE", "/users/api-keys/abc"),
}


@pytest.mark.parametrize("tool", sorted(ROUTE_BACKED_TOOLS))
def test_each_tools_scope_is_what_its_route_requires(tool):
    """The guard that makes `/mcp` no more powerful than the HTTP API.

    `TOOL_SCOPES` exists because a tool call never passes through
    `scope_enforcement_middleware` -- so if it and `required_scope` disagree,
    the same key gets different privileges depending on which front door it
    uses, and the difference is silent. Comparing the table against the
    function the routes are actually classified by is the only version of this
    test that can catch that; comparing it against a second hand-written table
    would only assert that someone typed the same thing twice.

    This is also what pins the DELIBERATE divergence from plan §16.2, which
    gives `plan_study` and `apply_instruction` `studies:write`. The routes say
    `optimize:read` and `optimize:write`, and following the plan would have let
    a study-authoring key spend money on Meta through a door it does not have
    over HTTP. See `planning/mcp.md` §3.
    """
    method, path = ROUTE_BACKED_TOOLS[tool]

    assert mt.TOOL_SCOPES[tool] == ak.required_scope(method, path)


def test_every_tool_is_either_route_backed_or_pure():
    """So a tool added later cannot quietly escape the check above."""
    pure = {name for name, scope in mt.TOOL_SCOPES.items() if scope is None}

    assert set(ROUTE_BACKED_TOOLS) | pure == set(mt.TOOL_SCOPES)
    assert pure == {"compile_strata", "extract_targeting"}


# --------------------------------------------------------------------------
# The drift guard
# --------------------------------------------------------------------------


def _stdio_tools() -> List[Dict[str, str]]:
    from mcp.shared.memory import create_connected_server_and_client_session as connect

    server = mt.build_server()

    async def main():
        with mt.use(mt.ToolEnv(_NoBackend())):
            async with connect(server._mcp_server) as client:
                listing = await client.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "schema": json.dumps(t.inputSchema, sort_keys=True),
                    }
                    for t in listing.tools
                ]

    return asyncio.run(main())


def test_the_two_transports_serve_exactly_the_same_tools(stub_client):
    """They are the same module, so this can only fail if a transport
    registered, renamed or re-described something of its own -- which would be
    invisible to whichever half of the users are on the other front door."""
    app, patches = with_scopes(stub_client, None)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        listing = result_of(rpc(client, "tools/list"))

    remote = [
        {
            "name": t["name"],
            "description": t.get("description") or "",
            "schema": json.dumps(t["inputSchema"], sort_keys=True),
        }
        for t in listing["tools"]
    ]

    assert remote == _stdio_tools()


def test_the_served_tools_are_the_declared_ones():
    """Catches a tool defined and never registered, which the drift guard above
    cannot: both transports would agree about its absence."""
    served = {t["name"] for t in _stdio_tools()}

    assert served == {fn.__name__ for fn in mt.TOOLS}
    assert served == set(mt.TOOL_SCOPES)


# --------------------------------------------------------------------------
# The runbook, against the real app and the real database
# --------------------------------------------------------------------------


@pytest.fixture
def db():
    _reset_db()
    ak.clear_api_key_cache()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    yield
    ak.clear_api_key_cache()


@pytest.fixture
def no_auth0():
    with patch("adopt.server.auth.verify_token") as m:
        m.side_effect = DifferentAuthError("not an auth0 token")
        yield m


@pytest.fixture
def org(db):
    org_id = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, "o"))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, USER),
    )
    return org_id


@pytest.fixture
def app_client(db, no_auth0):
    """The REAL service, with its lifespan running.

    `with TestClient(...)`, not a bare one: the streamable-HTTP session manager
    lives in the lifespan, and without it `/mcp` correctly refuses to serve.
    """
    from .server import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_the_runbook_end_to_end_through_post_mcp(app_client, org):
    """create -> push -> validate -> plan, as an agent would run it.

    One scoped key for the whole run, and the scopes are the ones the CLI's
    help tells a researcher to ask for. Everything between the JSON-RPC frame
    and the database is real.
    """
    token, _ = generate_api_token(
        user_id=USER,
        name="agent",
        scopes=["studies:write", "optimize:read"],
    )

    made, is_error = call_tool(
        app_client, "create_study", {"org": org, "name": "HPV Nigeria"}, token
    )
    assert not is_error, made
    slug = made["slug"]
    assert slug == "hpv-nigeria"

    sections = study()
    pushed, is_error = call_tool(
        app_client,
        "push_study",
        {"org": org, "slug": slug, "sections": sections},
        token,
    )
    assert not is_error, pushed
    assert pushed["refused"] is False
    assert pushed["written"][-1] == "recruitment"
    assert pushed["failed"] is None

    # What was written is what comes back, which is the round trip that matters:
    # a section the SDK can send and cannot read back is the bug that cost
    # `data-sources` (plan §11.4 item 5).
    pulled, is_error = call_tool(
        app_client, "pull_study", {"org": org, "slug": slug}, token
    )
    assert not is_error, pulled
    assert pulled["never_written"] == ["data_sources", "inference_data"]

    report, is_error = call_tool(
        app_client, "validate_study", {"sections": pulled["sections"]}, token
    )
    assert not is_error, report
    assert report["valid"] is True

    with patch("adopt.server.server.run_study_opt") as run_opt:
        from ..malaria import Instruction

        run_opt.return_value = [
            Instruction("campaign", "create", {"name": "hpv"}, None)
        ]
        plan, is_error = call_tool(
            app_client, "plan_study", {"org": org, "slug": slug}, token
        )

    assert not is_error, plan
    assert plan["count"] == 1
    assert plan["instructions"][0]["node"] == "campaign"


def test_a_read_only_key_cannot_push_through_mcp(app_client, org):
    """The property the whole scope table exists for, on the real service."""
    token, _ = generate_api_token(user_id=USER, name="ro", scopes=["studies:read"])

    message, is_error = call_tool(
        app_client,
        "push_study",
        {"org": org, "slug": "anything", "sections": {}},
        token,
    )

    assert is_error
    assert "studies:write" in message


def test_a_write_that_the_models_reject_is_a_422_not_a_stored_row(app_client, org):
    """The strict twins have to apply here too. A misspelled field reaching the
    database as a silently-dropped key is the failure `study_conf_strict.py`
    exists to prevent, and this transport parses the body itself."""
    token, _ = generate_api_token(user_id=USER, name="w", scopes=["studies:write"])

    made, _ = call_tool(app_client, "create_study", {"org": org, "name": "S"}, token)
    sections = study()
    sections["destinations"][0]["welcom_message"] = "typo"

    result, is_error = call_tool(
        app_client,
        "push_study",
        {"org": org, "slug": made["slug"], "sections": sections},
        token,
    )

    assert not is_error
    assert result["failed"] == "destinations"
    assert "welcom_message" in result["error"]
    # `general` is ordered before `destinations` and DID land. That is the
    # whole reason the failure reports what was written: there is no delete.
    assert result["written"] == ["general"]


def test_a_handlers_404_reaches_a_tool_as_a_tool_error(app_client, org):
    """`_wire_errors` in action: a handler raises `HTTPException(404)` and the
    tool sees `NotFoundError`, exactly as the wire would have produced. Without
    it, a tool would need one error path per transport.

    `diff_study`, not `pull_study`: `GET /confs` does not check that the study
    exists (see `test_mcp_stdio`), so it is the wrong tool to ask about a 404.
    This one 404s because `create_study` on an org the caller is not in does.
    """
    token, _ = generate_api_token(user_id=USER, name="x", scopes=["studies:write"])

    message, is_error = call_tool(
        app_client,
        "create_study",
        {"org": str(uuid.uuid4()), "name": "not my org"},
        token,
    )

    assert is_error
    assert "404" in message
    assert "Organization not found" in message


def test_discovery_through_mcp_with_a_read_only_key(app_client, org):
    """The gap this pair closes, exercised on the remote transport: a key that
    can only READ finds its org and then that org's slugs, without a human
    having handed over a UUID.

    `studies:read` and nothing else, deliberately. If either tool needed more,
    an agent would have to be given a key that can also write in order to find
    out what it could write to.
    """
    token, _ = generate_api_token(user_id=USER, name="ro", scopes=["studies:read"])

    # A study to find. Created with a second, wider key -- the read-only one
    # must not be able to do this, which the test below the runbook pins.
    writer, _ = generate_api_token(user_id=USER, name="w", scopes=["studies:write"])
    made, is_error = call_tool(
        app_client, "create_study", {"org": org, "name": "HPV Nigeria"}, writer
    )
    assert not is_error, made

    orgs, is_error = call_tool(app_client, "list_orgs", {}, token)
    assert not is_error, orgs
    assert [o["id"] for o in orgs["orgs"]] == [org]

    listing, is_error = call_tool(app_client, "list_studies", {"org": org}, token)
    assert not is_error, listing
    assert listing["page_size"] == 1
    assert listing["studies"][0]["slug"] == made["slug"]
    # The in-process path has to supply the Query defaults itself -- FastAPI is
    # not parsing a query string here, so an unsupplied `limit` would otherwise
    # arrive at psycopg as a `Query` object.
    assert listing["studies"][0]["created"].endswith("+00:00")


def test_list_studies_paging_survives_the_in_process_call(app_client, org):
    token, _ = generate_api_token(user_id=USER, name="rw", scopes=["studies:write"])

    for name in ("A", "B", "C"):
        made, is_error = call_tool(
            app_client, "create_study", {"org": org, "name": name}, token
        )
        assert not is_error, made

    listing, is_error = call_tool(
        app_client, "list_studies", {"org": org, "limit": 2}, token
    )
    assert not is_error, listing
    assert listing["page_size"] == 2

    listing, is_error = call_tool(
        app_client, "list_studies", {"org": org, "limit": 2, "offset": 2}, token
    )
    assert not is_error, listing
    assert listing["page_size"] == 1


def test_an_out_of_range_limit_is_rejected_in_process_too(app_client, org):
    """FastAPI's `Query(ge=1, le=500)` only runs when FastAPI parses a query
    string, and this transport calls the handler directly. Without the
    handler's own check a negative offset reaches psycopg as a 500."""
    token, _ = generate_api_token(user_id=USER, name="ro", scopes=["studies:read"])

    message, is_error = call_tool(
        app_client, "list_studies", {"org": org, "limit": 10_000}, token
    )

    assert is_error
    assert "422" in message


# --------------------------------------------------------------------------
# The study page, over the real transport
# --------------------------------------------------------------------------


def _study_id(org_id: str, slug: str) -> str:
    from ..db import query

    rows = query(
        db_conf,
        "select id from studies where org_id = %s and slug = %s",
        (org_id, slug),
        as_dict=True,
    )
    return str(list(rows)[0]["id"])


def test_cost_over_time_reads_the_report_a_plan_run_wrote(app_client, org):
    """The whole `stats:read` family in one exercise, against real rows.

    The report is seeded directly rather than by running a plan, because a plan
    run means Meta. What is being asserted is the path from a JSON-RPC frame to
    an `adopt_reports` row and back -- including that the in-process handler
    call returns the same shape the HTTP route serialises, which is the half
    that has no other test.
    """
    writer, _ = generate_api_token(user_id=USER, name="w", scopes=["studies:write"])
    made, is_error = call_tool(
        app_client, "create_study", {"org": org, "name": "HPV"}, writer
    )
    assert not is_error, made

    from ..campaign_queries import create_cost_over_time_report

    create_cost_over_time_report(
        _study_id(org, made["slug"]),
        [
            {
                "datetime": 1767225600000,
                "cumulativeSpend": 100.0,
                "cumulativeRespondents": 10,
                "marginalCost": 10.0,
                "newRespondents": 10,
                "dailySpend": 100.0,
            }
        ],
        db_conf,
    )

    token, _ = generate_api_token(user_id=USER, name="s", scopes=["stats:read"])
    out, is_error = call_tool(
        app_client, "cost_over_time", {"org": org, "slug": made["slug"]}, token
    )

    assert not is_error, out
    assert out["count"] == 1
    assert out["points"][0]["cumulativeSpend"] == 100.0
    # Milliseconds, not ISO. The report's own key names and units survive the
    # in-process call unchanged, which is what the dashboard's charts read.
    assert out["points"][0]["datetime"] == 1767225600000


def test_respondents_over_time_is_empty_before_any_plan_run(app_client, org):
    """Empty, not 404 -- and the description is what has to say that the
    difference between "no report yet" and "nobody answered" is invisible."""
    writer, _ = generate_api_token(user_id=USER, name="w", scopes=["studies:write"])
    made, _ = call_tool(app_client, "create_study", {"org": org, "name": "HPV"}, writer)

    token, _ = generate_api_token(user_id=USER, name="s", scopes=["stats:read"])
    out, is_error = call_tool(
        app_client, "respondents_over_time", {"org": org, "slug": made["slug"]}, token
    )

    assert not is_error, out
    assert out == {"points": [], "count": 0}


def test_study_errors_is_empty_for_a_study_with_no_events(app_client, org):
    """`[]` is the answer, not an error -- and it is not evidence of health:
    only swoosh writes these events, and they age out after 90 minutes."""
    writer, _ = generate_api_token(user_id=USER, name="w", scopes=["studies:write"])
    made, _ = call_tool(app_client, "create_study", {"org": org, "name": "HPV"}, writer)

    token, _ = generate_api_token(user_id=USER, name="o", scopes=["optimize:read"])
    out, is_error = call_tool(
        app_client, "study_errors", {"org": org, "slug": made["slug"]}, token
    )

    assert not is_error, out
    assert out == {"errors": [], "count": 0}


def test_a_studies_read_key_cannot_call_recruitment_stats(app_client, org):
    """`stats` is its own resource, and `studies:read` does not imply it. The
    error names the scope so an agent can say what to ask a human for."""
    token, _ = generate_api_token(user_id=USER, name="ro", scopes=["studies:read"])

    message, is_error = call_tool(
        app_client, "recruitment_stats", {"org": org, "slug": "anything"}, token
    )

    assert is_error
    assert "stats:read" in message


def test_a_read_only_key_can_discover_but_a_meta_key_cannot(app_client, org):
    """`meta:read` reads the researcher's Meta estate; it has no business
    enumerating vlab's own orgs. The error names the scope to ask for."""
    token, _ = generate_api_token(user_id=USER, name="m", scopes=["meta:read"])

    message, is_error = call_tool(app_client, "list_orgs", {}, token)

    assert is_error
    assert "studies:read" in message
