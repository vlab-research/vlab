"""The local MCP transport: `vlab mcp`, driven with the `mcp` client library.

The runbook -- create -> push -> validate -> plan -- through the tools, against
the REAL FastAPI app wrapped in a `TestClient` and the real database. The only
mock is `run_study_opt`, which is the boundary `test_cli.py` already mocks for
`vlab plan` and which would otherwise talk to Meta.

WHY THIS IS THE SERVER OBJECT AND NOT A SUBPROCESS

`serve_stdio` is `build_server()` plus one `use()` plus `run(transport="stdio")`,
and the last of those is the `mcp` library's own loop over stdin and stdout. A
subprocess would exercise that loop and nothing else of ours -- and it could not
be pointed at a `TestClient`, which lives in this process, so it would need a
real server and a real database socket to test the same tools. This connects a
real MCP client to the server object `vlab mcp` builds, over in-memory streams,
which covers everything up to the pipe: registration, schemas, dispatch,
serialisation and the tools themselves.

What that leaves untested is the stdio pipe itself and the `vlab mcp` command's
own wiring; `test_the_command_builds_the_server_and_serves_it_on_stdio` covers
the wiring, and the pipe is the library's.
"""

import asyncio
import json
import os
import uuid
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from typing import Any, Dict
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ..db import execute

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"
os.environ["FACEBOOK_APP_ID"] = "test-app-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-app-secret"

from fastapi.testclient import TestClient  # noqa: E402

from ..server.server import app  # noqa: E402
from . import mcp_tools as mt  # noqa: E402
from .cli import cli  # noqa: E402
from .client import VlabClient  # noqa: E402
from .test_mcp_tools import study  # noqa: E402

USER = "test|sdk-mcp"


# NOT autouse: the two `vlab mcp` wiring tests at the bottom need no database,
# and making them need one would mean the command could not be tested at all
# without a CockroachDB container.
@pytest.fixture
def clean_db():
    _reset_db()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    yield


@pytest.fixture(autouse=True)
def any_token_is_our_user():
    """Scopes are the remote transport's problem; this one delegates them to the
    service, and `test_mcp_server` is where they are asserted."""
    with patch("adopt.server.auth.verify_token") as m:
        m.return_value = {"sub": USER}
        yield m


@pytest.fixture
def org(clean_db):
    org_id = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, "o"))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, USER),
    )
    return org_id


@pytest.fixture
def session(clean_db):
    """An MCP client connected to the server `vlab mcp` would run.

    Yields a callable `(name, arguments) -> (payload, is_error)` so the tests
    below read as the runbook rather than as protocol plumbing.
    """
    from mcp.shared.memory import create_connected_server_and_client_session as connect

    client = VlabClient(
        api_key="token",
        base_url="http://testserver",
        session=TestClient(app, raise_server_exceptions=False),
    )
    server = mt.build_server()

    def call(name: str, arguments: Dict[str, Any]):
        async def main():
            with mt.use(mt.ToolEnv(mt.ClientBackend(client))):
                async with connect(server._mcp_server) as mcp_client:
                    result = await mcp_client.call_tool(name, arguments)
                    text = result.content[0].text
                    return (text, True) if result.isError else (json.loads(text), False)

        return asyncio.run(main())

    return call


def test_the_runbook_end_to_end_over_stdio(session, org):
    """create -> push -> validate -> plan, through the tools.

    Everything between the MCP frame and the database is real, including the
    HTTP the local transport makes: `ClientBackend` calls `VlabClient`, which
    calls the app.
    """
    made, is_error = session("create_study", {"org": org, "name": "HPV Nigeria"})
    assert not is_error, made
    slug = made["slug"]

    pushed, is_error = session(
        "push_study", {"org": org, "slug": slug, "sections": study()}
    )
    assert not is_error, pushed
    assert pushed["refused"] is False
    # PUSH_ORDER, recruitment last: the window is the study's on/off switch.
    assert pushed["written"][-1] == "recruitment"

    pulled, is_error = session("pull_study", {"org": org, "slug": slug})
    assert not is_error, pulled
    assert set(pulled["sections"]) == set(study())

    report, is_error = session("validate_study", {"sections": pulled["sections"]})
    assert not is_error, report
    assert report["valid"] is True
    assert report["known_gaps"]

    with patch("adopt.server.server.run_study_opt") as run_opt:
        from ..malaria import Instruction

        run_opt.return_value = [Instruction("campaign", "create", {"name": "x"}, None)]
        plan, is_error = session("plan_study", {"org": org, "slug": slug})

    assert not is_error, plan
    assert plan["count"] == 1


def test_a_second_push_of_the_same_study_writes_nothing(session, org):
    """`study_confs` is append-only, so a push that re-POSTed unchanged sections
    would append nine rows that change nothing, every time an agent ran it."""
    made, _ = session("create_study", {"org": org, "name": "HPV"})
    slug = made["slug"]

    session("push_study", {"org": org, "slug": slug, "sections": study()})
    again, is_error = session(
        "push_study", {"org": org, "slug": slug, "sections": study()}
    )

    assert not is_error, again
    assert again["written"] == []
    assert len(again["unchanged"]) == 7


def test_diff_then_push_agree_about_what_changes(session, org):
    """The property that makes the pair usable: what `diff_study` says would be
    written is what `push_study` writes."""
    made, _ = session("create_study", {"org": org, "name": "HPV"})
    slug = made["slug"]
    session("push_study", {"org": org, "slug": slug, "sections": study()})

    changed = study()
    changed["recruitment"]["budget"] = 5000

    diff, is_error = session(
        "diff_study", {"org": org, "slug": slug, "sections": changed}
    )
    assert not is_error, diff
    assert diff["would_push"] == ["recruitment"]

    pushed, is_error = session(
        "push_study", {"org": org, "slug": slug, "sections": changed}
    )
    assert not is_error, pushed
    assert pushed["written"] == ["recruitment"]


def test_a_study_that_does_not_exist_is_an_error_not_an_empty_study(session, org):
    message, is_error = session("pull_study", {"org": org, "slug": "no-such-study"})

    assert is_error
    assert "404" in message


def test_the_command_builds_the_server_and_serves_it_on_stdio():
    """`vlab mcp` is three lines and the interesting one is the transport.

    Asserted by intercepting the run rather than by starting one: a real stdio
    server reads stdin until it is closed, which is not something a test should
    be arranging.
    """
    served: Dict[str, Any] = {}

    def fake_run(self, transport=None, **kwargs):
        served["transport"] = transport
        served["tools"] = asyncio.run(self.list_tools())
        # The environment has to be bound BEFORE the loop starts, or every tool
        # raises "no environment is bound" on the first call.
        served["env"] = mt._ENV.get()

    with patch("mcp.server.fastmcp.FastMCP.run", fake_run):
        result = CliRunner().invoke(
            cli, ["mcp"], obj={"client": object()}, catch_exceptions=False
        )

    assert result.exit_code == 0, result.output
    assert served["transport"] == "stdio"
    assert {t.name for t in served["tools"]} == {fn.__name__ for fn in mt.TOOLS}
    assert served["env"] is not None
    assert isinstance(served["env"].backend, mt.ClientBackend)


def test_the_command_refuses_without_an_api_key():
    """It is started by a client, not typed, so the failure has to say what to
    put in the client's config rather than "401" some minutes later."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["mcp"],
        obj={"api_url": "http://x", "api_key": None},
        # Explicitly unset, because `--api-key` reads VLAB_API_KEY and a
        # developer running this on their own machine almost certainly has one
        # exported -- at which point the command does not refuse, it starts a
        # real stdio server on the test's stdin and closes stdout on EOF.
        env={"VLAB_API_KEY": None, "VLAB_API_URL": None},
    )

    assert result.exit_code == 1
    assert "VLAB_API_KEY" in result.output
