"""The MCP tool surface: written once, served over stdio and over HTTP.

Phase 4 of `planning/agent-study-authoring.md` §16; `planning/mcp.md` records
what shipped. Two transports, one module:

* **stdio** -- `vlab mcp`, on the researcher's or the agent's machine. Every
  tool reaches the service over HTTP through `sdk.client.VlabClient`, so scopes
  are enforced by the service's own route middleware on every underlying call
  and this side needs no scope logic at all.
* **streamable HTTP** -- `POST /mcp` on the conf service (`server/mcp_server.py`).
  Tools call the route handlers in process and therefore never pass through the
  middleware, so scopes ARE checked here, per tool, against `TOOL_SCOPES`.

NO TOOL CONTAINS LOGIC
----------------------

Every tool below is argument shaping around a function the `vlab` CLI already
calls: `client.*`, `study.push_sections`, `study.diff_sections`,
`authoring.validate.validate_study`, `authoring.strata`, `authoring.extract`.
That is plan §7's "one implementation" row applied to MCP, and it is the whole
reason Phase 3 came first. If a tool ever needs to *decide* something, the
decision belongs in the shared function and both front doors get it.

The one thing tools do own is their DESCRIPTION. Those are the product surface:
an agent's entire model of vlab is what it reads there, so each carries the
mental model it needs to not do damage -- confs are append-only and a POST is
the update, the reference graph runs creatives -> destinations and strata ->
creatives + audiences, regenerating strata recomputes quota and renaming a
stratum deletes an ad set, `plan_study` reads Meta and writes. `test_mcp_tools`
asserts every tool has one, that it is substantial, and that it names its scope
and its side effects.

THE ENVIRONMENT, AND WHY IT IS A CONTEXTVAR
-------------------------------------------

A tool needs two things that differ per transport and, on the remote one, per
REQUEST: the backend it calls, and whether this caller may call it. FastMCP
hands a tool only its declared arguments, so those two arrive in a contextvar
set by whichever transport is serving (`use()`), rather than by closing over
them at registration time -- which would work for stdio, where the backend is
fixed for the process, and not for `/mcp`, where every request is a different
user with different scopes.

THE BACKEND CONTRACT
--------------------

`VlabClient`'s method surface, exactly, and returning exactly what it returns:
`list_orgs`, `list_studies`, `create_study`, `get_confs`, `post_conf`,
`validate`, `plan`, `apply`, `meta_*`, `list_api_keys`, `revoke_api_key`.
`ClientBackend` below is the HTTP
one; `server/mcp_server.InProcessBackend` is the other, and it raises the same
`client.VlabHTTPError` subclasses so that a 404 reads the same to a tool
whichever side of the wire it came from.

Backends are ASYNC because FastMCP runs a synchronous tool on its event loop:
the in-process backend has to await route handlers, and blocking the loop with
`requests` would be wrong on the remote transport (and merely rude on stdio).
`ClientBackend` therefore puts the synchronous `VlabClient` on a worker thread.
That is a real gain only on the local transport, where the thread is waiting on
a socket; in process, a backend call is a handler call and occupies the loop for
whatever the handler occupies it for. See `_CallableFromThread`.
"""

import functools
import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence

import anyio

from ..authoring.extract import extract_from_adset
from ..authoring.strata import create_strata_from_variables, get_finish_question_ref
from ..authoring.validate import KNOWN_GAPS
from ..authoring.validate import validate_study as _validate_study
from .study import (
    SECTIONS,
    PushFailed,
    PushRefused,
    diff_sections,
    push_plan,
    push_sections,
    value_diff,
)

SERVER_NAME = "vlab"

# How many leaf changes `diff_study` reports per section before it stops
# listing them. Much larger than the CLI's twelve, which is a terminal-height
# number: an agent can read a hundred lines and the count of what was elided is
# reported either way, so the cap bounds the payload rather than hiding the
# fact of a change.
MAX_DIFF_LEAVES = 100


# --------------------------------------------------------------------------
# Scopes
# --------------------------------------------------------------------------

# The scope each tool needs, evaluated per call on the remote transport by
# `server/mcp_server.py` with `api_keys.scopes_allow` -- the same function the
# routes use, so `write` implies `read` and an absent scopes claim is
# unrestricted. `None` means the tool is PURE: it computes and reads nothing.
#
# A tool missing from this table is DENIED, never allowed by default
# (§16.3). `test_mcp_tools` introspects the registered server and fails on a
# missing entry, so adding a tool without deciding its scope is a test failure
# rather than a hole.
#
# DIVERGENCE FROM THE PLAN, DELIBERATE. §16.2's table gives `plan_study` and
# `apply_instruction` `studies:write`. The routes they call do not: `GET
# /{org}/optimize/{slug}` is `optimize:read` and `POST .../instruction` is
# `optimize:write` (`api_keys.required_scope`). Following the plan would make
# `/mcp` a way for a `studies:write` key to run the optimizer and spend money on
# Meta -- exactly what `optimize` was cut out of `studies` to prevent, and a
# privilege the same key does not have over HTTP. The rule §16.3 actually states
# is that this table reproduces what the routes enforce; where the two halves of
# the plan disagree, that rule wins. It also means the two transports demand the
# same scopes, which is what makes the drift guard meaningful.
TOOL_SCOPES: Dict[str, Optional[str]] = {
    "list_orgs": "studies:read",
    "list_studies": "studies:read",
    "create_study": "studies:write",
    "pull_study": "studies:read",
    "validate_study": "studies:read",
    "diff_study": "studies:read",
    "push_study": "studies:write",
    "compile_strata": None,
    "extract_targeting": None,
    "plan_study": "optimize:read",
    "apply_instruction": "optimize:write",
    "meta_credentials": "meta:read",
    "meta_adaccounts": "meta:read",
    "meta_campaigns": "meta:read",
    "meta_adsets": "meta:read",
    "meta_ads": "meta:read",
    "list_api_keys": "auth:read",
    "revoke_api_key": "auth:write",
}


class ScopeError(Exception):
    """A tool the caller's key is not scoped for.

    Raised by the authorizer, so it surfaces as a TOOL error naming the scope
    rather than as a transport error: an agent that gets a 403 on `POST /mcp`
    learns only that something is wrong, whereas one that gets "this tool needs
    optimize:write" on the call it made can say what to ask a human for.
    """


# --------------------------------------------------------------------------
# The per-call environment
# --------------------------------------------------------------------------


def _allow_everything(tool_name: str) -> None:
    """The stdio authorizer. The service checks scopes on every underlying
    call, so checking them again here would be a second, drifting copy of the
    rule -- and one that cannot see the token."""


@dataclass(frozen=True)
class ToolEnv:
    backend: Any
    authorize: Callable[[str], None] = _allow_everything


_ENV: ContextVar[Optional[ToolEnv]] = ContextVar("vlab_mcp_env", default=None)


@contextmanager
def use(env: ToolEnv) -> Iterator[ToolEnv]:
    """Bind the environment tools run in, for the duration of the block.

    stdio wraps the whole server run in one of these; `/mcp` wraps each
    request. A task spawned inside the block keeps its own copy of the context,
    so the request's environment outlives the block if the response does.
    """
    token = _ENV.set(env)
    try:
        yield env
    finally:
        _ENV.reset(token)


def current_env() -> ToolEnv:
    env = _ENV.get()
    if env is None:
        # A defect, not a user error: it means a transport called a tool
        # without binding one. Loud, because the alternative is a tool quietly
        # reaching for a backend that is not there.
        raise RuntimeError(
            "No vlab MCP environment is bound. A transport must call "
            "`use(ToolEnv(...))` around the request it serves."
        )
    return env


def backend() -> Any:
    return current_env().backend


class ClientBackend:
    """`VlabClient` with every method awaitable, off the event loop.

    Deliberately `__getattr__` rather than a dozen hand-written wrappers: the
    backend contract IS the client's surface, and spelling it out again here
    would be a second list to keep in step for no gain. A method the client
    does not have raises `AttributeError` at the call, which is where a typo in
    a tool should surface.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Callable[..., Any]:
        method = getattr(self._client, name)

        async def call(*args: Any, **kwargs: Any) -> Any:
            return await anyio.to_thread.run_sync(
                functools.partial(method, *args, **kwargs)
            )

        return call


class _CallableFromThread:
    """A backend's async methods, callable synchronously from a worker thread.

    Exists for exactly one caller: `study.push_sections`, which is synchronous
    -- the CLI calls it straight -- and which is the shared definition of what a
    push is. Rather than give the MCP tool its own copy of that loop (nine
    ordered POSTs, what to do when the seventh fails against an append-only
    table), the tool runs the real function on a worker thread and this hands
    its `client.get_confs` / `client.post_conf` calls back to the event loop.

    Works for any backend, so neither of them needs a synchronous twin.

    WHAT THIS DOES AND DOES NOT BUY, because the shape invites a wrong reading.
    The thread is there so `push_sections` can stay SYNCHRONOUS -- it is not a
    way to get work off the event loop. Each hop back through
    `anyio.from_thread.run` runs the backend method IN the loop, so on the
    remote transport the handler's blocking psycopg runs there exactly as it
    does when the same handler serves an HTTP request: net loop time is
    identical to the HTTP path, which is why this is not a regression, and it is
    not an improvement either. (`InProcessBackend` inherits whatever the handler
    does about that -- `get_all_confs` blocks, `validate_study_endpoint` and the
    meta routes use `asyncio.to_thread`.) On the local transport the inner
    `ClientBackend` puts the real HTTP call on a thread of its own, so there the
    loop is genuinely free while the request is in flight.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def __getattr__(self, name: str) -> Callable[..., Any]:
        method = getattr(self._backend, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            return anyio.from_thread.run(functools.partial(method, *args, **kwargs))

        return call


# --------------------------------------------------------------------------
# Tools: discovery
# --------------------------------------------------------------------------


async def list_orgs() -> Dict[str, Any]:
    """List the organisations this API key belongs to. Needs `studies:read`.

    Reads only; writes nothing. START HERE. Every other tool takes an `org`,
    and an organisation UUID is the one argument you cannot guess or derive:
    every address on this service is `/{org}/studies/...`, and a wrong org id
    gets a 404 that deliberately refuses to say whether the org does not exist
    or is simply not yours.

    Returns `{"orgs": [{"id", "name"}]}`. `id` is what every other tool wants.
    `name` may be null -- the column is nullable and nothing has ever required
    one -- so identify an org by its id, never by its name.

    An empty list is a real answer and not an error: the key's user is in no
    organisation at all, and NOTHING else here will work for them. That needs a
    human to add them to one; no key can do it, because there is no route that
    creates an org or grants membership.

    Scoped `studies:read` rather than a scope of its own. An org is the
    namespace a study lives in, and the only thing this reveals is which
    `/{org}/...` prefixes will not 404 -- so any key that can read a study can
    find out where to look for it. Next: `list_studies`.
    """
    return {"orgs": await backend().list_orgs()}


async def list_studies(
    org: str, limit: Optional[int] = None, offset: Optional[int] = None
) -> Dict[str, Any]:
    """List the studies in an organisation, newest first. Needs `studies:read`.

    Reads only; writes nothing. This is how you get a SLUG, which is what
    `pull_study`, `diff_study`, `push_study`, `plan_study` and
    `apply_instruction` all address a study by, and which is derived
    server-side in a way you cannot compute (apostrophes are deleted rather
    than replaced, so "Nandan's study" is "nandans-study").

    Returns `{"studies": [{"id", "name", "slug", "created"}], "count": n}`.
    `created` is ISO 8601 with an explicit UTC offset -- note that
    `create_study` reports the same field as `createdAt` in milliseconds, for
    compatibility with the dashboard, and the two are not the same shape.

    You see every study in an org you are a MEMBER of, whoever created it. A
    404 means the org is not yours or does not exist; the two are deliberately
    indistinguishable, and a malformed UUID gets the same answer again.

    `limit` is 1..500 and defaults to 100; `offset` skips rows. An org with
    more studies than the limit is silently truncated, so page rather than
    assuming one call is the whole list.

    An empty list means the org has no studies YET -- it is not evidence that a
    slug you already hold is wrong. Nothing here validates a slug: `pull_study`
    returns `{}` for a study that does not exist just as it does for one never
    configured, and only a write ever 404s on a bad slug.
    """
    studies = await backend().list_studies(org, limit, offset)
    return {"studies": studies, "count": len(studies)}


# --------------------------------------------------------------------------
# Tools: studies
# --------------------------------------------------------------------------


async def create_study(org: str, name: str) -> Dict[str, Any]:
    """Create an empty study and return its server-assigned slug. Needs `studies:write`.

    WRITES. It inserts a study row; there is no delete, so a study created by
    mistake stays in the org's list forever.

    The slug is derived server-side and is NOT a slugification you can predict:
    apostrophes are deleted rather than replaced, so "Nandan's study" becomes
    "nandans-study". Read it off this response and use it for every later call;
    computing it yourself gets 404s.

    `org` is an organisation UUID; `list_orgs` is what hands you one. A 404
    "Organization not found" means either that the org does not exist or that
    the caller is not a member of it; the two are deliberately
    indistinguishable, so check `list_orgs` rather than guessing which.

    A study created here has NO configuration at all. Next: `push_study` with
    the nine sections, then `plan_study`.
    """
    return await backend().create_study(org, name)


async def pull_study(org: str, slug: str) -> Dict[str, Any]:
    """Read a study's stored configuration, section by section. Needs `studies:read`.

    Reads only; writes nothing.

    Returns the NEWEST row per conf type. `study_confs` is append-only: every
    write inserts a new row and supersedes the previous one, so what you get
    back is the current state and the history is invisible here.

    AN EMPTY RESULT PROVES NOTHING EITHER WAY. This does not check that the
    study exists: a slug that is not there and a study that has simply never
    been configured both come back as `{}` with all nine sections in
    `never_written`. Neither this tool nor `diff_study` will tell you a slug is
    wrong -- only a write does. `create_study` is what hands you the slug, and
    it is derived server-side, so keep it rather than recomputing it.

    Keys are the STORED names (`data_sources`, `inference_data`, with
    underscores), which is exactly what `validate_study`, `diff_study` and
    `push_study` take. Nothing needs renaming between them.

    The nine sections and how they reference each other: `general` (the Meta ad
    account and which stored Facebook credential to use), `recruitment` (the
    campaign, the budget, and the start/end window that switches the study on),
    `destinations` (where a respondent lands -- a Messenger bot, a WhatsApp
    number, an app), `creatives` (each names ONE destination by name),
    `audiences`, `variables` (the dashboard's form for deriving strata; inert
    on the server), `strata` (each names creatives and audiences BY NAME, and
    its id is the Meta ad set name), `data_sources`, `inference_data`.
    """
    confs = await backend().get_confs(org, slug)
    return {
        "sections": confs,
        "never_written": [s for s in SECTIONS if s not in confs],
        "unrecognised": sorted(k for k in confs if k not in SECTIONS),
    }


async def validate_study(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Check a whole study for errors and warnings. Needs `studies:read`.

    PURE and instant: it runs `adopt.authoring.validate.validate_study` in
    process, writes nothing, touches no database, and needs no study to exist. Use it on
    sections you are ABOUT to write -- `study_confs` is append-only, so a bad
    write can only be superseded, never undone, and this is the only thing that
    catches a broken reference before it is stored.

    `sections` is the whole study keyed as stored, the same shape `pull_study`
    returns. An absent section is reported as missing, not assumed.

    What it checks: that each section parses; that every creative names a
    destination that exists; that every stratum names creatives and audiences
    that exist; that stratum ids are unique; that question targeting refers to
    declared variables; that inference data names real data sources.

    What it CANNOT check, and this matters: nothing on the Meta side. Whether
    the template campaign still exists, whether the creative template is still
    valid, whether Meta accepts your objective/optimization_goal pairing --
    none of it. `known_gaps` in the result spells this out. `plan_study` is
    what exercises the Meta half.

    Warnings do not make a study invalid: a study recruiting uniformly is
    entitled to a thin ref, and one not yet wired to a survey platform is
    unfinished rather than broken. Branch on `valid`.

    Scoped `studies:read` even though it reads nothing, so that the scope a key
    needs for this tool never has to be WIDENED later -- widening one silently
    breaks every key already issued.
    """
    report = _validate_study(sections)
    return {**report.model_dump(), "known_gaps": list(KNOWN_GAPS)}


async def diff_study(org: str, slug: str, sections: Dict[str, Any]) -> Dict[str, Any]:
    """Compare proposed sections against what the server holds. Needs `studies:read`.

    Reads only; writes nothing. Run it before `push_study` to see what a push
    would append.

    It compares what would be STORED, not what would be sent: the server keeps
    `model_dump()` of your body, so unknown keys are gone and defaults are
    filled in. Comparing raw bodies would report every section whose value
    omits an optional field as changed, forever.

    Per section the status is `new` (nothing stored yet), `changed`,
    `unchanged`, or `remote_only` (stored, and absent from what you passed --
    note that `push_study` will NOT delete it; there is no delete). `unknown`
    lists paths the models do not declare, which are the ones the server will
    422 on.

    `changes` is the per-leaf diff, capped. Section-level "changed" is almost no
    information on `strata`, and the difference between a quota moving and every
    stratum being renamed is enormous: a stratum id IS a Meta ad set name, so
    renaming one deletes that ad set on the next reconcile, with its learning
    and its history.
    """
    stored = await backend().get_confs(org, slug)
    diffs = diff_sections(sections, stored)

    out: List[Dict[str, Any]] = []
    for d in diffs:
        leaves = value_diff(d.stored, d.local) if d.status == "changed" else []
        out.append(
            {
                "section": d.section,
                "status": d.status,
                "unknown_keys": list(d.unknown),
                "changes": [
                    {"path": path, "stored": repr(was), "proposed": repr(now)}
                    for path, was, now in leaves[:MAX_DIFF_LEAVES]
                ],
                "changes_elided": max(0, len(leaves) - MAX_DIFF_LEAVES),
            }
        )

    return {"sections": out, "would_push": [d.section for d in push_plan(diffs)]}


async def push_study(
    org: str, slug: str, sections: Dict[str, Any], force: bool = False
) -> Dict[str, Any]:
    """Write the sections that differ from what the server holds. Needs `studies:write`.

    WRITES, IRREVERSIBLY. `study_confs` is append-only: each section is a POST
    that inserts a NEW row and supersedes the previous one. There is no update
    and no delete -- POSTING IS THE UPDATE -- so a bad write can only be
    written over, never withdrawn, and the old row stays in the table.

    Validates locally first and refuses on errors, writing nothing at all
    (`refused: true`, with the findings). `force` writes anyway; use it only
    when you know better than the validator.

    Unchanged sections are skipped, because re-POSTing an identical section
    appends a row that changes nothing.

    Order is fixed and is not yours: general, destinations, creatives,
    audiences, variables, strata, data_sources, inference_data, recruitment.
    The server checks nothing across sections, so the order buys the server
    nothing; it means a push that stops half way leaves a PREFIX of the
    reference graph stored rather than a middle of it -- a stratum is never
    stored naming a creative that was not written. `recruitment` is last
    because its start/end window is the study's on/off switch: writing it last
    means the two-hourly ad cron cannot pick up a half-configured study.

    There is no transaction. If a write fails part way, `written` lists the
    sections that ARE now on the server and cannot be withdrawn, and `failed`
    names the one that did not. Fix the cause and call again: the next push
    writes only what is still outstanding.

    Do not retry a push that timed out without diffing first. The POST may well
    have landed.
    """
    result: Dict[str, Any] = {
        "written": [],
        "unchanged": [],
        "outstanding": [],
        "refused": False,
        "failed": None,
        "error": None,
    }

    try:
        # The real `vlab push`, on a worker thread. See `_CallableFromThread`:
        # this tool deliberately owns none of the ordering, the refusal or the
        # partial-failure reporting.
        pushed = await anyio.to_thread.run_sync(
            functools.partial(
                push_sections,
                _CallableFromThread(backend()),
                org,
                slug,
                sections,
                force=force,
            )
        )
    except PushRefused as e:
        # Not raised as a tool error: "nothing was written" is the single most
        # important fact here and it belongs in the payload beside the findings
        # that caused it, not in a message an agent has to parse.
        result["refused"] = True
        result["validation"] = {
            **e.report.model_dump(),
            "known_gaps": list(KNOWN_GAPS),
        }
        return result
    except PushFailed as e:
        # Likewise, and more so: `written` cannot be undone, so losing it in an
        # exception message would leave the caller unable to tell what state the
        # study is in.
        result["written"] = e.written
        result["failed"] = e.failed
        result["error"] = str(e.error)
        return result

    result["written"] = pushed.written
    result["unchanged"] = pushed.unchanged
    result["outstanding"] = pushed.outstanding
    result["validation"] = {
        **pushed.report.model_dump(),
        "known_gaps": list(KNOWN_GAPS),
    }
    return result


# --------------------------------------------------------------------------
# Tools: the pure authoring helpers
# --------------------------------------------------------------------------


async def compile_strata(
    variables: List[Any],
    finish_question_ref: Optional[str] = None,
    existing_strata: Optional[List[Any]] = None,
    creatives: Optional[List[Any]] = None,
    audiences: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Compile a `variables` section into a `strata` section. Pure: no scope needed.

    Computes and returns; reads nothing, writes nothing, and never touches the
    network. The result is not stored anywhere -- pass it to `push_study` as
    the `strata` section if you want it kept.

    This is exactly the dashboard's "Regenerate", ported and held identical to
    the TypeScript by a replayed fixture set: the full factorial of the
    variables, with each stratum's quota the PRODUCT of its levels' quotas.

    WHAT REGENERATING DOES TO EXISTING STRATA, which is the thing to understand
    before calling it on a live study. Pass `existing_strata` and a stratum with
    a matching id keeps its hand-edited `creatives`, `audiences` and
    `excluded_audiences`; its `facebook_targeting`, `question_targeting`,
    `metadata` and `quota` are RECOMPUTED and your edits to those are lost.
    Quota in particular is recomputed on purpose -- preserving it would mean a
    changed level quota could never reach an existing study.

    A stratum the new variables no longer produce simply is not in the result.
    A stratum id IS a Meta ad set name, so pushing that deletes the ad set, with
    its delivery learning and its history. Diff before you push.

    `creatives` and `audiences` are the study's sections, and they are how NEW
    strata get populated: omit them and every newly produced stratum names no
    creative at all, which validates as a broken study.

    `finish_question_ref` is the question ref that marks a respondent finished.
    Omit it and it is read off the first existing stratum. With neither, there
    is nothing to compile and the result is empty -- there is no stratum to
    write without a question that says a respondent finished.
    """
    ref = finish_question_ref
    if not ref and existing_strata:
        ref = get_finish_question_ref(existing_strata)

    fresh = create_strata_from_variables(
        variables, ref, creatives or [], audiences or [], existing_strata or []
    )

    existing_ids = {s.get("id") for s in (existing_strata or []) if isinstance(s, dict)}
    fresh_ids = {s["id"] for s in fresh}
    return {
        "strata": fresh,
        "finish_question_ref": ref,
        "merged_with_existing": sorted(str(i) for i in existing_ids & fresh_ids),
        "no_longer_produced": sorted(
            str(i) for i in existing_ids - fresh_ids if i is not None
        ),
    }


async def extract_targeting(
    adset: Dict[str, Any], properties: List[str]
) -> Dict[str, Any]:
    """Pull targeting properties off a template ad set. Pure: no scope needed.

    Computes and returns; reads nothing, writes nothing, no network. Feed it one
    ad set object from `meta_adsets` and the property keys you want, and put the
    result in a stratum's `facebook_targeting`.

    A requested property that is not on the ad set is an ERROR, not a default.
    Silently omitting `geo_locations` would produce a stratum targeting a whole
    country and spending its budget there.

    `targeting_automation: {advantage_audience: 0}` is always forced onto the
    result, overwriting whatever the source ad set had. Advantage+ audience
    expansion leaks delivery outside a geographic stratum, which makes that
    stratum's estimate wrong, so vlab never uses it.
    """
    return {"targeting": extract_from_adset(adset, list(properties))}


# --------------------------------------------------------------------------
# Tools: plan / apply
# --------------------------------------------------------------------------


async def plan_study(org: str, slug: str) -> Dict[str, Any]:
    """The reconciliation plan, indexed for `apply_instruction`. Needs `optimize:read`.

    NOT SIDE-EFFECT FREE, despite being called a preview. Every run READS META
    with the researcher's stored credential, HEALS AD ATTRIBUTIONS (inserting
    `ad_attributions` rows for live ads that have none), and writes an
    `adopt_reports` row plus a respondents-over-time and a cost-over-time
    report. It creates no Meta objects and spends no money. On a large study it
    is slow -- the server allows it five minutes. Do not poll it.

    It is nonetheless the only thing that checks the Meta-side half of a study:
    `validate_study` is pure and cannot see whether the template campaign still
    exists or whether Meta will accept the objective. A failure here carries the
    real message in the error.

    Reconciliation is LAYERED, so a short plan is often correct: on a fresh
    study a working configuration returns exactly one campaign/create and
    nothing else. Ad sets are planned once the campaign exists on Meta; ads once
    the ad set does. An EMPTY plan means the study reconciles as it stands --
    or that its recruitment window is closed, since the crons only touch a study
    where start_date < now < end_date.

    Applying nothing is a legitimate choice: the adopt-ads cron runs this whole
    loop every two hours at :30 for every study inside its window.
    """
    instructions = await backend().plan(org, slug)
    return {"instructions": instructions, "count": len(instructions)}


async def apply_instruction(org: str, slug: str, index: int) -> Dict[str, Any]:
    """Apply ONE instruction of the current plan to Meta. Needs `optimize:write`.

    THIS SPENDS MONEY. It is the only tool that creates, updates or deletes
    objects on Meta -- campaigns, ad sets, ads, custom audiences -- with real
    budget attached. That is precisely why `optimize` is a separate scope
    resource from `studies`: a key that can edit a study's configuration should
    not, by that fact alone, be able to launch ads.

    The plan is RECOMPUTED here rather than read from a cache, so `index` is an
    index into a fresh list -- which also means this run has all of
    `plan_study`'s side effects (Meta reads, attribution healing, report rows)
    before it applies anything. An instruction list goes stale the moment
    anything is applied, and posting a stale one means posting an `adset_id`
    that no longer means what it did.

    RE-PLAN AFTER EVERY APPLY. Reconciliation is layered: an ad set's ads are
    not planned until the ad set exists on Meta, so a loop that applied the
    whole list in one pass would be applying a list computed before any of it
    was true. There is deliberately no tool that applies more than one.
    """
    instructions = await backend().plan(org, slug)
    if not 0 <= index < len(instructions):
        raise IndexError(
            f"Index {index} is not in the current plan, which has "
            f"{len(instructions)} instruction(s). Call plan_study again -- the "
            "list changes as instructions are applied."
        )

    instruction = instructions[index]
    result = await backend().apply(org, slug, instruction)
    return {"applied": instruction, "result": result}


# --------------------------------------------------------------------------
# Tools: the read-only Meta proxy
# --------------------------------------------------------------------------

_META_NOTE = """
    The server reads Meta with the Facebook credential it already stores for
    this user; no Facebook token ever reaches the caller, and there is no write
    proxy -- everything here is read-only.

    A user can hold more than one Facebook credential, and different tokens see
    different ad accounts. With more than one and no `credentials_key`, the
    server answers 409 naming them rather than picking: a wrong pick surfaces
    hours later as an unexplained Meta rejection at ad-set create time.
    `meta_credentials` lists the names.

    NO CACHING. Every call is a live Graph read against Meta's per-app rate
    limits, shared with everything else this account does. Do not poll these in
    a loop. Results are paged; `paging.truncated` means the server stopped at
    its ten-page cap and `paging.after` is where to resume.
"""


async def meta_credentials(org: str) -> Dict[str, Any]:
    """List the caller's stored Facebook credentials by name. Needs `meta:read`.

    Reads Meta configuration held by vlab; writes nothing.

    Exists because `credentials_key` is otherwise undiscoverable, and it is
    needed both to disambiguate every other meta_* tool and to fill in
    `general.credentials_key`. Never returns tokens.
    """
    return {"credentials": await backend().meta_credentials(org)}


async def meta_adaccounts(
    org: str,
    credentials_key: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """List the ad accounts the stored Facebook credential can see. Needs `meta:read`.

    Reads Meta; writes nothing.

    `account_id` is the bare number that goes in `general.ad_account`; `id` is
    the same thing prefixed `act_`. Both come back.
    """
    return await backend().meta_adaccounts(org, credentials_key, limit, after)


async def meta_campaigns(
    org: str,
    account: str,
    credentials_key: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """List an ad account's campaigns on Meta. Needs `meta:read`.

    Reads Meta; writes nothing. `account` takes `act_123` or `123`.

    Use it to find the TEMPLATE campaign a study copies its targeting and
    creative shape from -- vlab does not build a campaign from nothing.
    """
    return await backend().meta_campaigns(org, account, credentials_key, limit, after)


async def meta_adsets(
    org: str,
    campaign: str,
    credentials_key: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """List a campaign's ad sets on Meta, with their targeting. Needs `meta:read`.

    Reads Meta; writes nothing.

    Each ad set here goes straight into `extract_targeting` unchanged -- that is
    what `targeting` is in the field list for.
    """
    return await backend().meta_adsets(org, campaign, credentials_key, limit, after)


async def meta_ads(
    org: str,
    campaign: Optional[str] = None,
    adset: Optional[str] = None,
    credentials_key: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """List ads on Meta, with their creatives. Needs `meta:read`.

    Reads Meta; writes nothing. Pass EXACTLY ONE of `campaign` or `adset` --
    defaulting would mean guessing which id an ambiguous caller meant.

    Each ad carries its creative nested under `creative`. Store that blob
    VERBATIM as a `creatives[].template`: it is what the dashboard's Creatives
    form stores, and vlab rewrites only the pieces it must.
    """
    return await backend().meta_ads(org, campaign, adset, credentials_key, limit, after)


# The Meta caveats belong on every meta_* tool -- an agent reads one
# description, not the module -- and repeating them by hand in six docstrings is
# six chances to let them drift.
for _fn in (meta_credentials, meta_adaccounts, meta_campaigns, meta_adsets, meta_ads):
    _fn.__doc__ = (_fn.__doc__ or "").rstrip() + "\n" + _META_NOTE


# --------------------------------------------------------------------------
# Tools: keys
# --------------------------------------------------------------------------


async def list_api_keys() -> Dict[str, Any]:
    """List the caller's live API keys. Needs `auth:read`.

    Reads only; writes nothing. Never returns a token -- vlab does not store
    them, only their ids.

    Keys minted before the 2026-09-04 hardening are NOT listed and cannot be:
    nothing was ever persisted for them. They are also permanent and
    unrestricted. If you hold one from before that date, ask for a reissued
    key; nothing you can do makes the old one expire.
    """
    return await backend().list_api_keys()


async def revoke_api_key(key_id: str) -> Dict[str, Any]:
    """Revoke one API key by its id. Needs `auth:write`.

    WRITES, IRREVERSIBLY: deleting the credentials row IS the revocation, and
    there is no un-revoke. The id is the `jti` from the mint response, which
    `list_api_keys` returns as `id`.

    A 404 means it is not one of YOUR live keys -- never a 403, so this cannot
    be used to find out whether someone else's key exists.

    The replica that serves this drops the key at once; other replicas honour it
    for up to 30 seconds, because row lookups are cached in process. Treat
    revocation as "dead within a minute", not "dead now".
    """
    await backend().revoke_api_key(key_id)
    return {"revoked": key_id, "other_replicas_honour_until_seconds": 30}


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------

# Ordered as a study is authored, because a client lists them in this order and
# that ordering is itself a hint about the runbook.
TOOLS: Sequence[Callable[..., Any]] = (
    list_orgs,
    list_studies,
    create_study,
    pull_study,
    validate_study,
    diff_study,
    push_study,
    compile_strata,
    extract_targeting,
    plan_study,
    apply_instruction,
    meta_credentials,
    meta_adaccounts,
    meta_campaigns,
    meta_adsets,
    meta_ads,
    list_api_keys,
    revoke_api_key,
)


def _guarded(fn: Callable[..., Any]) -> Callable[..., Any]:
    """`fn` with the environment's authorizer run first.

    A wrapper rather than a line at the top of every tool: a tool added later
    cannot forget it, which is the same reason scope enforcement on the routes
    is a middleware rather than a per-route dependency. `functools.wraps` sets
    `__wrapped__`, so FastMCP's `inspect.signature` still sees the real
    parameters and builds the real schema.
    """

    @functools.wraps(fn)
    async def guarded(**kwargs: Any) -> Any:
        current_env().authorize(fn.__name__)
        return await fn(**kwargs)

    return guarded


def register_tools(server: Any) -> Any:
    """Register every tool on a FastMCP server. The only registration path.

    Both transports call this and neither adds, removes or renames anything
    afterwards, which is what makes the tool list and the descriptions
    identical over stdio and over `/mcp` by construction rather than by
    discipline. `test_mcp_server` diffs the two anyway.
    """
    for fn in TOOLS:
        server.add_tool(
            _guarded(fn),
            name=fn.__name__,
            # `inspect.cleandoc`, not the raw `__doc__`: FastMCP passes the
            # description through to the client verbatim, and the raw one
            # carries this file's indentation into an agent's context window.
            description=inspect.cleandoc(fn.__doc__ or ""),
        )
    return server


INSTRUCTIONS = """\
Author, validate and launch a vlab recruitment study.

Start with `list_orgs` and `list_studies`: everything else takes an
organisation UUID and a study slug, and neither is guessable.

A study is nine configuration sections. Read them with `pull_study`, change
them, check with `validate_study`, see what would change with `diff_study`,
write with `push_study`, then reconcile onto Meta with `plan_study` and
`apply_instruction`.

Two things govern everything here. Configuration is APPEND-ONLY: a write
inserts a new row that supersedes the previous one, there is no delete, and a
bad write can only be written over. And the sections reference each other by
NAME: creatives name destinations, strata name creatives and audiences, and a
stratum's id is the name of a Meta ad set -- so renaming one deletes that ad
set on the next reconcile, with its delivery learning.
"""


def build_server(instructions: str = INSTRUCTIONS, **settings: Any) -> Any:
    """A FastMCP server with the tools registered. Imports `mcp` lazily.

    Lazy because `vlab --help` must stay fast: importing `mcp` pulls in
    starlette, uvicorn and pydantic-settings, and the CLI is the one caller
    that pays for an import it does not use. `test_cli` pins the startup cost.
    """
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415 -- see docstring

    return register_tools(
        FastMCP(name=SERVER_NAME, instructions=instructions, **settings)
    )


def serve_stdio(client: Any) -> None:
    """Run the tool server on stdio against `client`. What `vlab mcp` calls.

    The environment is bound for the whole run rather than per call: on stdio
    there is one caller, one key and one backend for the life of the process,
    and the service checks that key's scopes on every underlying HTTP call.
    """
    server = build_server()
    with use(ToolEnv(ClientBackend(client))):
        server.run(transport="stdio")
