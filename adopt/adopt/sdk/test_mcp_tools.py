"""Tests for the MCP tool module: what each tool calls, and what it promises.

No database and no HTTP. The backend is a recorder implementing the contract
`VlabClient` defines, which is exactly the boundary plan §16.5 asks these to
mock at: the point of a tool is that it shapes arguments and calls the same
function the CLI calls, so what is worth asserting is WHICH function, with
WHICH arguments, and that the result comes back unchanged.

The other half of this file is about the descriptions. They are the product
surface -- an agent's entire model of vlab is what it reads there -- so they are
tested like code: every tool has one, it is substantial, it names the scope the
tool needs, and the ones that write say so.
"""

import ast
import asyncio
import os
import pathlib
from typing import Any, Dict, List

import pytest

from ..authoring.validate import validate_study as pure_validate
from . import mcp_tools as mt

ORG = "9d3d0f6a-0f0f-4b2a-9b7e-000000000001"
SLUG = "hpv"


# ---------------------------------------------------------------------------
# A backend that records
# ---------------------------------------------------------------------------


class Recorder:
    """The backend contract, recording every call and returning canned values.

    `__getattr__` rather than a method per name, so this cannot silently
    disagree with the contract: a tool calling a method nobody planned for is
    recorded rather than an `AttributeError`, and the test asserting the call
    list is what fails.
    """

    def __init__(self, **returns: Any) -> None:
        self.calls: List[Any] = []
        self.returns = returns

    def __getattr__(self, name: str):
        async def call(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args, kwargs))
            value = self.returns.get(name, {})
            return value(*args) if callable(value) else value

        return call

    @property
    def names(self) -> List[str]:
        return [c[0] for c in self.calls]


def run(tool, backend=None, **kwargs):
    """Call one tool with an environment bound. Returns its result."""
    backend = Recorder() if backend is None else backend

    async def main():
        with mt.use(mt.ToolEnv(backend)):
            return await tool(**kwargs)

    return asyncio.run(main())


# A complete, valid study. Deliberately a copy of nothing: `test_cli.py`'s
# fixture is next to a module that opens a database connection at import.
def study() -> Dict[str, Any]:
    return {
        "general": {
            "name": "HPV",
            "credentials_key": "Facebook",
            "credentials_entity": "facebook",
            "ad_account": "123",
            "opt_window": 48,
        },
        "recruitment": {
            "type": "simple",
            "ad_campaign_name": "hpv",
            "objective": "OUTCOME_ENGAGEMENT",
            "optimization_goal": "LINK_CLICKS",
            "min_budget": 100,
            "budget": 10000,
            "max_sample": 1000,
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-03-01T00:00:00",
        },
        "destinations": [
            {
                "type": "messenger",
                "name": "main",
                "initial_shortcode": "abc123",
                "welcome_message": "hello",
                "button_text": "Start",
            }
        ],
        "creatives": [
            {"name": "creative-a", "destination": "main", "template": {"actor_id": "1"}}
        ],
        "audiences": [],
        "variables": [],
        "strata": [
            {
                "id": "everyone",
                "quota": 1.0,
                "creatives": ["creative-a"],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {"genders": [1]},
                # The real shape: an `and` whose first term is the `answered`
                # one. `strata.get_finish_question_ref` reads the ref off that
                # term, so a flattened fixture would make `compile_strata`
                # untestable against a real study.
                "question_targeting": {
                    "op": "and",
                    "vars": [
                        {
                            "op": "answered",
                            "vars": [{"type": "question", "value": "finished"}],
                        }
                    ],
                },
                "metadata": {},
            }
        ],
    }


# ---------------------------------------------------------------------------
# One test per tool: what it calls, and what it returns
# ---------------------------------------------------------------------------


def test_list_orgs_calls_the_client_and_names_the_list():
    orgs = [{"id": ORG, "name": "vlab"}]
    backend = Recorder(list_orgs=orgs)

    assert run(mt.list_orgs, backend) == {"orgs": orgs}
    assert backend.calls == [("list_orgs", (), {})]


def test_list_orgs_passes_an_empty_list_through():
    """Not an error: the key's user is in no org, and nothing else here will
    work for them until a human adds them to one."""
    assert run(mt.list_orgs, Recorder(list_orgs=[])) == {"orgs": []}


def test_list_studies_calls_the_client_and_counts():
    rows = [
        {
            "id": "1",
            "name": "HPV",
            "slug": "hpv",
            "created": "2026-01-01T00:00:00+00:00",
        }
    ]
    backend = Recorder(list_studies=rows)

    out = run(mt.list_studies, backend, org=ORG)

    assert backend.calls == [("list_studies", (ORG, None, None), {})]
    assert out == {"studies": rows, "count": 1}


def test_list_studies_forwards_paging():
    """Without these an org past the server's default cap is silently
    truncated and the tool has no way past it."""
    backend = Recorder(list_studies=[])

    run(mt.list_studies, backend, org=ORG, limit=10, offset=20)

    assert backend.calls == [("list_studies", (ORG, 10, 20), {})]


def test_create_study_calls_the_client_and_returns_it_unchanged():
    made = {"id": "1", "name": "HPV", "slug": "hpv", "createdAt": 0}
    backend = Recorder(create_study=made)

    assert run(mt.create_study, backend, org=ORG, name="HPV") == made
    assert backend.calls == [("create_study", (ORG, "HPV"), {})]


def test_pull_study_reads_the_confs_and_says_what_is_missing():
    backend = Recorder(get_confs={"general": {"name": "HPV"}, "weird": []})

    out = run(mt.pull_study, backend, org=ORG, slug=SLUG)

    assert backend.calls == [("get_confs", (ORG, SLUG), {})]
    assert out["sections"] == {"general": {"name": "HPV"}, "weird": []}
    # Both halves matter to an agent: which of the nine have never been written,
    # and which stored conf types are not among the nine at all.
    assert "recruitment" in out["never_written"]
    assert out["unrecognised"] == ["weird"]


def test_validate_study_is_the_library_function_and_touches_no_backend():
    backend = Recorder()

    out = run(mt.validate_study, backend, sections=study())

    assert backend.calls == []
    assert out["valid"] == pure_validate(study()).valid
    # Always echoed: what the verdict did NOT cover is exactly what a caller
    # reading `valid: true` is at risk of over-reading.
    assert out["known_gaps"]


def test_validate_study_reports_a_broken_reference_rather_than_raising():
    broken = study()
    broken["strata"][0]["creatives"] = ["does-not-exist"]

    out = run(mt.validate_study, sections=broken)

    assert out["valid"] is False
    assert any("does-not-exist" in (e["message"] or "") for e in out["errors"])


def test_diff_study_compares_against_what_is_stored():
    stored = study()
    stored["recruitment"] = {**stored["recruitment"], "budget": 999}
    backend = Recorder(get_confs=stored)

    out = run(mt.diff_study, backend, org=ORG, slug=SLUG, sections=study())

    assert backend.calls == [("get_confs", (ORG, SLUG), {})]
    by_section = {s["section"]: s for s in out["sections"]}
    assert by_section["recruitment"]["status"] == "changed"
    assert by_section["general"]["status"] == "unchanged"
    assert out["would_push"] == ["recruitment"]
    # To the leaf, not just "recruitment changed": the difference between a
    # budget moving and every stratum being renamed is enormous.
    assert by_section["recruitment"]["changes"][0]["path"] == "budget"


def test_diff_study_names_a_key_no_model_declares():
    local = study()
    local["destinations"][0]["welcom_message"] = "typo"
    backend = Recorder(get_confs=study())

    out = run(mt.diff_study, backend, org=ORG, slug=SLUG, sections=local)

    unknown = {s["section"]: s["unknown_keys"] for s in out["sections"]}
    assert any("welcom_message" in u for u in unknown["destinations"])


def test_push_study_writes_the_changed_sections_in_reference_order():
    stored = {"general": study()["general"]}  # everything else is new
    backend = Recorder(get_confs=stored)

    out = run(mt.push_study, backend, org=ORG, slug=SLUG, sections=study())

    assert backend.names[0] == "get_confs"
    written = [c[1][2] for c in backend.calls if c[0] == "post_conf"]
    # PUSH_ORDER, and `recruitment` LAST: its start/end window is the study's
    # on/off switch, so writing it last means the two-hourly ad cron cannot pick
    # up a half-configured study.
    expected = [
        "destinations",
        "creatives",
        "audiences",
        "variables",
        "strata",
        "recruitment",
    ]
    assert written == expected
    assert out["written"] == expected
    # Skipped, not re-POSTed: an identical write appends a row that changes
    # nothing to an append-only table.
    assert out["unchanged"] == ["general"]
    assert out["refused"] is False


def test_push_study_refuses_an_invalid_study_and_writes_nothing():
    broken = study()
    broken["creatives"][0]["destination"] = "nowhere"
    backend = Recorder(get_confs={})

    out = run(mt.push_study, backend, org=ORG, slug=SLUG, sections=broken)

    assert out["refused"] is True
    assert out["written"] == []
    assert "post_conf" not in backend.names
    assert out["validation"]["valid"] is False


def test_push_study_forces_past_validation_when_asked():
    broken = study()
    broken["creatives"][0]["destination"] = "nowhere"
    backend = Recorder(get_confs={})

    out = run(mt.push_study, backend, org=ORG, slug=SLUG, sections=broken, force=True)

    assert out["refused"] is False
    assert out["written"]


def test_push_study_reports_what_landed_when_a_write_fails():
    """The single most important thing a partial push can say.

    There is no transaction and `study_confs` has no delete, so the sections
    already written cannot be withdrawn. Losing that list in an exception
    message would leave the caller unable to tell what state the study is in.
    """

    class Failing(Recorder):
        def __getattr__(self, name):
            call = super().__getattr__(name)

            async def maybe(*args, **kwargs):
                if name == "post_conf" and args[2] == "creatives":
                    raise RuntimeError("422 from the server")
                return await call(*args, **kwargs)

            return maybe

    backend = Failing(get_confs={})
    out = run(mt.push_study, backend, org=ORG, slug=SLUG, sections=study())

    assert out["written"] == ["general", "destinations"]
    assert out["failed"] == "creatives"
    assert "422" in out["error"]


def test_compile_strata_is_the_dashboards_regeneration():
    variables = [
        {
            "name": "gender",
            "levels": [
                {"name": "m", "quota": 0.5, "facebook_targeting": {"genders": [1]}},
                {"name": "f", "quota": 0.5, "facebook_targeting": {"genders": [2]}},
            ],
        }
    ]

    out = run(
        mt.compile_strata,
        variables=variables,
        finish_question_ref="finished",
        creatives=[{"name": "creative-a"}],
    )

    assert len(out["strata"]) == 2
    # New strata get the study's creatives; omitting them is how an agent
    # produces a study that validates as broken.
    assert out["strata"][0]["creatives"] == ["creative-a"]
    assert out["finish_question_ref"] == "finished"


def test_compile_strata_reads_the_finish_question_off_existing_strata():
    existing = study()["strata"]
    variables = [
        {
            "name": "gender",
            "levels": [{"name": "m", "quota": 1.0, "facebook_targeting": {}}],
        }
    ]

    out = run(mt.compile_strata, variables=variables, existing_strata=existing)

    assert out["finish_question_ref"] == "finished"


def test_compile_strata_says_which_strata_are_no_longer_produced():
    """A stratum id IS a Meta ad set name, so this list is what a push would
    delete -- with the ad set's learning and history."""
    existing = study()["strata"]  # id "everyone"
    variables = [
        {
            "name": "gender",
            "levels": [{"name": "m", "quota": 1.0, "facebook_targeting": {}}],
        }
    ]

    out = run(
        mt.compile_strata,
        variables=variables,
        finish_question_ref="finished",
        existing_strata=existing,
    )

    assert out["no_longer_produced"] == ["everyone"]


def test_extract_targeting_forces_advantage_audience_off():
    adset = {
        "id": "1",
        "name": "template",
        "targeting": {
            "geo_locations": {"countries": ["NG"]},
            "targeting_automation": {"advantage_audience": 1},
        },
    }

    out = run(mt.extract_targeting, adset=adset, properties=["geo_locations"])

    assert out["targeting"]["geo_locations"] == {"countries": ["NG"]}
    # Never inherited from the source ad set: expansion leaks delivery outside
    # a geographic stratum and makes its estimate wrong.
    assert out["targeting"]["targeting_automation"] == {"advantage_audience": 0}


def test_extract_targeting_refuses_a_property_the_adset_does_not_have():
    adset = {"id": "1", "targeting": {"geo_locations": {"countries": ["NG"]}}}

    with pytest.raises(Exception):
        run(mt.extract_targeting, adset=adset, properties=["age_min"])


def test_plan_study_calls_plan_and_returns_the_instructions():
    instructions = [{"node": "campaign", "action": "create", "params": {}, "id": None}]
    backend = Recorder(plan=instructions)

    out = run(mt.plan_study, backend, org=ORG, slug=SLUG)

    assert backend.calls == [("plan", (ORG, SLUG), {})]
    assert out == {"instructions": instructions, "count": 1}


def test_apply_instruction_replans_first_and_posts_that_instruction():
    instructions = [
        {"node": "campaign", "action": "create", "params": {"name": "a"}, "id": None},
        {"node": "adset", "action": "create", "params": {"name": "b"}, "id": None},
    ]
    backend = Recorder(plan=instructions, apply={"ok": True})

    out = run(mt.apply_instruction, backend, org=ORG, slug=SLUG, index=1)

    assert backend.names == ["plan", "apply"]
    # The plan is recomputed rather than cached: an instruction list goes stale
    # the moment anything is applied.
    assert backend.calls[1][1] == (ORG, SLUG, instructions[1])
    assert out["applied"] == instructions[1]


def test_apply_instruction_refuses_an_index_outside_the_current_plan():
    backend = Recorder(plan=[])

    with pytest.raises(IndexError):
        run(mt.apply_instruction, backend, org=ORG, slug=SLUG, index=0)

    assert backend.names == ["plan"]


@pytest.mark.parametrize(
    "tool,kwargs,method,args",
    [
        (
            "meta_credentials",
            {"org": ORG},
            "meta_credentials",
            (ORG,),
        ),
        (
            "meta_adaccounts",
            {"org": ORG, "credentials_key": "fb", "limit": 5, "after": "c"},
            "meta_adaccounts",
            (ORG, "fb", 5, "c"),
        ),
        (
            "meta_campaigns",
            {"org": ORG, "account": "act_1"},
            "meta_campaigns",
            (ORG, "act_1", None, None, None),
        ),
        (
            "meta_adsets",
            {"org": ORG, "campaign": "1"},
            "meta_adsets",
            (ORG, "1", None, None, None),
        ),
        (
            "meta_ads",
            {"org": ORG, "adset": "2"},
            "meta_ads",
            (ORG, None, "2", None, None, None),
        ),
    ],
)
def test_the_meta_tools_are_the_client_methods(tool, kwargs, method, args):
    backend = Recorder(**{method: {"data": []}})

    run(getattr(mt, tool), backend, **kwargs)

    assert backend.calls == [(method, args, {})]


def test_meta_credentials_unwraps_the_envelope():
    backend = Recorder(meta_credentials=[{"key": "Facebook", "entity": "facebook"}])

    out = run(mt.meta_credentials, backend, org=ORG)

    assert out == {"credentials": [{"key": "Facebook", "entity": "facebook"}]}


def test_list_api_keys_returns_the_clients_payload_unchanged():
    payload = {"keys": [{"id": "1", "name": "agent"}], "legacy_revocations": []}
    backend = Recorder(list_api_keys=payload)

    assert run(mt.list_api_keys, backend) == payload


def test_revoke_api_key_says_how_long_other_replicas_honour_it():
    backend = Recorder()

    out = run(mt.revoke_api_key, backend, key_id="k1")

    assert backend.calls == [("revoke_api_key", ("k1",), {})]
    # 30 seconds is the negative-cache TTL. Saying it is the difference between
    # "dead now" and "dead within a minute", and a caller that believes the
    # first will be surprised.
    assert out["other_replicas_honour_until_seconds"] == 30


# ---------------------------------------------------------------------------
# Registration, scopes and the environment
# ---------------------------------------------------------------------------


def test_a_tool_without_an_environment_fails_loudly():
    """A defect in a transport, not a user error: better a RuntimeError naming
    the cause than a tool quietly reaching for a backend that is not there."""
    with pytest.raises(RuntimeError, match="environment"):
        asyncio.run(mt.pull_study(org=ORG, slug=SLUG))


def test_every_registered_tool_has_a_scope_entry():
    """§16.3: a tool with no entry is DENIED, never allowed by default -- so a
    tool added without deciding its scope has to fail here rather than become
    a hole in production."""
    registered = {fn.__name__ for fn in mt.TOOLS}

    assert registered == set(mt.TOOL_SCOPES), (
        "mcp_tools.TOOL_SCOPES has drifted from the registered tools. Every "
        "tool needs a scope, or an explicit None for a pure one."
    )


def test_the_authorizer_runs_before_the_tool_does():
    """The check is a wrapper at registration, not a line inside each tool, so
    a tool added later cannot forget it."""
    calls: List[str] = []

    def deny(name: str) -> None:
        calls.append(name)
        raise mt.ScopeError("nope")

    backend = Recorder()

    async def main():
        with mt.use(mt.ToolEnv(backend, deny)):
            guarded = mt._guarded(mt.pull_study)
            await guarded(org=ORG, slug=SLUG)

    with pytest.raises(mt.ScopeError):
        asyncio.run(main())

    assert calls == ["pull_study"]
    assert backend.calls == []


def test_guarding_keeps_the_tools_signature():
    """FastMCP builds the input schema from the signature, so a wrapper that
    hid it behind `**kwargs` would publish a tool that takes nothing."""
    import inspect

    guarded = mt._guarded(mt.pull_study)

    assert list(inspect.signature(guarded).parameters) == ["org", "slug"]


# The scope table is checked against `api_keys.required_scope` -- the real
# function the routes are classified by -- in `server/test_mcp_server.py`.
# It cannot live here: this module is deliberately free of the server and of
# the environment variables importing it needs.


# ---------------------------------------------------------------------------
# The descriptions, which are the product
# ---------------------------------------------------------------------------

# Long enough to carry a mental model rather than a label. The shortest real
# description here is `meta_credentials` at ~900 characters; the floor is set
# well below that so it catches a tool shipped with a one-liner, not a tool
# whose description is merely concise.
MIN_DESCRIPTION = 400


def tool_descriptions() -> Dict[str, str]:
    import inspect

    return {fn.__name__: inspect.cleandoc(fn.__doc__ or "") for fn in mt.TOOLS}


@pytest.mark.parametrize("name", [fn.__name__ for fn in mt.TOOLS])
def test_every_tool_description_carries_its_scope_and_its_effects(name):
    description = tool_descriptions()[name]

    assert len(description) >= MIN_DESCRIPTION, (
        f"{name}'s description is {len(description)} characters. These are the "
        "product surface: an agent's whole model of vlab is what it reads here."
    )

    scope = mt.TOOL_SCOPES[name]
    if scope is None:
        assert "Pure" in description, (
            f"{name} needs no scope; its description has to say so, or a caller "
            "cannot tell it apart from one that reads their data."
        )
    else:
        assert scope in description, (
            f"{name} needs {scope} and its description does not say so. A "
            "caller who gets a scope error has to be able to say what to ask a "
            "human for."
        )

    # Every tool says what it does to the world, in words a reader cannot skim
    # past. The writes are the ones that matter -- study_confs has no delete.
    assert any(
        phrase in description
        for phrase in ("WRITES", "writes nothing", "NOT SIDE-EFFECT FREE", "SPENDS")
    ), f"{name} does not say whether it writes."


def test_the_writing_tools_say_that_confs_are_append_only():
    """The one thing an agent has to know before its first write: a POST IS the
    update, and there is no way back."""
    descriptions = tool_descriptions()

    assert "append-only" in descriptions["push_study"].lower()
    assert "POSTING IS THE UPDATE" in descriptions["push_study"]


def test_plan_study_says_it_reads_meta_and_heals_attributions():
    """It is a GET, it is called a preview, and it writes. Everything about its
    name suggests otherwise, so the description has to be explicit."""
    description = tool_descriptions()["plan_study"]

    assert "NOT SIDE-EFFECT FREE" in description
    assert "META" in description
    assert "HEALS AD ATTRIBUTIONS" in description


def test_the_server_instructions_carry_the_reference_graph():
    """What a client shows before any tool is called."""
    assert "APPEND-ONLY" in mt.INSTRUCTIONS
    assert "creatives name destinations" in mt.INSTRUCTIONS
    assert "ad set" in mt.INSTRUCTIONS


# ---------------------------------------------------------------------------
# The module boundary, and the CLI's import cost
# ---------------------------------------------------------------------------

SDK_DIR = pathlib.Path(__file__).parent


def _imported_modules(path: pathlib.Path) -> List[str]:
    tree = ast.parse(path.read_text("utf8"))
    out: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append(node.module)
        elif isinstance(node, ast.ImportFrom) and node.level:
            # `from ..server import x` -- the relative form, which is the one
            # this package would actually use.
            out.append("." * node.level + (node.module or ""))
    return out


# The static "adopt/sdk must never import adopt.server" check lives in
# `adopt/test_confs.py`, next to the other cross-module boundary tests, and it
# covers this module for free. Repeating it here would be a second copy of a
# rule that has one.


def test_the_cli_does_not_import_mcp_at_module_scope():
    """`vlab --help` has to stay fast.

    `mcp` pulls in starlette, uvicorn and pydantic-settings; `adopt.marketing`
    pulls in cvxpy, which is over a second on its own. Every `vlab` command
    would pay for either one, for the benefit of the one command that uses it.
    Both are therefore imported inside the function that needs them, and this is
    the test that keeps it that way.
    """
    imported = _imported_modules(SDK_DIR / "cli.py")

    assert "mcp" not in imported
    assert not [m for m in imported if m.startswith("mcp.")]
    assert not [m for m in imported if m.endswith("marketing")]


def test_vlab_help_does_not_load_mcp_or_cvxpy():
    """The property the test above is a proxy for, measured for real.

    A subprocess, because the modules are already imported in THIS one -- by
    the tests above, among other things -- so asking `sys.modules` in process
    would pass no matter what the CLI did.
    """
    import subprocess
    import sys
    import textwrap

    program = textwrap.dedent(
        """
        import sys
        from click.testing import CliRunner
        from adopt.sdk.cli import cli
        CliRunner().invoke(cli, ["--help"])
        loaded = [m for m in sys.modules if m == "mcp" or m.startswith("mcp.")]
        loaded += [m for m in sys.modules if m in ("cvxpy", "adopt.marketing")]
        print(",".join(sorted(loaded)))
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(SDK_DIR)),
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "", f"`vlab --help` imported: {out.stdout.strip()}"


# ---------------------------------------------------------------------------
# The HTTP backend, over a real ASGI app
# ---------------------------------------------------------------------------


def test_the_http_backend_drives_a_real_app_from_the_event_loop():
    """`ClientBackend` puts the synchronous `VlabClient` on a worker thread, and
    `push_sections` -- which is synchronous, because the CLI calls it straight --
    is itself run on one and hands its calls back to the loop.

    That is two thread hops in each direction, and the reason for a test with no
    mock in it: a deadlock or a lost context there would show up only under the
    real transports, where it would look like a hang rather than a failure. A
    toy ASGI app is enough to prove the plumbing; `test_mcp_stdio` runs the same
    path against the real service.
    """
    from typing import Union

    from fastapi import Body, FastAPI
    from fastapi.testclient import TestClient

    from .client import VlabClient

    app = FastAPI()
    written: List[str] = []

    @app.get("/{org}/studies/{slug}/confs")
    async def _confs(org: str, slug: str):
        return {"data": {}}

    @app.post("/{org}/studies/{slug}/confs/{segment}", status_code=201)
    async def _post(
        org: str, slug: str, segment: str, config: Union[dict, list] = Body(...)
    ):
        written.append(segment)
        return {"data": {"ok": True}}

    backend = mt.ClientBackend(
        VlabClient(api_key="t", base_url="http://testserver", session=TestClient(app))
    )

    out = run(mt.push_study, backend, org=ORG, slug=SLUG, sections=study())

    assert out["failed"] is None, out["error"]
    assert written == [
        "general",
        "destinations",
        "creatives",
        "audiences",
        "variables",
        "strata",
        "recruitment",
    ]
