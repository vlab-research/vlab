"""Keeps adopt/schemas/ honest.

Three separate things can rot, and each has a test:

  1. The committed files can fall behind the models (someone edits
     `study_conf.py` and forgets `make schemas`). CI catches that too, via
     `make check-schemas`, but a test catches it on the developer's machine,
     before the push.
  2. The export can stop being deterministic, at which point the committed
     artifact churns on every regeneration and the diff stops being readable
     -- which is the only reason to commit it at all.
  3. `CONF_ENDPOINTS` can fall behind the routes in server.py, silently
     shipping a schema for a body no endpoint takes, or omitting one it does.

(3) reads server.py with `ast` rather than importing it: importing the server
evaluates `PG_URL`, the Auth0 settings and the API-key secret at module scope
(`adopt/adopt/server/db.py:13`, `adopt/adopt/server/auth.py:13-18`), and those
module-level constants are captured on first import -- so importing it here,
with placeholder values, would poison the auth tests that import it later in
the same pytest process. Parsing the source has none of that hazard and needs
no database.
"""

import ast
import json
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest

from . import study_conf
from .schema_export import (
    CONF_ENDPOINTS,
    SCHEMA_DIR,
    build_schemas,
    render,
    stale_report,
    write_schemas,
)

SERVER_PATH = Path(__file__).resolve().parent / "server" / "server.py"

CONF_ROUTE_PREFIX = "/{org_id}/studies/{slug}/confs/"


def _annotation_source(annotation: Any) -> str:
    """Render an annotation the way server.py spells it.

    Names are found by identity in `study_conf` rather than via `__name__`,
    because two of the conf types (`DestinationConf`, `RecruitmentConf`) are
    annotated aliases and have no `__name__`.
    """
    if get_origin(annotation) is list:
        return f"list[{_annotation_source(get_args(annotation)[0])}]"

    for name, value in vars(study_conf).items():
        if value is annotation or value == annotation:
            return name

    raise AssertionError(f"{annotation!r} is not exported from study_conf")


def _routes_declared_in_server() -> dict[str, str]:
    """{wire conf type: source text of the `config` parameter's annotation}."""

    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    routes = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (isinstance(func, ast.Attribute) and func.attr == "post"):
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue

            path = decorator.args[0].value
            if not isinstance(path, str) or not path.startswith(CONF_ROUTE_PREFIX):
                continue

            conf_type = path[len(CONF_ROUTE_PREFIX) :]
            config_args = [
                a for a in node.args.args + node.args.kwonlyargs if a.arg == "config"
            ]
            assert config_args, f"POST {path} has no `config` parameter"
            routes[conf_type] = ast.unparse(config_args[0].annotation)

    return routes


def test_covers_every_conf_endpoint():
    """The export table and server.py's routes describe the same API."""

    declared = {
        ep.conf_type: _annotation_source(ep.annotation) for ep in CONF_ENDPOINTS
    }
    assert declared == _routes_declared_in_server(), (
        "adopt/adopt/schema_export.py:CONF_ENDPOINTS has drifted from the "
        "routes in adopt/adopt/server/server.py. Add, remove or retype the "
        "entry so the committed schemas describe what the server accepts."
    )


def test_render_is_deterministic():
    """Two builds of an unchanged tree produce byte-identical output."""

    first = {name: render(s) for name, s in build_schemas().items()}
    second = {name: render(s) for name, s in build_schemas().items()}
    assert first == second


def test_written_files_are_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_schemas(a)
    write_schemas(b)

    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir())
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_files_end_with_a_single_newline():
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n") and not text.endswith("\n\n"), path


def test_committed_schemas_are_current():
    """The developer-side half of `make check-schemas`."""

    problem = stale_report()
    if problem:
        pytest.fail(problem)


def _refs(node: Any):
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield node["$ref"]
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)


@pytest.mark.parametrize(
    "path", sorted(SCHEMA_DIR.glob("*.json")), ids=lambda p: p.name
)
def test_every_ref_resolves(path):
    """A committed schema with a dangling `$ref` is worse than no schema."""

    schema = json.loads(path.read_text(encoding="utf-8"))
    defs = schema.get("$defs", {})
    for ref in _refs(schema):
        assert ref.startswith("#/$defs/"), f"{path.name}: unexpected $ref {ref}"
        assert ref[len("#/$defs/") :] in defs, f"{path.name}: unresolved $ref {ref}"


def test_destination_union_exports_its_discriminator():
    """The `type` discriminator has to survive into the published schema.

    `DestinationConf` is `Annotated[Union[...], Field(discriminator="type")]`
    wrapped in a `BeforeValidator`, and it is not obvious that pydantic keeps
    the discriminator through that wrapping -- it does, and this pins it.

    It matters more than tidiness. This union was a plain, shape-matched Union
    until 2026-08-30, and every multi destination silently validated as a
    Messenger one (see the comment above `_TaggedDestination` in
    study_conf.py). A consumer generating requests from an untagged `anyOf`
    would reproduce exactly that class of bug on the client side.
    """

    schema = json.loads((SCHEMA_DIR / "destinations.json").read_text(encoding="utf-8"))
    discriminator = schema["items"]["discriminator"]

    assert discriminator["propertyName"] == "type"
    assert set(discriminator["mapping"]) == {
        "messenger",
        "app",
        "web",
        "website",
        "whatsapp",
        "multi",
    }


def test_study_conf_schema_carries_every_section():
    schema = json.loads((SCHEMA_DIR / "study-conf.json").read_text(encoding="utf-8"))
    assert set(study_conf.StudyConf.model_fields) <= set(schema["properties"])
