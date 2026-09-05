"""Exports the study-configuration pydantic models as committed JSON Schema.

Why this exists
---------------
`adopt/adopt/study_conf.py` is the only real, enforced schema for a vlab study,
but it is Python. There is no OpenAPI artifact and no published contract, so an
agent, a notebook or any other non-dashboard consumer has nothing to program
against: it has to guess the shape of the JSON it POSTs and find out it guessed
wrong from a 422 (or, worse, from a cron hours later — see
planning/agent-study-authoring.md §2.5).

Pydantic emits JSON Schema for free. Committing the output turns that into a
contract with two properties the in-memory models do not have:

  1. A consumer can fetch it, validate against it, and generate from it without
     running Python.
  2. **A schema change shows up in code review.** That is the whole point of
     committing generated output rather than serving it from an endpoint. When
     someone adds a required field to `StratumConf`, the diff says so, next to
     the change, and the reviewer can ask whether every existing stored conf
     still validates.

`make check-schemas` (and `test_schema_export.py`) fail when the committed
files drift from the models, so property 2 cannot rot.

The conf-type keys
------------------
Files are keyed by the **wire** conf-type — the last path segment of
`POST /{org_id}/studies/{slug}/confs/<type>` — not by the Python class name,
because the wire name is what a consumer sees. Note the two places these
disagree with the storage key used inside the database (`data-sources` is
stored as `data_sources`, `inference-data` as `inference_data`); the URL spells
them with hyphens and so do these files.

`CONF_ENDPOINTS` below duplicates, deliberately, the route table in
`adopt/adopt/server/server.py`. It is not derived from the FastAPI app because
importing the server drags in the database, Facebook and auth config at import
time, which a pure code-generation step has no business needing.
`test_schema_export.py` parses server.py's routes with `ast` and fails if the
two ever disagree, so the duplication cannot drift silently.

Usage:
    python -m adopt.schema_export           # regenerate schemas/ in place
    python -m adopt.schema_export --check   # fail if schemas/ is stale
"""

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, get_args, get_origin

from pydantic import TypeAdapter

from .study_conf import (
    AudienceConf,
    CreativeConf,
    DataSourceConf,
    DestinationConf,
    GeneralConf,
    InferenceDataConf,
    RecruitmentConf,
    StratumConf,
    StudyConf,
    VariableConf,
)

# The 2020-12 dialect is what pydantic v2 emits. Stating it explicitly means a
# generic validator does not have to guess which draft these files are in.
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

CONF_URL_TEMPLATE = "/{org_id}/studies/{slug}/confs/%s"

INDEX_FILENAME = "index.json"
STUDY_CONF_FILENAME = "study-conf.json"


@dataclass(frozen=True)
class ConfEndpoint:
    """One `POST /confs/<conf_type>` route, and the exact body it accepts."""

    conf_type: str
    annotation: Any
    description: str

    @property
    def filename(self) -> str:
        return f"{self.conf_type}.json"

    @property
    def url(self) -> str:
        return CONF_URL_TEMPLATE % self.conf_type

    @property
    def is_list(self) -> bool:
        """True when the endpoint takes a JSON array of confs, not one conf.

        Faithfulness matters here: POSTing a bare object to `/confs/creatives`
        is a 422, and a consumer reading only the per-model schema would never
        learn that.
        """
        return get_origin(self.annotation) is list


# Mirrors adopt/adopt/server/server.py, in route-declaration order. Verified
# against that file by test_schema_export.py::test_covers_every_conf_endpoint.
CONF_ENDPOINTS: list[ConfEndpoint] = [
    ConfEndpoint(
        "general",
        GeneralConf,
        "Study-wide settings: name, ad account, credentials, opt window.",
    ),
    ConfEndpoint(
        "recruitment",
        RecruitmentConf,
        "How the study spends: one of three recruitment strategies. "
        "NOTE: this union carries no tag field, so it is an untagged `anyOf` "
        "- a consumer must tell the arms apart by shape "
        "(`ad_campaign_name` vs `ad_campaign_name_base`, then `arms` vs "
        "`destinations`). See 'JSON Schemas' in adopt/README.md.",
    ),
    ConfEndpoint(
        "destinations",
        list[DestinationConf],
        "Where respondents are sent. Discriminated on `type`.",
    ),
    ConfEndpoint(
        "creatives",
        list[CreativeConf],
        "Ad creatives, each naming the destination it recruits into.",
    ),
    ConfEndpoint(
        "audiences",
        list[AudienceConf],
        "Custom audiences derived from responses, and lookalikes of them.",
    ),
    ConfEndpoint(
        "variables",
        list[VariableConf],
        "Experimental variables and their levels, used to derive strata.",
    ),
    ConfEndpoint(
        "strata",
        list[StratumConf],
        "The recruitment cells: quota, creatives, audiences and targeting.",
    ),
    ConfEndpoint(
        "data-sources",
        list[DataSourceConf],
        "Response sources to pull from. Stored under the key `data_sources`.",
    ),
    ConfEndpoint(
        "inference-data",
        InferenceDataConf,
        "How to extract inference variables from responses. "
        "Stored under the key `inference_data`.",
    ),
]


def _json_schema(annotation: Any) -> dict[str, Any]:
    """Validation-mode JSON Schema for any annotation, model or alias.

    `TypeAdapter` rather than `model_json_schema()` because two of the conf
    types (`DestinationConf`, `RecruitmentConf`) are annotated aliases, not
    models, and three more arrive wrapped in `list[...]`. Validation mode is
    the right one: these files describe request bodies.
    """
    return TypeAdapter(annotation).json_schema(mode="validation")


def _decorate(
    schema: dict[str, Any], title: str, comment: str, description: str
) -> dict[str, Any]:
    """Add the dialect and provenance without clobbering pydantic's output.

    `title` and `description` are only filled in where pydantic left them
    empty — a model's own docstring is better documentation than anything this
    module can synthesise, so it wins. Provenance goes in `$comment`, which
    every validator ignores.
    """
    out = {"$schema": JSON_SCHEMA_DIALECT, "$comment": comment, **schema}
    out.setdefault("title", title)
    out.setdefault("description", description)
    return out


def _provenance(extra: str) -> str:
    return (
        "Generated from adopt/adopt/study_conf.py by adopt/adopt/schema_export.py. "
        "Do not edit by hand; run `make schemas`. " + extra
    )


def build_schemas() -> dict[str, dict[str, Any]]:
    """Every schema file this module owns, keyed by filename."""

    schemas: dict[str, dict[str, Any]] = {}

    for ep in CONF_ENDPOINTS:
        body = "a JSON array" if ep.is_list else "a JSON object"
        schemas[ep.filename] = _decorate(
            _json_schema(ep.annotation),
            title=f"{ep.conf_type} conf",
            comment=_provenance(f"Body of POST {ep.url} ({body})."),
            description=ep.description,
        )

    # The whole-study shape. No endpoint accepts it: adopt assembles it from
    # the individually-POSTed sections on the optimize path (`load_basics`),
    # which is where the cross-section validators finally run. A consumer that
    # wants to know whether its sections add up to a valid study — before a
    # cron tells it hours later — validates against this one.
    schemas[STUDY_CONF_FILENAME] = _decorate(
        _json_schema(StudyConf),
        title="StudyConf",
        comment=_provenance(
            "The assembled whole-study configuration. Not accepted by any "
            "endpoint; adopt builds it from the per-section confs. Structural "
            "only — StudyConf's cross-section model validators (e.g. "
            "check_whatsapp_refs_are_deliverable) cannot be expressed in JSON "
            "Schema and are NOT represented here."
        ),
        description=(
            "The full study configuration, as adopt assembles it from the "
            "per-section confs before running an optimization."
        ),
    )

    schemas[INDEX_FILENAME] = {
        "$comment": _provenance("Manifest of the schemas in this directory."),
        "confs": [
            {
                "conf_type": ep.conf_type,
                "url": ep.url,
                "method": "POST",
                "body": "array" if ep.is_list else "object",
                "schema": ep.filename,
                "description": ep.description,
            }
            for ep in CONF_ENDPOINTS
        ],
        "study": {"schema": STUDY_CONF_FILENAME},
    }

    return schemas


def render(schema: dict[str, Any]) -> str:
    """Bytes-on-disk form. Deterministic, and readable in a diff.

    `sort_keys` is what makes two runs byte-identical regardless of the order
    pydantic happened to walk the models in, and it keeps a diff to the keys
    that actually changed. Lists are left alone: `required` is emitted in field
    order, and that order is information about the model.
    """
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, schema in build_schemas().items():
        path = out_dir / filename
        path.write_text(render(schema), encoding="utf-8")
        written.append(path)
    return written


def stale_report(schema_dir: Path = SCHEMA_DIR) -> Optional[str]:
    """None if `schema_dir` matches the models, else a message saying how not.

    Regenerates into a temp dir and compares bytes, so this catches a hand-edit
    of a committed file just as surely as it catches a forgotten `make
    schemas`.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        write_schemas(tmp_dir)

        expected = {p.name: p.read_text(encoding="utf-8") for p in tmp_dir.iterdir()}
        actual = {
            p.name: p.read_text(encoding="utf-8")
            for p in schema_dir.iterdir()
            if p.suffix == ".json"
        }

    problems = []
    for name in sorted(set(expected) - set(actual)):
        problems.append(f"  missing:   {name}")
    for name in sorted(set(actual) - set(expected)):
        problems.append(f"  unexpected: {name} (no model produces this file)")
    for name in sorted(set(expected) & set(actual)):
        if expected[name] != actual[name]:
            problems.append(f"  stale:     {name}")

    if not problems:
        return None

    return (
        f"Committed JSON Schemas in {schema_dir} do not match the models in "
        "adopt/adopt/study_conf.py:\n"
        + "\n".join(problems)
        + "\n\nRun `make schemas` in adopt/ and commit the result.\n"
        "The regenerated schema is part of the change under review: if the "
        "diff surprises you, the model change probably does too."
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero if the committed schemas are stale",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=SCHEMA_DIR,
        help=f"directory to write into (default: {SCHEMA_DIR})",
    )
    args = parser.parse_args(argv)

    if args.check:
        problem = stale_report(args.out)
        if problem:
            print(problem, file=sys.stderr)
            return 1
        print(f"JSON Schemas in {args.out} are up to date.")
        return 0

    written = write_schemas(args.out)
    print(f"Wrote {len(written)} schema files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
