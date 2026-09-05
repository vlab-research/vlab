"""`vlab` -- author, validate, push, plan and apply a study from a file.

    pipx install --python python3.10 \\
      "adopt[sdk] @ git+https://github.com/vlab-research/vlab.git#subdirectory=adopt"
    export VLAB_API_KEY=eyJ...        # a human mints this; see `vlab keys --help`
    vlab create $ORG "HPV Nigeria" --init study.yaml
    $EDITOR study.yaml
    vlab validate && vlab diff && vlab push
    vlab plan  $ORG/hpv-nigeria
    vlab apply $ORG/hpv-nigeria 0

Needs Python `>=3.9,<3.11` -- `adopt`'s own constraint, which the SDK inherits.

Every command prints for a human by default and takes `--json` for a program.
Every command that talks to the server takes `--api-url` and `--api-key`,
before OR after the subcommand, defaulting to `VLAB_API_URL` and
`VLAB_API_KEY`. **No token is ever written to disk**: there is no `vlab login`
and no credentials file, because the one thing an agent's working directory
should not contain is a key that can spend money on Meta.

`--json` and a confirmation prompt are incompatible, so `apply` and
`keys revoke` require `--yes` alongside it rather than emitting a prompt into
what is supposed to be parseable output.

EXIT CODES

    0  it worked, or the study is valid
    1  it did not work, or the study is invalid (`validate`, `push`)
    2  the command line was wrong (click's own)

`validate` exiting 1 on an invalid study is what makes it usable in a
`&&` chain and in CI. Warnings never do that -- a study recruiting uniformly is
entitled to a thin ref, and a study not yet wired to a survey platform is
unfinished rather than broken (plan §14.2).

WHAT THIS DOES NOT DO

No retries and no automatic multi-step apply. `study_confs` is append-only, so
a write that appears to have failed may have landed and a retry writes a second
row; and the plan/apply loop is genuinely iterative -- an ad set's ads are not
planned until the ad set exists on Meta -- so a loop that applied everything
would be applying a stale list. Both are the caller's call to make.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import click

from ..authoring.extract import ExtractError, extract_from_adset
from ..authoring.geo import GeoError
from ..authoring.sheets import SheetError
from ..authoring.strata import create_strata_from_variables, get_finish_question_ref
from ..authoring.validate import KNOWN_GAPS, validate_study
from ..confs import json_safe
from .client import DEFAULT_API_URL, VlabClient, VlabError
from .study import (
    SECTION_URL_SEGMENTS,
    SECTIONS,
    SectionDiff,
    StudyFile,
    diff_sections,
    push_plan,
    skeleton,
    value_diff,
)

DEFAULT_STUDY_FILE = "study.yaml"

# How many leaf changes a `changed` section prints before it stops. A study
# with forty strata whose finish question moved has hundreds; the count is
# always shown, so the cap hides volume rather than the fact of it.
MAX_DIFF_LINES = 12


# ---------------------------------------------------------------------------
# Plumbing
# ---------------------------------------------------------------------------


# Every error type that means "your input is wrong" rather than "the SDK has a
# bug". Deliberately a list rather than a bare `except Exception`: a genuine
# defect in here should print a traceback, because a traceback is what gets it
# reported, whereas `ClickException` makes it look like the user's fault.
USER_ERRORS = (VlabError, ExtractError, SheetError, GeoError, ValueError, OSError)


class VlabGroup(click.Group):
    """Turns every user-facing error into a clean message and exit 1.

    One place rather than a decorator per command, so a command added later
    cannot forget it and print a traceback at a researcher. On the group AND on
    each sub-group, because click dispatches into a sub-group's own `invoke`.
    """

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except (click.ClickException, click.exceptions.Abort):
            raise
        except USER_ERRORS as e:
            raise click.ClickException(str(e))


def get_client(ctx: click.Context) -> VlabClient:
    """The client, built once per invocation -- or the injected one.

    `ctx.obj["client"]` is how the tests hand in a `VlabClient` wrapping a
    Starlette `TestClient`, so the CLI tests drive the real FastAPI app rather
    than a mock of it.
    """
    obj = ctx.ensure_object(dict)
    if obj.get("client") is not None:
        return obj["client"]

    if not obj.get("api_key"):
        raise click.ClickException(
            "No API key. Set VLAB_API_KEY, or pass --api-key.\n"
            "A human has to mint the first one: it needs an Auth0 login, from "
            "the dashboard's Accounts page. Ask for scopes "
            '["studies:write", "meta:read", "optimize:read"] unless you need '
            "to launch ads."
        )

    obj["client"] = VlabClient(api_key=obj["api_key"], base_url=obj["api_url"])
    return obj["client"]


def parse_target(target: str) -> Tuple[str, str]:
    """`<org>/<slug>` -> `(org, slug)`.

    An org id is a UUID and a slug never contains a slash, so one split is
    unambiguous. The error names both halves because "org" is not discoverable
    from any endpoint an API key can call (§7.1) and a user who does not have
    it needs to be told to ask for it, not told the syntax is wrong.
    """
    org, sep, slug = target.partition("/")
    # `"/" in slug` matters: without it `org/slug/extra` splits happily, the
    # extra segment is percent-encoded into the path by `client._seg`, and the
    # caller gets a 404 instead of being told the argument is malformed.
    if not sep or not org or not slug or "/" in slug:
        raise click.BadParameter(
            f"Expected <org>/<slug>, got {target!r}. The org is a UUID a human "
            "has to hand you -- no endpoint an API key can call lists them."
        )
    return org, slug


def load_study(path: Optional[str]) -> StudyFile:
    target = path or DEFAULT_STUDY_FILE
    if not os.path.exists(target):
        raise click.ClickException(
            f"No such file: {target}. `vlab pull <org>/<slug>` writes one, or "
            "`vlab create <org> <name> --init` starts a new one."
        )
    return StudyFile.load(target)


def emit_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def short(value: Any, width: int = 60) -> str:
    """A value on one line, truncated. For diff and plan output."""
    text = json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= width else text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# The group
# ---------------------------------------------------------------------------


# `auto_envvar_prefix` is not used: the two options are declared with explicit
# `envvar=`, and click's automatic prefixing would also invent VLAB_CREATE_ORG
# and friends for every argument of every subcommand.
GROUP_CONTEXT = {"help_option_names": ["-h", "--help"]}


def auth_options(command):
    """Let `--api-url` / `--api-key` be given after the subcommand as well.

    They are group-level options, so `vlab --api-key X push` has always worked
    and `vlab push --api-key X` was a usage error -- which is the wrong way
    round from how anyone types it, and the module docstring claimed both. The
    same env vars back both spellings, and a value given on the subcommand
    wins over one given on the group, because it is the more specific of the
    two.
    """
    command = click.option(
        "--api-url",
        envvar="VLAB_API_URL",
        default=None,
        expose_value=False,
        callback=_remember("api_url"),
        help="Base URL of the study-configuration service.",
    )(command)
    return click.option(
        "--api-key",
        envvar="VLAB_API_KEY",
        default=None,
        expose_value=False,
        callback=_remember("api_key"),
        help="Bearer token. Prefer the environment variable.",
    )(command)


def _remember(key: str):
    def callback(ctx: click.Context, param: Any, value: Any) -> Any:
        if value is not None:
            ctx.ensure_object(dict)[key] = value
        return value

    return callback


@click.group(cls=VlabGroup, context_settings=GROUP_CONTEXT)
@click.option(
    "--api-url",
    envvar="VLAB_API_URL",
    default=DEFAULT_API_URL,
    show_default=True,
    help="Base URL of the study-configuration service.",
)
@click.option(
    "--api-key",
    envvar="VLAB_API_KEY",
    default=None,
    help="Bearer token. Prefer the environment variable.",
)
@click.version_option(package_name="adopt", prog_name="vlab")
@click.pass_context
def cli(ctx: click.Context, api_url: str, api_key: Optional[str]) -> None:
    """Author a vlab study from a file.

    A study on disk is one `study.yaml`: a three-key header (org, slug, name)
    and the nine configuration sections in the wire shapes
    `documentation/agent-api.md` §3 documents. Writing a section REPLACES it
    whole; there is no partial update and no delete.
    """
    obj = ctx.ensure_object(dict)
    obj.setdefault("api_url", api_url)
    obj.setdefault("api_key", api_key)


# ---------------------------------------------------------------------------
# create / pull
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("org")
@click.argument("name")
@click.option(
    "--init",
    "init_path",
    is_flag=False,
    flag_value=DEFAULT_STUDY_FILE,
    default=None,
    help="Also write a starter study file at this path.",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def create(
    ctx: click.Context, org: str, name: str, init_path: Optional[str], as_json: bool
) -> None:
    """Create a study. Prints its slug.

    The slug is derived server-side and is not a slugification you can predict:
    apostrophes are deleted rather than replaced, so "Nandan's study" is
    "nandans-study". Read it from here rather than computing it.
    """
    client = get_client(ctx)
    study = client.create_study(org, name)

    if init_path:
        if os.path.exists(init_path):
            raise click.ClickException(
                f"{init_path} already exists. The study was created "
                f"(slug: {study['slug']}); pass a different --init path, or "
                "move the file out of the way."
            )
        with open(init_path, "w", encoding="utf8") as f:
            f.write(skeleton(org=org, slug=study["slug"], name=study["name"]))

    if as_json:
        emit_json({"study": study, "file": init_path})
        return

    click.echo(f"Created study {study['name']!r}")
    click.echo(f"  slug: {study['slug']}")
    click.echo(f"  id:   {study['id']}")
    if init_path:
        click.echo(f"  file: {init_path}")
        click.echo("")
        click.echo(f"Edit {init_path}, then: vlab validate && vlab push")


@cli.command()
@click.argument("target")
@click.option(
    "-o",
    "--output",
    default=DEFAULT_STUDY_FILE,
    show_default=True,
    help="Where to write. A .json extension writes JSON.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing file.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def pull(
    ctx: click.Context, target: str, output: str, force: bool, as_json: bool
) -> None:
    """Write <org>/<slug>'s stored configuration to a file."""
    org, slug = parse_target(target)
    client = get_client(ctx)

    if os.path.exists(output) and not force:
        raise click.ClickException(
            f"{output} exists. Pass --force to overwrite it, or -o to write "
            "elsewhere. (Pulling over local edits would lose them, and there "
            "is no undo.)"
        )

    confs = client.get_confs(org, slug)
    study = StudyFile.from_confs(org, slug, confs, path=output)
    study.save()

    written = [s for s in SECTIONS if s in study.sections]
    missing = [s for s in SECTIONS if s not in study.sections]

    if as_json:
        emit_json(
            {
                "file": output,
                "written": written,
                "never_written": missing,
                "unrecognised": sorted(study.extra),
            }
        )
        return

    click.echo(f"Wrote {output}: {len(written)} of 9 sections.")
    if missing:
        click.echo(f"  never written: {', '.join(missing)}")
    if study.extra:
        click.echo(f"  unrecognised conf types kept: {', '.join(sorted(study.extra))}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", required=False)
@click.option(
    "--remote",
    is_flag=True,
    help="Ask the server instead of validating in process.",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def validate(
    ctx: click.Context, path: Optional[str], remote: bool, as_json: bool
) -> None:
    """Check a study file. Exits 1 when it is invalid.

    Local by default: `adopt.authoring.validate.validate_study` is a pure
    function, so this is instant, runs offline, and works on sections that have
    never been written.

    `--remote` posts the file's sections to
    `POST /{org}/studies/{slug}/validate` instead. The endpoint is a wrapper
    over the same function, so the two agree by construction -- use it when
    this package is older than the deployment and you want the deployment's
    opinion, not this one's.

    Neither half looks at Meta. Whether the template campaign still exists,
    whether the creative template is still valid, whether Meta accepts your
    objective/optimization_goal pairing: none of that is checked here, and the
    plan endpoint is what exercises it. See `known_gaps` in the output.
    """
    study = load_study(path)

    if remote:
        org, slug = study.require_target()
        body = client_validate(ctx, org, slug, study.all_sections())
        report = body.get("data", {})
        gaps = body.get("known_gaps", [])
    else:
        report = validate_study(study.all_sections()).model_dump()
        gaps = list(KNOWN_GAPS)

    if as_json:
        emit_json({"data": report, "known_gaps": gaps})
    else:
        print_report(report, gaps, study)

    if not report.get("valid"):
        ctx.exit(1)


def client_validate(
    ctx: click.Context, org: str, slug: str, sections: Mapping[str, Any]
) -> Dict[str, Any]:
    return get_client(ctx).validate(org, slug, sections)


def print_report(
    report: Mapping[str, Any], gaps: Sequence[str], study: StudyFile
) -> None:
    errors = report.get("errors") or []
    warnings = report.get("warnings") or []

    for label, findings in (("ERROR", errors), ("WARNING", warnings)):
        for f in findings:
            where = f.get("path") or f.get("section") or "-"
            click.echo(f"{label:<8} {f.get('code'):<40} {where}")
            for line in _wrap(f.get("message") or ""):
                click.echo(f"         {line}")

    if errors or warnings:
        click.echo("")

    where = f" ({study.path})" if study.path else ""
    if report.get("valid"):
        click.echo(f"valid{where}: {len(warnings)} warning(s), no errors.")
    else:
        click.echo(
            f"INVALID{where}: {len(errors)} error(s), {len(warnings)} warning(s)."
        )

    # Always, not only on success: what the verdict did not cover is exactly
    # what a caller reading "valid" is at risk of over-reading.
    click.echo("")
    click.echo("Not checked (known gaps):")
    for gap in gaps:
        for i, line in enumerate(_wrap(gap, 74)):
            click.echo(("  - " if i == 0 else "    ") + line)


def _wrap(text: str, width: int = 70) -> List[str]:
    import textwrap

    return textwrap.wrap(text, width=width) or [""]


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", required=False)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def diff(ctx: click.Context, path: Optional[str], as_json: bool) -> None:
    """Compare a study file against what the server holds.

    Compares what would be STORED, not what would be sent: the server keeps
    `model_dump()` of your body, so unknown keys are gone and defaults are
    filled in. Without reproducing that, every section whose file omits an
    optional field would read as changed forever.

    A `type` tag on `recruitment` or a `messenger` `destinations[]` entry that
    merely restates the body's own shape is not a difference. It cannot be:
    a server on PR #262 or later stores one and an older one drops it, so a
    file that writes the tag -- which it should -- would otherwise diff against
    both of them permanently.
    """
    study = load_study(path)
    org, slug = study.require_target()
    stored = get_client(ctx).get_confs(org, slug)

    diffs = diff_sections(study.sections, stored)

    if as_json:
        emit_json(
            {
                "sections": [
                    {
                        "section": d.section,
                        "status": d.status,
                        "unknown_keys": list(d.unknown),
                        "changes": [
                            {"path": p, "stored": s, "local": l}
                            for p, s, l in value_diff(d.stored, d.local)
                        ]
                        if d.status == "changed"
                        else [],
                    }
                    for d in diffs
                ]
            }
        )
        return

    print_diff(diffs, study)


def print_diff(diffs: Sequence[SectionDiff], study: StudyFile) -> None:
    if not diffs:
        click.echo("No sections locally or on the server.")
        return

    marks = {"new": "+", "changed": "~", "unchanged": " ", "remote_only": "?"}

    for d in diffs:
        click.echo(f"{marks[d.status]} {d.section:<16} {d.status}")

        if d.status == "changed":
            changes = value_diff(d.stored, d.local)
            for p, stored_v, local_v in changes[:MAX_DIFF_LINES]:
                click.echo(f"      {p or '(whole section)'}")
                click.echo(f"        stored: {short(stored_v)}")
                click.echo(f"        local:  {short(local_v)}")
            if len(changes) > MAX_DIFF_LINES:
                click.echo(f"      … and {len(changes) - MAX_DIFF_LINES} more")

        for key in d.unknown:
            click.echo(f"      ! {key} is not a field of this conf")

    unknown_total = sum(len(d.unknown) for d in diffs)
    if unknown_total:
        click.echo("")
        click.echo(
            "! marks keys no model declares. An older server accepts the write "
            "and silently drops them; a server on PR #262 or later rejects the "
            "write with a 422 naming the key."
        )

    # `push_plan`, not a filter over `diffs`: the summary must list the
    # sections in the order `push` will actually write them, or the two
    # commands disagree about the same study on the same screen.
    to_push = [d.section for d in push_plan(diffs)]
    remote_only = [d.section for d in diffs if d.status == "remote_only"]

    click.echo("")
    if to_push:
        click.echo(f"{len(to_push)} section(s) would be written: {', '.join(to_push)}")
    else:
        click.echo("Nothing to push.")
    if remote_only:
        click.echo(
            f"On the server but not in {study.path or 'the file'}: "
            f"{', '.join(remote_only)}. `push` never touches these -- there is "
            "no way to remove a section through the API at all."
        )
    if study.extra:
        # A key outside the nine has no route, so it is not written, not
        # rejected and not missed -- the worst outcome available. Say so here
        # as well as in `validate`'s `section.unrecognized`, because `diff` is
        # the command a caller runs to find out what `push` will do, and the
        # honest answer for one of these is "nothing at all, ever".
        click.echo(
            f"Not a configuration section, so never written: "
            f"{', '.join(sorted(study.extra))}. If one of those is a typo for a "
            "section name, nothing will ever tell you but this line."
        )


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", required=False)
@click.option(
    "--section",
    "only",
    multiple=True,
    type=click.Choice(SECTIONS),
    help="Write only this section. Repeatable.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Write even though local validation found errors.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be written and stop.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def push(
    ctx: click.Context,
    path: Optional[str],
    only: Sequence[str],
    force: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Write the sections that differ from what the server holds.

    Validates locally first and refuses on errors, because `study_confs` is
    APPEND-ONLY: a POST inserts a new row and supersedes the previous one, and
    there is no way to take a bad write back -- only to write over it. `--force`
    pushes anyway.

    Unchanged sections are skipped: re-POSTing an identical section would
    append a row that changes nothing, and the history is worth keeping
    readable.

    Order is fixed and is not the file's: general, destinations, creatives,
    audiences, variables, strata, data_sources, inference_data, recruitment.
    The server checks nothing across sections, so this buys the server nothing;
    it means a push that stops half way (a 422 on creatives) leaves a prefix of
    the reference graph on the server rather than a middle of it. `recruitment`
    is last because its start/end window is what makes the study visible to the
    crons -- writing it last means the two-hourly run cannot pick up a
    half-configured study.
    """
    study = load_study(path)
    org, slug = study.require_target()
    client = get_client(ctx)

    report = validate_study(study.all_sections())
    if report.errors and not force:
        print_report(report.model_dump(), list(KNOWN_GAPS), study)
        raise click.ClickException(
            f"{len(report.errors)} validation error(s). Nothing was written. "
            "Fix them, or pass --force -- but note that study_confs is "
            "append-only, so a bad write can only be superseded, never undone."
        )

    diffs = diff_sections(study.sections, client.get_confs(org, slug))
    unchanged = [d.section for d in diffs if d.status == "unchanged"]
    plan = push_plan(diffs)
    outstanding = [d.section for d in plan]
    if only:
        plan = [d for d in plan if d.section in set(only)]

    if not plan:
        # The message has to distinguish "the study is in sync" from "the
        # sections you asked for are, and others are not". Saying the first
        # when the second is true tells an agent or a CI step that the study
        # matches the server when it does not.
        skipped_elsewhere = [s for s in outstanding if s not in set(only or ())]
        if as_json:
            emit_json(
                {
                    "written": [],
                    "skipped": unchanged,
                    "outstanding": skipped_elsewhere,
                }
            )
        elif skipped_elsewhere:
            click.echo(
                f"Nothing to push in {', '.join(sorted(only))}. "
                f"Still outstanding elsewhere: {', '.join(skipped_elsewhere)}."
            )
        else:
            click.echo("Nothing to push: every section matches the server.")
        return

    if dry_run:
        if as_json:
            emit_json({"would_write": [d.section for d in plan]})
        else:
            for d in plan:
                click.echo(f"would write {d.section} ({d.status})")
        return

    written: List[str] = []
    try:
        for d in plan:
            # `json_safe`, not `d.local`: YAML gives a `datetime.date` for an
            # unquoted `start_date: 2026-06-01`, which pydantic accepts (so
            # `validate` and `diff` both pass) and the JSON encoder does not.
            # It is NOT `stored_conf` of the parsed section -- undeclared keys
            # have to reach the server so the 422 can name them.
            client.post_conf(
                org, slug, SECTION_URL_SEGMENTS[d.section], json_safe(d.local)
            )
            written.append(d.section)
            if not as_json:
                click.echo(f"wrote {d.section} ({d.status})")
    except VlabError as e:
        # A push is nine separate POSTs with no transaction and no rollback, so
        # a failure part way through leaves earlier sections WRITTEN -- and
        # `study_confs` has no delete, so that cannot be undone. Which ones
        # landed is therefore the single most important thing to report, and in
        # `--json` mode nothing has been printed yet, so re-raising bare would
        # lose it entirely. Re-run to continue: the next diff shows only what is
        # still outstanding.
        if as_json:
            emit_json(
                {
                    "written": written,
                    "failed": plan[len(written)].section,
                    "error": str(e),
                }
            )
        else:
            click.echo("")
            click.echo(f"FAILED on {plan[len(written)].section}.")
            click.echo(
                f"{len(written)} section(s) were already written and cannot be "
                "withdrawn (study_confs is append-only). Fix the error and run "
                "`vlab push` again -- it will write only what is still "
                "outstanding."
            )
        raise click.ClickException(str(e))

    if as_json:
        emit_json(
            {
                "written": written,
                "skipped": unchanged,
                "outstanding": [s for s in outstanding if s not in set(written)],
            }
        )
        return

    click.echo("")
    click.echo(
        f"{len(written)} section(s) written. Each POST inserted a NEW row; the "
        "previous version of that section is still in study_confs and the "
        "newest row is what every reader takes."
    )
    if report.warnings:
        click.echo(
            f"{len(report.warnings)} warning(s) -- `vlab validate` to read them."
        )
    click.echo(f"Next: vlab plan {org}/{slug}")


# ---------------------------------------------------------------------------
# plan / apply
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("target")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def plan(ctx: click.Context, target: str, as_json: bool) -> None:
    """The instruction list for <org>/<slug>, with indices for `vlab apply`.

    \b
    NOT SIDE-EFFECT FREE, despite being a GET and being called a preview.
    Every run heals ad attributions (writing ad_attributions rows), reads Meta,
    and writes an adopt_reports row plus a respondents-over-time and a
    cost-over-time report. It creates no Meta objects and spends no money.
    On a large study it is also slow -- the server allows it five minutes.

    It is nonetheless the only thing that checks the Meta-side half:
    `vlab validate` is pure and cannot see whether the template campaign still
    exists. A 500 here carries the real message in `detail`.

    Reconciliation is layered, so an empty-looking plan may be correct: on a
    fresh study a working configuration returns exactly one campaign/create per
    campaign the recruitment conf names, and nothing else. Ad sets appear once
    the campaign exists; ads once the ad set does.
    """
    org, slug = parse_target(target)
    instructions = get_client(ctx).plan(org, slug)

    if as_json:
        emit_json(instructions)
        return

    if not instructions:
        click.echo(
            "No instructions: the study reconciles as it stands, or its "
            "recruitment window is closed (the crons only touch a study where "
            "start_date < now < end_date)."
        )
        return

    for i, ins in enumerate(instructions):
        name = (ins.get("params") or {}).get("name")
        target_id = ins.get("id")
        bits = [f"{i:>3}  {ins.get('node')}/{ins.get('action')}"]
        if name:
            bits.append(f"name={name!r}")
        if target_id:
            bits.append(f"id={target_id}")
        click.echo("  ".join(bits))

    click.echo("")
    click.echo(f"{len(instructions)} instruction(s).")
    click.echo(
        f"Apply one with: vlab apply {org}/{slug} <index>. Then RE-PLAN -- the "
        "list is stale the moment anything is applied, because ads are only "
        "planned for an ad set that already exists on Meta."
    )
    click.echo(
        "Or apply none: the adopt-ads cron runs the whole loop every two hours "
        "at :30 for every study inside its recruitment window."
    )


@cli.command()
@click.argument("target")
@click.argument("index", type=int)
@click.option("--yes", is_flag=True, help="Do not ask.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def apply(
    ctx: click.Context, target: str, index: int, yes: bool, as_json: bool
) -> None:
    """Apply instruction <index> of the CURRENT plan.

    The plan is recomputed here rather than read from a cache, which is
    deliberate and is why the index is an index into a fresh list: an
    instruction list goes stale the moment anything is applied, and posting a
    stale one means posting an `adset_id` that no longer means what it did.
    The cost is that this makes the plan's writes and Meta reads happen again.

    This is the one command that can spend money on Meta. It needs
    `optimize:write`, which is exactly why `optimize` is a separate scope
    resource from `studies`.
    """
    org, slug = parse_target(target)
    client = get_client(ctx)

    instructions = client.plan(org, slug)
    if not 0 <= index < len(instructions):
        raise click.ClickException(
            f"Index {index} is not in the current plan, which has "
            f"{len(instructions)} instruction(s). Re-run `vlab plan` -- the "
            "list changes as instructions are applied."
        )

    instruction = instructions[index]

    if not yes:
        if as_json:
            # The confirmation prints the instruction and a prompt on stdout,
            # which would leave `--json` output that is not JSON -- and a
            # non-interactive caller cannot answer the prompt anyway. Refusing
            # beats either silently applying or silently hanging: this is the
            # one command that spends money on Meta.
            raise click.UsageError(
                "--json needs --yes. Without it this asks for confirmation on "
                "stdout, which would not be parseable and which nothing is "
                "there to answer."
            )
        click.echo(json.dumps(instruction, indent=2, default=str))
        click.confirm(f"Apply this to {org}/{slug} on Meta?", abort=True, default=False)

    result = client.apply(org, slug, instruction)

    if as_json:
        emit_json(result)
        return

    click.echo(f"applied {instruction.get('node')}/{instruction.get('action')}")
    click.echo(f"Re-plan before applying anything else: vlab plan {org}/{slug}")


# ---------------------------------------------------------------------------
# meta
# ---------------------------------------------------------------------------


@cli.group(cls=VlabGroup)
def meta() -> None:
    """Read Meta through vlab, without holding a Facebook token.

    The server reads with the credential it already stores for you and the
    token never reaches this machine. Everything here is read-only; there is no
    write proxy.

    A user can hold more than one Facebook credential, and different tokens see
    different ad accounts. With more than one and no `--credentials-key`, the
    server answers 409 naming them rather than picking -- a wrong pick would
    surface hours later as an unexplained Meta rejection at ad-set create time.
    `vlab meta credentials` lists the names.

    No caching: every call is a live Graph read against Meta's per-app rate
    limits. Do not poll these in a loop.
    """


def _meta_out(body: Any, as_json: bool, columns: Sequence[str]) -> None:
    if as_json:
        emit_json(body)
        return

    rows = body.get("data") if isinstance(body, dict) else body
    if isinstance(rows, dict):
        rows = [rows]
    rows = rows or []

    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column)
            cells.append(value if isinstance(value, str) else short(value, 40))
        click.echo("  ".join(cells))

    paging = body.get("paging") if isinstance(body, dict) else None
    click.echo("")
    click.echo(f"{len(rows)} row(s).")
    if paging and paging.get("truncated"):
        click.echo(
            f"TRUNCATED at the server's 10-page cap after "
            f"{paging.get('pages_fetched')} pages. Continue with "
            f"--after {paging.get('after')}, or lower --limit."
        )


_credentials_key = click.option(
    "--credentials-key",
    default=None,
    help="Which Facebook credential. Same value as general.credentials_key.",
)
_limit = click.option("--limit", type=int, default=None, help="Page size (max 500).")
_after = click.option("--after", default=None, help="Resume cursor from paging.after.")
_json_flag = click.option(
    "--json", "as_json", is_flag=True, help="Machine-readable output."
)


@meta.command("credentials")
@click.option("--org", required=True, envvar="VLAB_ORG")
@_json_flag
@auth_options
@click.pass_context
def meta_credentials(ctx: click.Context, org: str, as_json: bool) -> None:
    """Your Facebook credentials by name. Never tokens.

    The only API-key-reachable way to discover a valid `general.credentials_key`.
    """
    rows = get_client(ctx).meta_credentials(org)
    _meta_out({"data": rows}, as_json, ["key", "entity", "created"])


@meta.command("adaccounts")
@click.option("--org", required=True, envvar="VLAB_ORG")
@_credentials_key
@_limit
@_after
@_json_flag
@auth_options
@click.pass_context
def meta_adaccounts(
    ctx: click.Context,
    org: str,
    credentials_key: Optional[str],
    limit: Optional[int],
    after: Optional[str],
    as_json: bool,
) -> None:
    """Ad accounts. `account_id` is what general.ad_account wants -- the BARE
    number, not the act_-prefixed `id`."""
    body = get_client(ctx).meta_adaccounts(org, credentials_key, limit, after)
    _meta_out(body, as_json, ["account_id", "id", "name"])


@meta.command("campaigns")
@click.option("--org", required=True, envvar="VLAB_ORG")
@click.option("--account", required=True, help="act_123 or 123.")
@_credentials_key
@_limit
@_after
@_json_flag
@auth_options
@click.pass_context
def meta_campaigns(
    ctx: click.Context,
    org: str,
    account: str,
    credentials_key: Optional[str],
    limit: Optional[int],
    after: Optional[str],
    as_json: bool,
) -> None:
    """Campaigns on an ad account, whatever their status -- a template campaign
    is usually paused, so filtering to active ones would hide it."""
    body = get_client(ctx).meta_campaigns(org, account, credentials_key, limit, after)
    _meta_out(body, as_json, ["id", "name"])


@meta.command("adsets")
@click.option("--org", required=True, envvar="VLAB_ORG")
@click.option("--campaign", required=True)
@_credentials_key
@_limit
@_after
@_json_flag
@auth_options
@click.pass_context
def meta_adsets(
    ctx: click.Context,
    org: str,
    campaign: str,
    credentials_key: Optional[str],
    limit: Optional[int],
    after: Optional[str],
    as_json: bool,
) -> None:
    """Ad sets, with their `targeting`.

    `--json` output goes straight into `vlab strata extract-targeting`; the ad
    set object is what that command takes, unchanged.
    """
    body = get_client(ctx).meta_adsets(org, campaign, credentials_key, limit, after)
    _meta_out(body, as_json, ["id", "name"])


@meta.command("ads")
@click.option("--org", required=True, envvar="VLAB_ORG")
@click.option("--campaign", default=None)
@click.option("--adset", default=None)
@click.option("--ad", "ad_id", default=None, help="One ad: return just its creative.")
@_credentials_key
@_limit
@_after
@_json_flag
@auth_options
@click.pass_context
def meta_ads(
    ctx: click.Context,
    org: str,
    campaign: Optional[str],
    adset: Optional[str],
    ad_id: Optional[str],
    credentials_key: Optional[str],
    limit: Optional[int],
    after: Optional[str],
    as_json: bool,
) -> None:
    """Ads with their creative nested under `creative`.

    Store that blob VERBATIM as `creatives[].template`. Do not reshape it:
    adopt diffs the stored blob against the live ad field by field, so an
    "improved" blob is a perpetual no-op rewrite.

    Exactly one of --campaign or --adset, or --ad for a single creative.

    --ad prints the creative blob as JSON with or without --json: it is the
    thing you paste into `creatives[].template`, and there is no useful
    one-line rendering of it. An ad has exactly one creative, so --limit and
    --after mean nothing there and are refused rather than ignored.
    """
    client = get_client(ctx)

    if ad_id:
        if campaign or adset:
            raise click.BadParameter("--ad is on its own; drop --campaign/--adset.")
        if limit is not None or after is not None:
            raise click.BadParameter(
                "--limit and --after do not apply to --ad: an ad has exactly "
                "one creative, so there is nothing to page."
            )
        emit_json(client.meta_ad_creative(org, ad_id, credentials_key))
        return

    if bool(campaign) == bool(adset):
        raise click.BadParameter("Pass exactly one of --campaign or --adset.")

    body = client.meta_ads(org, campaign, adset, credentials_key, limit, after)
    _meta_out(body, as_json, ["id", "name"])


# ---------------------------------------------------------------------------
# strata
# ---------------------------------------------------------------------------


@cli.group(cls=VlabGroup)
def strata() -> None:
    """Build strata. One helper among several, not the only way.

    `generate` is the dashboard's derivation -- the full factorial of the
    variables, quota as the product of the level quotas -- ported and held
    identical to the TypeScript by a replayed fixture set. It is *a* way to
    build strata. Hand-written strata are legitimate; so are strata built from
    a census spreadsheet with `adopt.authoring.sheets` and radius targeting
    with `adopt.authoring.geo`, which the Variables form cannot express at all.
    `vlab validate` checks the result either way.
    """


@strata.command("generate")
@click.argument("path", required=False)
@click.option(
    "--finish-question",
    "finish_question",
    default=None,
    help="The question ref that marks a respondent finished.",
)
@click.option(
    "--dry-run", is_flag=True, help="Print the strata instead of writing the file."
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.pass_context
def strata_generate(
    ctx: click.Context,
    path: Optional[str],
    finish_question: Optional[str],
    dry_run: bool,
    as_json: bool,
) -> None:
    """Compile `variables` into `strata`, merging with the existing strata.

    Exactly the dashboard's Regenerate, including what it preserves and what it
    overwrites. A stratum that already exists keeps its hand-edited
    `creatives`, `audiences` and `excluded_audiences`; its `facebook_targeting`,
    `question_targeting`, `metadata` and `quota` are RECOMPUTED. `quota` in
    particular: it is the product of the level quotas, so preserving it would
    mean editing a level's quota could never propagate to an existing study.

    The finish question ref comes from --finish-question, or is read off the
    first existing stratum's `answered` term. A study with neither cannot be
    compiled -- there is no stratum to write without a question that says a
    respondent finished.
    """
    study = load_study(path)
    variables = study.sections.get("variables") or []
    existing = study.sections.get("strata") or []

    if not variables:
        raise click.ClickException(
            "No `variables` section. `strata generate` derives strata from it; "
            "write it first, or write `strata` by hand -- the server stores "
            "whatever you send and `variables` is inert on it anyway."
        )

    ref = finish_question
    if not ref:
        try:
            ref = get_finish_question_ref(existing)
        except ValueError as e:
            raise click.ClickException(
                f"{e} Pass --finish-question to say which it is."
            )
    if not ref:
        raise click.ClickException(
            "No finish question ref: none was given and there are no existing "
            "strata to read one off. Pass --finish-question."
        )

    fresh = create_strata_from_variables(
        variables,
        ref,
        study.sections.get("creatives") or [],
        study.sections.get("audiences") or [],
        existing,
    )

    if dry_run:
        emit_json(fresh)
        return

    kept = {s.get("id") for s in existing} & {s["id"] for s in fresh}
    dropped = [
        s.get("id") for s in existing if s.get("id") not in {f["id"] for f in fresh}
    ]

    study.sections["strata"] = fresh
    study.save()

    if as_json:
        emit_json(
            {
                "file": study.path,
                "strata": [s["id"] for s in fresh],
                "merged": sorted(str(i) for i in kept),
                "no_longer_produced": [str(d) for d in dropped],
            }
        )
        return

    click.echo(f"{len(fresh)} strata written to {study.path}.")
    click.echo(
        f"  {len(kept)} merged with an existing stratum (creatives, "
        "audiences and exclusions kept; targeting, metadata and quota "
        "recomputed)"
    )
    if dropped:
        click.echo(
            f"  {len(dropped)} no longer produced by the variables: "
            f"{', '.join(str(d) for d in dropped[:5])}"
            f"{' …' if len(dropped) > 5 else ''}"
        )
        click.echo(
            "  A stratum id is a Meta ad set NAME. Pushing this deletes "
            "those ad sets, with their learning and their history."
        )
    click.echo("Nothing was pushed. `vlab diff` to see what would change.")


@strata.command("extract-targeting")
@click.argument("adset_json", type=click.File("r"))
@click.argument("properties", nargs=-1, required=True)
@click.option(
    "--name",
    "adset_name",
    default=None,
    help="Pick this ad set by name from a `vlab meta adsets --json` response.",
)
@click.pass_context
def strata_extract(
    ctx: click.Context,
    adset_json: Any,
    properties: Sequence[str],
    adset_name: Optional[str],
) -> None:
    """Pull targeting properties off a template ad set. Prints the JSON.

    Takes what `vlab meta adsets --json` prints -- either the whole response
    (then use --name to pick one) or a single ad set object. `-` reads stdin.

    A property that is not on the ad set is an error, not a default: silently
    omitting `geo_locations` would produce a stratum targeting a whole country.

    `targeting_automation: {advantage_audience: 0}` is always forced onto the
    result, overwriting the source ad set's -- even one you asked for by name.
    Advantage+ audience expansion leaks delivery outside a geographic stratum,
    which makes the stratum's estimate wrong, so it is never used.
    """
    body = json.load(adset_json)

    adset = body
    if isinstance(body, dict) and "data" in body:
        rows = body["data"]
        if isinstance(rows, list):
            if adset_name is None:
                if len(rows) != 1:
                    raise click.ClickException(
                        f"{len(rows)} ad sets in that response; pass --name to "
                        "pick one. Names: "
                        + ", ".join(repr(r.get("name")) for r in rows[:10])
                    )
                adset = rows[0]
            else:
                matches = [r for r in rows if r.get("name") == adset_name]
                if not matches:
                    raise click.ClickException(
                        f"No ad set named {adset_name!r}. Names: "
                        + ", ".join(repr(r.get("name")) for r in rows[:10])
                    )
                adset = matches[0]
        else:
            adset = rows

    emit_json(extract_from_adset(adset, list(properties)))


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------


@cli.group(cls=VlabGroup)
def keys() -> None:
    """List and revoke API keys.

    There is deliberately no `vlab keys create`. Minting needs a token you
    already have, and for the first key that is an Auth0 token -- a browser
    login, from the dashboard's Accounts page. A key can mint further keys only
    if it holds `auth:write`, and then only narrower ones. An agent cannot mint
    its own first key; a human hands it one. Exposing a create command would
    mostly produce a confusing 403.
    """


@keys.command("list")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def keys_list(ctx: click.Context, as_json: bool) -> None:
    """Your live API keys. Needs `auth:read`.

    Keys minted before the 2026-09-04 hardening are NOT listed: nothing was
    ever stored for them, so there is nothing to list. They are also permanent
    and unrestricted. If you were handed a key before that date, ask for a
    reissued one -- nothing you can do makes the old one expire.
    """
    body = get_client(ctx).list_api_keys()

    if as_json:
        emit_json(body)
        return

    rows = body.get("keys") or []
    for row in rows:
        scopes = ",".join(row.get("scopes") or []) or "(unrestricted)"
        flag = " EXPIRED" if row.get("expired") else ""
        click.echo(
            # `or ""` on every field: a format spec applied to None is a
            # TypeError, which is not a user error and would print a traceback
            # at somebody who only ran `vlab keys list`.
            f"{row.get('id') or ''}  {row.get('name') or '':<24} {scopes:<40} "
            f"expires {row.get('expires_at')}{flag}"
        )
    click.echo("")
    click.echo(f"{len(rows)} key(s).")

    legacy = body.get("legacy_revocations") or []
    if legacy:
        click.echo(
            f"{len(legacy)} legacy name tombstone(s): "
            + ", ".join(str(r.get("name")) for r in legacy)
        )


@keys.command("revoke")
@click.argument("key_id")
@click.option("--yes", is_flag=True, help="Do not ask.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@auth_options
@click.pass_context
def keys_revoke(ctx: click.Context, key_id: str, yes: bool, as_json: bool) -> None:
    """Revoke a key by its id (the `jti` from the mint response). Needs `auth:write`.

    404 means it is not one of YOUR live keys -- never 403, so this cannot be
    used to find out whether someone else's key exists.

    The replica that serves this drops the key at once; others honour it for up
    to 30 seconds, because row lookups (misses included) are cached in process.
    Treat revocation as "dead within a minute", not "dead now".
    """
    if not yes:
        if as_json:
            raise click.UsageError(
                "--json needs --yes: the confirmation prompt goes to stdout."
            )
        click.confirm(f"Revoke key {key_id}?", abort=True, default=False)

    get_client(ctx).revoke_api_key(key_id)

    if as_json:
        emit_json({"revoked": key_id, "other_replicas_honour_until_seconds": 30})
        return
    click.echo(f"Revoked {key_id}. Other replicas may honour it for ~30 seconds.")


def main() -> None:
    """Console-script entry point (`[tool.poetry.scripts] vlab`)."""
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()
