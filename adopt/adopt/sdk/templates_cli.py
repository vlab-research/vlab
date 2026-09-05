"""`vlab template` -- build the paused Meta objects a study is configured from.

    export FACEBOOK_ACCESS_TOKEN=EAAB...        # see AUTH below
    vlab template plan      spec.yaml           # dry run: print the Graph calls
    vlab template create    spec.yaml --create  # actually create, all PAUSED
    vlab template creative  --campaign 120… --adset 120… --name my-creative …
    vlab template check-targeting --account act_… --targeting @t.json
    vlab template delete    120…

A template campaign is authoring-time scaffolding, not recruitment. The
dashboard (and `vlab strata extract-targeting`) read *targeting* off its ad
sets and the *creative blob* off its ads; adopt then builds the study's real
objects from the study conf and never reads the template again. So everything
here is created PAUSED and nothing here can activate anything.

WHY THIS TALKS TO META DIRECTLY, unlike `vlab meta …`

`vlab meta` reads Meta through the vlab server, so no Facebook token ever
reaches this machine. That is not available here: creating a creative needs an
image upload, which would make the conf service a bytes relay, and it would put
money-spending liability on a service that today cannot spend money at all.
The decision is recorded in `planning/agent-study-authoring.md` §10 (last
bullet) and is not reopened here. The consequence is the AUTH section below:
this group, alone in `vlab`, wants a Facebook token.

AUTH

`--token`, or `FACEBOOK_ACCESS_TOKEN`. Nothing is written to disk and there is
no login command, for the same reason the rest of the CLI has none.

`FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` are optional. With both, the session
sends `appsecret_proof`, exactly as the conf service does. Without them it
sends only the token, which Meta accepts unless the app has Settings ->
Advanced -> "Require app secret" turned on. Whether the vlab app has it on is
not readable from this repository, so a token-only run prints a warning naming
the error to expect if it is (`code 1, Invalid appsecret_proof provided`)
rather than pretending to know.

INPUT: FLAGS OR A YAML SPEC, AND WHICH TO USE

A campaign has many ad sets and many ads, and neither is expressible in flags
without inventing a mini-language -- so `plan` and `create` read a YAML spec
file, which is also the artifact worth committing next to the study. `creative`
and `check-targeting` are single-object commands and take flags. The spec is
plain YAML with no schema of its own; its keys are the `AdsetSpec` / `AdSpec`
field names, and an unknown key is an error rather than a silent drop.

    account: act_1342820622846299
    name: VL Pulse Nigeria          # gains the "Templates - " marker
    properties: [genders, age_min, age_max, geo_locations]
    adsets:
      - name: Kwara - Men
        kind: messenger
        targeting:
          genders: [1]
          age_min: 18
          age_max: 65
          geo_locations:
            regions: [{key: "2619", name: Kwara, country: "NG"}]
            location_types: [home, recent]
    ads:
      - name: vlpulse-ng-1          # a JOIN KEY. Name it once, never change it.
        kind: messenger
        page_id: "1855355231229529"
        message: Tell us what you think.
        headline: Chat with us
        image: ./ad.png             # uploaded; or image_hash: <existing>
        adset: Kwara - Men

**A bare `NO` in YAML 1.1 is the boolean false, not Norway.** `country: NO`
parses as `false`, and nothing downstream notices. Quote every two-letter
country code. (The same trap is documented for `study.yaml` in
`planning/vlab-sdk.md` §6b.)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import fields as dataclass_fields
from dataclasses import replace
from typing import Any, Dict, List, Optional

import click
import yaml

from ..authoring.templates import (
    CREATIVE_KINDS,
    DELIVERY_ESTIMATE,
    REACH_ESTIMATE,
    AdsetSpec,
    AdSpec,
    TemplateError,
    TemplatePlan,
    apply,
    delete_template_campaign,
    meta_message,
    plan_template_ads,
    plan_template_campaign,
    validate_targeting,
)
from ..facebook.state import api_for_token
from .cli import VlabGroup, cli, emit_json

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _api(token: Optional[str], app_id: Optional[str], app_secret: Optional[str]):
    token = token or os.environ.get("FACEBOOK_ACCESS_TOKEN")
    if not token:
        raise click.ClickException(
            "No Facebook token. Set FACEBOOK_ACCESS_TOKEN or pass --token.\n"
            "It must be a token for a user with a role on the ad account and "
            "on the Page. `vlab meta credentials --org <org>` lists the "
            "credentials vlab holds for you, but it does not (and will not) "
            "hand out their tokens -- keeping them server-side is the whole "
            "point of the read proxy."
        )

    app_id = app_id or os.environ.get("FACEBOOK_APP_ID")
    app_secret = app_secret or os.environ.get("FACEBOOK_APP_SECRET")
    if not (app_id and app_secret):
        click.echo(
            "warning: FACEBOOK_APP_ID / FACEBOOK_APP_SECRET are unset, so no "
            "appsecret_proof is sent. That is fine unless the app has "
            '"Require app secret" enabled, in which case Meta answers '
            "'code 1, Invalid appsecret_proof provided' and you need both.",
            err=True,
        )
    return api_for_token(token, app_id, app_secret)


def meta_options(command):
    """The three Meta credentials, on every command in this group."""
    command = click.option(
        "--app-secret",
        envvar="FACEBOOK_APP_SECRET",
        default=None,
        help="Enables appsecret_proof. Prefer the environment variable.",
    )(command)
    command = click.option(
        "--app-id", envvar="FACEBOOK_APP_ID", default=None, help="See --app-secret."
    )(command)
    return click.option(
        "--token",
        envvar="FACEBOOK_ACCESS_TOKEN",
        default=None,
        help="Facebook access token. Prefer the environment variable.",
    )(command)


# ---------------------------------------------------------------------------
# The spec file
# ---------------------------------------------------------------------------


def _dataclass_from(kind: str, cls, raw: Any, where: str):
    """Build an `AdsetSpec` / `AdSpec` from a mapping, refusing unknown keys.

    Unknown keys are an error, not a drop, for exactly the reason
    `planning/vlab-sdk.md` §4 gives about the conf models: a misspelled
    optional field that is silently ignored produces a template that is subtly
    not the one you wrote, and nothing ever says so. Here the cost is higher
    than for a conf, because the object is on someone's ad account by the time
    you notice.
    """
    if not isinstance(raw, dict):
        raise click.ClickException(
            f"{where}: expected a mapping, got {type(raw).__name__}."
        )
    known = {f.name for f in dataclass_fields(cls)}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise click.ClickException(
            f"{where}: unknown key(s) {unknown}. Known keys for a {kind}: "
            f"{sorted(known)}."
        )
    try:
        return cls(**raw)
    except TypeError as e:
        # A missing required key. The dataclass's own message names the field,
        # and it is clearer than anything reconstructed from
        # `dataclass_fields`; `where` is an index, so the entry's own `name` is
        # added when it has one -- that is what a reader is scanning the file
        # for.
        named = f" ({raw['name']!r})" if isinstance(raw.get("name"), str) else ""
        raise click.ClickException(f"{where}{named}: {e}") from e


def _load_spec(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise click.ClickException(f"No such spec file: {path}")
    with open(path, encoding="utf8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            # `yaml.YAMLError` is neither ValueError nor OSError, so it walks
            # past `VlabGroup.invoke` and prints a traceback if it is not
            # caught here. The same bug was found and fixed for `study.yaml`.
            raise click.ClickException(f"{path} is not valid YAML: {e}") from e

    if not isinstance(raw, dict):
        raise click.ClickException(
            f"{path}: expected a mapping at the top level (account, name, "
            "adsets, ads)."
        )

    known = {"account", "name", "objective", "properties", "adsets", "ads"}
    unknown = sorted(set(raw) - known)
    if unknown:
        raise click.ClickException(
            f"{path}: unknown top-level key(s) {unknown}. Known: {sorted(known)}."
        )
    return raw


def _plan_from_spec(path: str) -> TemplatePlan:
    raw = _load_spec(path)
    for required in ("account", "name"):
        if not raw.get(required):
            raise click.ClickException(f"{path}: '{required}' is required.")

    adsets = [
        _dataclass_from("adset", AdsetSpec, a, f"{path}: adsets[{i}]")
        for i, a in enumerate(raw.get("adsets") or [])
    ]
    ads = [
        _dataclass_from("ad", AdSpec, a, f"{path}: ads[{i}]")
        for i, a in enumerate(raw.get("ads") or [])
    ]

    # Image paths are relative to the SPEC, not to the shell's cwd. A spec
    # committed next to its images has to work from anywhere.
    base = os.path.dirname(os.path.abspath(path))
    ads = [
        a
        if not a.image or os.path.isabs(a.image)
        else replace(a, image=os.path.normpath(os.path.join(base, a.image)))
        for a in ads
    ]

    return plan_template_campaign(
        account_id=raw["account"],
        name=raw["name"],
        adsets=adsets,
        ads=ads,
        **({"objective": raw["objective"]} if raw.get("objective") else {}),
        **({"properties": raw["properties"]} if raw.get("properties") else {}),
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _print_plan(plan: TemplatePlan) -> None:
    click.echo(
        f"account   {plan.account_id}\n"
        f"campaign  {plan.campaign_name or plan.campaign_id}"
        + ("  (exists)" if plan.campaign_id else "  (new)")
    )
    if plan.properties:
        click.echo(f"declare   {json.dumps(list(plan.properties))}")
    click.echo("")
    for c in plan.creates:
        label = c.params.get("name") or c.source or ""
        click.echo(f"  {c.node:<9} {label!r:<28} {c.edge}")
    click.echo("")
    for w in plan.warnings:
        click.echo(f"warning: {w}", err=True)


def _print_result(result) -> None:
    click.echo(f"campaign  {result.campaign_id}  PAUSED")
    for a in result.adsets:
        click.echo(f"  adset   {a['id']}  {a['name']!r}  PAUSED")
    for a in result.ads:
        click.echo(f"  ad      {a['id']}  {a['name']!r}  PAUSED")
    for w in result.warnings:
        click.echo(f"warning: {w}", err=True)
    if result.ads:
        click.echo("")
        click.echo(
            "The creative blobs are in `--json` output under ads[].template -- "
            "that is exactly what a `creatives` conf wants as its `template`, "
            "read back from Meta rather than echoed."
        )


# ---------------------------------------------------------------------------
# The group
# ---------------------------------------------------------------------------


class TemplateGroup(VlabGroup):
    """`VlabGroup` plus `TemplateError`.

    `VlabGroup.invoke` turns a known user error into a `ClickException` -- a
    one-line message rather than a traceback -- from a `USER_ERRORS` tuple in
    `cli.py`. `TemplateError` belongs in that tuple, but adding it there would
    be a second edit to `cli.py`, and this branch keeps that file's diff to the
    single line that registers this group so that merging review fixes into it
    stays trivial. Subclassing costs three lines and says the same thing.
    """

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except (click.ClickException, click.exceptions.Abort, SystemExit):
            raise
        except TemplateError as e:
            raise click.ClickException(str(e))


@cli.group(cls=TemplateGroup)
def template() -> None:
    """Author template campaigns, ad sets, creatives and ads on Meta.

    \b
    Everything created here is PAUSED and stays PAUSED; this group cannot
    activate anything, and it refuses to touch a campaign whose name does not
    start with "Templates - ".

    \b
    Unlike every other `vlab` command, this one talks to Meta directly and
    needs a Facebook token (FACEBOOK_ACCESS_TOKEN). See the module help for
    why, and for the appsecret_proof question.

    \b
    Dry run is the default: `plan` prints exactly what `create` would send.
    """


@template.command("plan")
@click.argument("spec", type=click.Path())
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def template_plan(spec: str, as_json: bool) -> None:
    """Print the Graph calls a spec would make. Touches nothing, needs no token.

    \b
    Pure: no network, so this works offline and on a machine with no Facebook
    credentials at all. Everything checkable without Meta is checked here --
    the declared-property contract, the budget ceiling, unknown spec keys,
    missing image files -- so a clean plan is a real signal.
    """
    plan = _plan_from_spec(spec)
    if as_json:
        emit_json(plan.to_dict())
        return
    _print_plan(plan)
    click.echo("DRY RUN -- nothing created. `vlab template create` applies it.")


@template.command("create")
@click.argument("spec", type=click.Path())
@click.option(
    "--create",
    "confirmed",
    is_flag=True,
    help="Required. Without it this prints the plan and stops.",
)
@click.option("--yes", is_flag=True, help="Same as --create; do not ask.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@meta_options
def template_create(
    spec: str,
    confirmed: bool,
    yes: bool,
    as_json: bool,
    token: Optional[str],
    app_id: Optional[str],
    app_secret: Optional[str],
) -> None:
    """Create the campaign, ad sets, creatives and ads in SPEC. All PAUSED.

    \b
    Requires --create (or --yes). Without it you get the plan and nothing else,
    which is the same output as `vlab template plan`.

    \b
    Refused before anything is created if a campaign of that name already
    exists on the account: two campaigns with one name make
    `FacebookState.campaign` raise StateNameError, which breaks the run path of
    any study naming that campaign. Delete and re-run is the recoverable path.

    \b
    There is no rollback. If Meta refuses object four of six, objects one to
    three exist; the error names which one failed and how to delete the
    campaign.
    """
    plan = _plan_from_spec(spec)

    if not (confirmed or yes):
        _print_plan(plan)
        raise click.ClickException(
            "Refusing to create without --create (or --yes). The plan above is "
            "what would be sent."
        )

    result = apply(plan, _api(token, app_id, app_secret))

    if as_json:
        emit_json(result.to_dict())
        return
    _print_result(result)
    click.echo("")
    click.echo(f"Delete it all again with: vlab template delete {result.campaign_id}")


@template.command("creative")
@click.option("--campaign", required=True, help="Template campaign id to add to.")
@click.option("--adset", "adset_id", required=True, help="Ad set id to hang it on.")
@click.option("--account", required=True, help="act_123 or 123.")
@click.option(
    "--name",
    required=True,
    help="The creative name. A JOIN KEY -- mint_ref_token is keyed on it and "
    "reconciliation matches ads by it. Name it once.",
)
@click.option("--kind", type=click.Choice(CREATIVE_KINDS), default="messenger")
@click.option("--page-id", required=True, help="The Page the ad posts as.")
@click.option("--message", required=True, help="The ad's primary text.")
@click.option("--headline", default=None, help="link_data.name / video_data.title.")
@click.option("--description", default=None)
@click.option(
    "--image",
    type=click.Path(),
    default=None,
    help="Local file to upload. The ad's image, or a video's thumbnail.",
)
@click.option("--image-hash", default=None, help="An image already on the account.")
@click.option(
    "--video-id",
    default=None,
    help="A video already on the account. Also needs an image (thumbnail) "
    "and a headline.",
)
@click.option("--instagram-user-id", default=None)
@click.option("--link", default=None, help="Required for web and app.")
@click.option("--deeplink", default=None, help="Required for app.")
@click.option("--create", "confirmed", is_flag=True, help="Required to write.")
@click.option("--yes", is_flag=True, help="Same as --create.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@meta_options
def template_creative(
    campaign: str,
    adset_id: str,
    account: str,
    name: str,
    kind: str,
    page_id: str,
    message: str,
    headline: Optional[str],
    description: Optional[str],
    image: Optional[str],
    image_hash: Optional[str],
    video_id: Optional[str],
    instagram_user_id: Optional[str],
    link: Optional[str],
    deeplink: Optional[str],
    confirmed: bool,
    yes: bool,
    as_json: bool,
    token: Optional[str],
    app_id: Optional[str],
    app_secret: Optional[str],
) -> None:
    """Build one creative, upload its image, and hang a PAUSED ad on an ad set.

    \b
    This is the command that exists because the creative is the thing a
    researcher cannot get an agent to do: everything else about a template can
    be lifted off an ad set that already exists.

    \b
    Two checks before anything is created, and BOTH are needed. --campaign must
    carry the "Templates - " marker, AND --adset must actually belong to that
    campaign: an ad is created with an adset_id and no campaign of its own, so
    the AD SET is what decides which campaign the ad lands in. Checking only
    the name would let a marked --campaign paired with someone else's ad set
    put a paused ad inside a live study.

    \b
    For a video creative pass --video-id AND an image (--image or
    --image-hash), which is its thumbnail, AND --headline. Meta's video_data
    wants all three, and adopt copies them with no null filter.

    \b
    On success the JSON output carries `ads[0].template` -- the creative as
    Meta returns it, which is exactly what a `creatives` conf wants.
    """
    ad = AdSpec(
        name=name,
        kind=kind,
        page_id=page_id,
        message=message,
        headline=headline,
        description=description,
        image=image,
        image_hash=image_hash,
        video_id=video_id,
        instagram_user_id=instagram_user_id,
        link=link,
        deeplink=deeplink,
    )
    plan = plan_template_ads(
        account_id=account, campaign_id=campaign, adset_id=adset_id, ads=[ad]
    )

    if not (confirmed or yes):
        _print_plan(plan)
        raise click.ClickException("Refusing to create without --create (or --yes).")

    result = apply(plan, _api(token, app_id, app_secret))
    if as_json:
        emit_json(result.to_dict())
        return
    _print_result(result)


@template.command("delete")
@click.argument("campaign_id")
@click.option("--yes", is_flag=True, help="Do not ask.")
@click.option(
    "--force",
    is_flag=True,
    help="Delete even if it is delivering. Never skips the name check.",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@meta_options
def template_delete(
    campaign_id: str,
    yes: bool,
    force: bool,
    as_json: bool,
    token: Optional[str],
    app_id: Optional[str],
    app_secret: Optional[str],
) -> None:
    """Delete a template campaign and everything under it.

    \b
    Refuses any campaign whose name does not start with "Templates - ", and any
    marked one whose effective_status says it is delivering (--force skips only
    the second check). A template is created PAUSED and should never be
    delivering; if it is, somebody activated it and the reason is not knowable
    from here.
    """
    if not yes:
        click.confirm(
            f"Delete campaign {campaign_id} and every ad set and ad under it?",
            abort=True,
            default=False,
        )
    out = delete_template_campaign(
        _api(token, app_id, app_secret), campaign_id, force=force
    )
    if as_json:
        emit_json(out)
        return
    click.echo(f"deleted campaign {out['deleted']}  {out['name']!r}")


@template.command("check-targeting")
@click.option("--account", required=True, help="act_123 or 123.")
@click.option(
    "--targeting",
    default=None,
    help="A targeting spec as JSON, or @path/to/file.json.",
)
@click.option(
    "--spec",
    "spec_path",
    type=click.Path(),
    default=None,
    help="A template spec file: checks every ad set in it.",
)
@click.option(
    "--edge",
    type=click.Choice([REACH_ESTIMATE, DELIVERY_ESTIMATE]),
    default=REACH_ESTIMATE,
    show_default=True,
)
@click.option(
    "--optimization-goal",
    default=None,
    help=f"Required for {DELIVERY_ESTIMATE}.",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@meta_options
def template_check_targeting(
    account: str,
    targeting: Optional[str],
    spec_path: Optional[str],
    edge: str,
    optimization_goal: Optional[str],
    as_json: bool,
    token: Optional[str],
    app_id: Optional[str],
    app_secret: Optional[str],
) -> None:
    """Ask Meta whether a targeting spec is valid, without creating anything.

    \b
    Read-only. It creates nothing and spends nothing, which makes it the
    cheapest answer to "will this ad set be accepted" -- today the only other
    answer is to create one. A `geo_locations.regions[].key` wrong by one digit
    comes back as a Meta 400 naming the key, instead of being discovered at
    ad-set create time with a campaign already on the account.

    \b
    Neither edge has been exercised against live Meta from this code. If
    reachestimate answers "Unsupported get request", try
    --edge delivery_estimate --optimization-goal CONVERSATIONS.
    """
    if bool(targeting) == bool(spec_path):
        raise click.UsageError("Give exactly one of --targeting or --spec.")

    api = _api(token, app_id, app_secret)
    cases: List[Dict[str, Any]] = []

    if targeting:
        cases = [{"name": "(--targeting)", "targeting": _read_json(targeting)}]
    else:
        raw = _load_spec(spec_path)  # type: ignore[arg-type]
        # Through `_dataclass_from`, not straight off the YAML, so that this
        # command applies the SAME unknown-key check `plan` does. Review caught
        # the raw read: a spec with a misspelled ad-set key exited 0 here and 1
        # under `plan`, and the whole point of check-targeting is that it runs
        # BEFORE plan -- a green check on a spec plan will reject is worse than
        # no check.
        #
        # Only the ad sets are built. The ads are irrelevant to a targeting
        # question, and requiring them to be valid would stop a researcher
        # checking their targeting before the creative exists, which is the
        # ordinary order of work.
        specs = [
            _dataclass_from("adset", AdsetSpec, a, f"{spec_path}: adsets[{i}]")
            for i, a in enumerate(raw.get("adsets") or [])
        ]
        if not specs:
            raise click.ClickException(f"{spec_path} declares no ad sets.")
        # Refused here rather than sent: `json.dumps(None)` is the string
        # "null", which Meta answers with a message about `targeting_spec`
        # being malformed -- true, and useless for finding the ad set that is
        # missing it.
        empty = [s.name for s in specs if not isinstance(s.targeting, dict)]
        if empty:
            raise click.ClickException(
                f"{spec_path}: ad set(s) {empty} have no targeting to check."
            )
        cases = [{"name": s.name, "targeting": s.targeting} for s in specs]

    out = []
    failed = False
    for case in cases:
        try:
            body = validate_targeting(
                api,
                account,
                case["targeting"],
                edge=edge,
                optimization_goal=optimization_goal,
            )
            out.append({"name": case["name"], "ok": True, "result": body})
        except Exception as e:  # noqa: BLE001 -- a Meta rejection IS the answer
            failed = True
            # `meta_message`, not `str(e)`: the SDK's own string interpolates
            # the whole request context, burying the one sentence Meta said.
            out.append({"name": case["name"], "ok": False, "error": meta_message(e)})

    if as_json:
        emit_json(out)
    else:
        for row in out:
            if row["ok"]:
                data = row["result"].get("data")
                click.echo(f"ok      {row['name']}  {json.dumps(data)}")
            else:
                click.echo(f"FAILED  {row['name']}  {row['error']}", err=True)

    if failed:
        sys.exit(1)


def _read_json(value: str) -> Any:
    """Inline JSON, or `@path`. Same convention as curl's `-d @file`."""
    if value.startswith("@"):
        path = value[1:]
        if not os.path.exists(path):
            raise click.ClickException(f"No such file: {path}")
        with open(path, encoding="utf8") as f:
            value = f.read()
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Not valid JSON: {e}") from e
