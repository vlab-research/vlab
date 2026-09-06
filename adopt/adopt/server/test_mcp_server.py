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


def test_no_token_at_all_is_a_401(stub_client):
    app, patches = with_scopes(stub_client, None)
    with patches[0], patches[1], patches[2], TestClient(app) as client:
        response = client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


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


def test_a_study_in_another_users_org_is_a_404_through_mcp(app_client):
    token, _ = generate_api_token(user_id=USER, name="x", scopes=["studies:read"])

    message, is_error = call_tool(
        app_client,
        "pull_study",
        {"org": str(uuid.uuid4()), "slug": "nope"},
        token,
    )

    assert is_error
    assert "404" in message
