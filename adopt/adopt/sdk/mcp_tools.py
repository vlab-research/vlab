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

`VlabClient`'s method surface AS THE TOOLS USE IT, returning exactly what it
returns: `list_orgs`, `list_studies`, `create_study`, `get_confs`, `post_conf`,
`copy_from`, `validate`, `plan`, `apply`, `study_errors`, `current_data`,
`ad_attributions`, `recruitment_stats`, `respondents_over_time`,
`cost_over_time`, `strata_progress`, `meta_*`, `list_api_keys`,
`revoke_api_key`. A client method
no tool calls -- `ad_attributions_csv`, which exists for `vlab
ad-attributions --csv` -- is deliberately NOT part of the contract and has no
in-process twin: an unreachable method on one backend only is the first thing
to rot. `ClientBackend` below is the HTTP
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
    "copy_study_from": "studies:write",
    "plan_study": "optimize:read",
    "apply_instruction": "optimize:write",
    "study_errors": "optimize:read",
    "current_data": "optimize:read",
    "ad_attributions": "responses:read",
    "recruitment_stats": "stats:read",
    "respondents_over_time": "stats:read",
    "cost_over_time": "stats:read",
    "strata_progress": "stats:read",
    "meta_credentials": "meta:read",
    "meta_adaccounts": "meta:read",
    "meta_campaigns": "meta:read",
    "meta_adsets": "meta:read",
    "meta_ads": "meta:read",
    "list_api_keys": "auth:read",
    "revoke_api_key": "auth:write",
    # Connected accounts and key minting (Phase C of
    # `planning/mcp-full-coverage.md`). All four are `auth`, which is the
    # resource that is never implicitly granted: a key that can author studies
    # must not thereby be able to read, replace or delete the researcher's
    # third-party credentials, nor mint itself a wider key.
    "list_accounts": "auth:read",
    "create_account": "auth:write",
    "delete_account": "auth:write",
    "create_api_key": "auth:write",
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

    WHAT AN ORG IS TODAY: a personal workspace, not a team. Every vlab user
    has exactly ONE, created automatically the first time they log in to the
    dashboard, and its `name` is that user's Auth0 id (`auth0|...`), not a
    label anyone chose. There is no membership: nobody can be added to another
    user's org, and no route creates an org. So expect a single entry, take
    its `id`, and do not describe the org to a researcher as a team or ask
    which org they meant. Multi-user orgs are scaffolding for later; when they
    arrive the shape here stays the same and only the count changes.

    Returns `{"orgs": [{"id", "name"}]}`. `id` is what every other tool wants.
    Identify an org by its id, never by its name: the schema leaves `name`
    nullable, so treat it as optional, and in practice it is the Auth0 id.

    An empty list should not happen. Minting an API key requires having logged
    in to the dashboard, and that first login is what creates the org. If you
    see one, the server side is wrong in a way no tool here can fix -- there
    is no route that creates an org or grants membership.

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

    Returns `{"studies": [{"id", "name", "slug", "created"}], "page_size": n}`.
    `page_size` is the length of THIS page, not the org's total: at the
    default `limit` of 100 a page_size of 100 means there may be more, and the
    next page is `offset=100`. There is no total count.
    `created` is ISO 8601 with an explicit UTC offset -- note that
    `create_study` reports the same field as `createdAt` in milliseconds, for
    compatibility with the dashboard, and the two are not the same shape.

    You see every study in the org. Today an org is one user's personal
    workspace (see `list_orgs`), so this is every study the key's user has
    ever created, in the dashboard or through this API. A 404 means the org is
    not yours or does not exist; the two are deliberately indistinguishable,
    and a malformed UUID gets the same answer again.

    `limit` is 1..500 and defaults to 100; `offset` skips rows. An org with
    more studies than the limit is silently truncated, so page rather than
    assuming one call is the whole list.

    An empty list means the org has no studies YET -- it is not evidence that a
    slug you already hold is wrong. Nothing here validates a slug: `pull_study`
    returns `{}` for a study that does not exist just as it does for one never
    configured, and only a write ever 404s on a bad slug.
    """
    studies = await backend().list_studies(org, limit, offset)
    return {"studies": studies, "page_size": len(studies)}


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

    `org` is an organisation UUID; `list_orgs` is what hands you one, and
    today it hands you exactly one, the user's personal workspace. A 404
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


async def copy_study_from(org: str, slug: str, source_slug: str) -> Dict[str, Any]:
    """Copy another study's configuration into this one. Needs `studies:write`.

    WRITES, IRREVERSIBLY, and this is the dashboard's "initialize from an
    existing study". It appends the SOURCE's newest row per conf type to the
    TARGET, so the copy supersedes whatever the target held. Nothing is
    deleted, nothing is merged, and there is no undo: `study_confs` is
    append-only, so an unwanted copy can only be written over section by
    section with `push_study`.

    `slug` is the study being written to and `source_slug` is the one being
    read. Getting them the wrong way round overwrites the study you meant to
    copy FROM, and there is nothing here that can tell the difference.

    `general` is deliberately NOT copied: it names the Meta ad account and the
    stored Facebook credential, which are the two things that should not follow
    a study around. Everything else is -- destinations, creatives, audiences,
    variables, strata, data_sources, inference_data, recruitment -- INCLUDING
    `recruitment`, whose start/end window is the study's on/off switch, so a
    copy can switch a study on. Read the result and check it.

    Returns the sections that were copied, keyed as stored. Both slugs are
    resolved against your own studies in this org, so a source you do not own
    is a 404 rather than a copy; 404 also when the source has no configuration
    to copy at all.

    Follow it with `pull_study` to see what the target now holds, and
    `validate_study` before `plan_study`: a copied `strata` section names
    creatives and audiences by name, and those came from the source.
    """
    return await backend().copy_from(org, slug, source_slug)


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
# Tools: what a running study is doing
# --------------------------------------------------------------------------
#
# These are the dashboard's study page, tool for tool: the Errors tab, Current
# Data, Ad Attributions, Recruitment Statistics, the participants chart and the
# spend charts. Every one is a READ of something a CRON already wrote -- there
# is no live Meta call anywhere in this group -- and none computes anything the
# route does not.
#
# What refreshes what, because the descriptions below all have to repeat it:
# `plan_study` (and the adopt-ads cron, two-hourly) writes the FACEBOOK_ADOPT
# report and the two time series; the adopt-recruitment-data cron, FOUR-hourly,
# writes the spend rows `recruitment_stats` sums; swoosh, half-hourly, writes
# the events `study_errors` derives from. Nothing here refreshes anything.


async def study_errors(org: str, slug: str) -> Dict[str, Any]:
    """The study's currently open errors and warnings. Needs `optimize:read`.

    Reads only; writes nothing. This is the dashboard's Errors tab and the
    badge beside it.

    Returns `{"errors": [{source, fingerprint, severity, message, details,
    first_seen, last_seen}], "count": n}`, errors before warnings and newest
    first. Derived from the `study_run_events` log rather than stored as a
    status: the LATEST event per (source, fingerprint), kept only when it is an
    error or a warning AND was seen in the last 90 MINUTES.

    THAT WINDOW IS WHY AN EMPTY LIST IS NOT "HEALTHY". It is a dead-man's
    switch -- a problem that stops being re-emitted ages out by itself, with
    nobody having closed it -- so `[]` means "nothing is currently
    re-emitting", which also describes a study whose cron stopped running at
    all. 90 minutes is three times the 30-minute swoosh cron.

    AND ONLY ONE WRITER EXISTS. Today only swoosh (survey-data extraction)
    writes these events. adopt, which builds the ads, writes NONE, so an
    ad-building failure never appears here whatever went wrong. To see that,
    run `plan_study` and read its error. `documentation/agent-api.md` §2.3.

    Errors are served even when a study has no data at all -- a hard extraction
    failure means no rows exist, which is exactly when this matters.
    """
    errors = await backend().study_errors(org, slug)
    return {"errors": errors, "count": len(errors)}


async def current_data(org: str, slug: str) -> Dict[str, Any]:
    """The respondent data the optimizer works from. Needs `optimize:read`.

    Reads only; writes nothing. This is the dashboard's Current Data tab, and
    it is the answer to "why did the optimizer decide that": these rows, and
    nothing else, are what the quota and budget arithmetic sees.

    Returns `{"rows": [{user_id, variable, value, timestamp}], "count": n}` --
    ONE ROW PER RESPONDENT PER VARIABLE, not one per respondent, so a survey
    with twenty questions produces twenty rows for each person who finished it.

    Scoped to the study's INFERENCE WINDOW, which is
    `recruitment.start_date`..`recruitment.end_date` for a `simple` or
    `destination` study and, for a `pipeline_experiment`, the CURRENT WAVE
    only -- so on a wave study this is a slice, not the study's history, and it
    changes underneath you as waves turn over. A respondent outside the window
    is simply absent, and that is a configuration fact rather than missing data.
    (`general.opt_window` is a different thing entirely: it is the
    recruitment-data lookback the budget arithmetic uses, and it has no effect
    here.)

    CAN BE LARGE and can be slow: the server allows this call five minutes.
    Ask for it once and work from the answer; there is no paging and no filter.

    An empty list means no respondent has answered inside the window -- which
    is either a young study or a broken data pipeline, and `study_errors` is
    what tells the two apart.
    """
    rows = await backend().current_data(org, slug)
    return {"rows": rows, "count": len(rows)}


async def ad_attributions(org: str, slug: str) -> Dict[str, Any]:
    """The frozen ad -> stratum mapping, as a table. Needs `responses:read`.

    Reads only; writes nothing. This is the dashboard's Ad Attributions tab,
    and it is what a survey export is joined against: left-join your export on
    `ad_id` and every stratum and metadata column comes back, named as it was
    when the ad was created.

    Returns `{"columns": [...], "rows": [{column: value}], "count": n}`.
    `columns` is a union across the rows in first-seen order, because the
    metadata blob is flattened into columns under its own key names and
    different ads can carry different keys.

    FROZEN AND APPEND-ONLY. A row is written once, when the ad is created, and
    is never updated: it records what the stratum meant AT THAT MOMENT, so
    editing a stratum later does not rewrite history. Ads Meta no longer has
    are still listed, deliberately -- respondents keep arriving from deleted
    ads through reshared page posts, and a missing row would be
    indistinguishable from an unattributed respondent.

    Rows appear as ads are created, and `plan_study` also HEALS this table
    (inserting rows for live ads that have none), so a gap here can sometimes
    be closed by running a plan. This tool itself changes nothing.
    """
    table = await backend().ad_attributions(org, slug)
    rows = (table or {}).get("rows") or []
    return {**(table or {}), "count": len(rows)}


async def recruitment_stats(org: str, slug: str) -> Dict[str, Any]:
    """Spend, reach and cost per respondent, per stratum. Needs `stats:read`.

    Reads only; writes nothing. This is the dashboard's Recruitment Statistics
    table, and it is the money question: what has each stratum cost, and what
    is a respondent costing there.

    Returns `{"strata": {stratum_id: {spend, cpm, reach, frequency,
    impressions, unique_clicks, unique_ctr, respondents,
    price_per_respondent, incentive_cost, total_cost, conversion_rate}}}`.

    NOTHING HERE IS LIVE, AND THE TWO HALVES ARE STALE BY DIFFERENT AMOUNTS.
    `spend`, `reach`, `unique_clicks` and `impressions` are SUMMED OVER ALL TIME
    from `recruitment_data_events`, which the `adopt-recruitment-data` cron
    writes EVERY FOUR HOURS -- no Meta call happens when you call this.
    `respondents` comes from the latest `FACEBOOK_ADOPT` report, which a plan
    run writes. The four derived figures combine the two, with `incentive_cost`
    using `recruitment.incentive_per_respondent`. Calling this tool refreshes
    NEITHER half; `plan_study` refreshes only the respondent half, and nothing
    an API key can call refreshes the spend half.

    `cpm` IS NOT COST PER MILLE. It is computed as impressions / spend --
    impressions per dollar, so a bigger number is cheaper delivery. That is
    what the dashboard shows, and this tool reports the field as the service
    computes it rather than quietly redefining it.

    404 WHEN THE STUDY HAS NEVER HAD A PLAN RUN. There is no report to take
    respondent counts from, so the route refuses rather than reporting zero
    respondents against real spend. `plan_study` writes that report -- and is
    not side-effect free. A 404 also means the study has no strata configured.
    """
    return {"strata": await backend().recruitment_stats(org, slug)}


async def respondents_over_time(org: str, slug: str) -> Dict[str, Any]:
    """The participants-over-time series, per segment. Needs `stats:read`.

    Reads only; writes nothing. This is the dashboard's participants chart and
    its "Current Participants" card.

    Returns `{"points": [{datetime, totalParticipants, segments: [{id,
    participants}]}], "count": n}`, oldest first, in HOURLY buckets, with
    `datetime` in MILLISECONDS since the epoch (not ISO, unlike every other
    timestamp here). Counts are CUMULATIVE, so the difference between two
    points is what arrived between them.

    THE LAST POINT IS NOT NECESSARILY THE STUDY'S TOTAL. It is the total
    WITHIN THE INFERENCE WINDOW (see `current_data` -- one wave only, for a
    `pipeline_experiment`) and only across CURRENTLY-CONFIGURED strata: a
    respondent attributed to a stratum that has since been renamed or removed
    is not counted here at all, though `ad_attributions` still remembers the
    ad. Buckets are anchored to the first and last interaction in the data
    rather than to the configured start and end dates.

    READ FROM A PRE-COMPUTED REPORT, not from the responses. An EMPTY list
    therefore means no report has been written yet, NOT that nobody has
    answered -- and the thing that writes one is a plan run. `plan_study`
    refreshes it, and `plan_study` reads Meta and writes rows, so refreshing
    this is not free. The adopt-ads cron does the same every two hours for a
    study inside its recruitment window, which is why this is usually current
    without anyone asking.

    `segments` are stratum ids, which are also Meta ad set names. This is the
    conf service's `segments-progress`; the Go service serves a route of the
    same name with a different payload, and the two are not interchangeable.
    """
    points = await backend().respondents_over_time(org, slug)
    return {"points": points, "count": len(points)}


async def cost_over_time(org: str, slug: str) -> Dict[str, Any]:
    """The spend and marginal-cost series. Needs `stats:read`.

    Reads only; writes nothing. This is the dashboard's Total Spent card, its
    Avg Cost per Participant card and the two spend charts.

    Returns `{"points": [{datetime, cumulativeSpend, cumulativeRespondents,
    marginalCost, newRespondents, dailySpend}], "count": n}`, oldest first,
    `datetime` in MILLISECONDS, one point per DAY.

    SPEND MEANS TWO DIFFERENT THINGS IN THE SAME ROW, and the difference is
    `recruitment.incentive_per_respondent`. `cumulativeSpend` is ad spend PLUS
    INCENTIVES (`newRespondents * incentive_per_respondent`, accumulated);
    `dailySpend` is that day's AD SPEND ALONE, with no incentive in it; and
    `marginalCost` is `(dailySpend + that day's incentives) / newRespondents`,
    null on a day that gained none -- which is the number that says whether
    recruitment is getting harder. So `cumulativeSpend` is not the running sum
    of `dailySpend` unless the study pays no incentive.

    THE POINTS ARE NOT CONSECUTIVE DAYS. A day on which neither spend nor
    respondents changed is omitted, because it is a flat segment on a
    cumulative chart; the first and last active days are always present.
    Leading and trailing days with no activity at all are trimmed, so the
    series starts when the study really started rather than at
    `recruitment.start_date`.

    READ FROM A PRE-COMPUTED REPORT, exactly as `respondents_over_time` is: an
    EMPTY list means no plan run has written one yet, not that nothing has been
    spent. `plan_study` is what refreshes it and it is not side-effect free;
    the adopt-ads cron refreshes it every two hours for a study inside its
    recruitment window.

    For per-stratum money rather than a series over time, use
    `recruitment_stats`.
    """
    points = await backend().cost_over_time(org, slug)
    return {"points": points, "count": len(points)}


# --------------------------------------------------------------------------
# Tools: the optimizer's reports
# --------------------------------------------------------------------------


async def strata_progress(org: str, slug: str, history: int = 1) -> Dict[str, Any]:
    """The optimizer's per-stratum allocation and prices. Needs `stats:read`.

    Reads only; writes nothing. This is the answer to "where is the money
    going, and what is a respondent costing me" -- the dashboard's
    "Participants per Segment" table, one row per stratum:

    * `current_budget` -- the optimizer's allocation for that stratum over the
      rest of the recruitment period. NOT a daily budget: the ad set's daily
      budget is this divided by the days left, floored to the cent and zeroed if
      below the study's `min_budget`, so a non-zero allocation here can still
      mean a paused ad set.
    * `current_price_per_participant` -- an ESTIMATE of what one more respondent
      in that stratum costs, not a measurement: a Gamma-Poisson posterior over
      the study's `opt_window` shrunk toward a prior of 2 +
      `incentive_per_respondent` dollars, so a stratum with little data sits
      near that prior rather than near its own history. It is nonetheless the
      reason budget moves between strata -- the optimizer buys where it is
      cheap until the quota shape says stop.
    * `current_participants`, and the `desired`/`current`/`expected` percentage
      triple -- where the sample is, where it should be, and where this
      allocation expects it to land. THE THREE `*_percentage` FACTS AND
      `percentage_deviation_from_goal` ARE FRACTIONS BETWEEN 0 AND 1, not 0-100,
      despite the names: they are shares of the sample. Deviation is
      `abs(desired - current)`, unrounded.
    * `total_spent` and `lifetime_spent` -- the optimization window and all
      time; `efficiency_weight` -- how hard this study trades cost against
      matching the quota exactly. The two `counterfactual_*` facts appear only
      when a constraint binds, and are null otherwise.

    WHERE THE NUMBERS COME FROM, which decides how you read them. Every value
    is read out of the report `plan_study` writes at the end of a plan run, and
    NOTHING ELSE WRITES IT. So these are the numbers as of that run, not live
    Meta, and calling `plan_study` is the only way to refresh them -- which is
    not free: it reads Meta and heals ad attributions. The adopt-ads cron plans
    every study inside its recruitment window every two hours, so on a running
    study this is at most two hours stale on its own.

    TWO DIFFERENT 404s, and the message tells them apart. "No adopt report found
    for study <slug>" means NO PLAN HAS EVER RUN for it -- on a study that is
    configured but never planned that is the expected answer, and `plan_study`
    is what changes it. "Study not found: <slug>" is the other case: wrong slug,
    or an org that is not yours (`list_studies` is what settles both).

    `history` is 1..200 (default 1) and returns that many reports NEWEST FIRST,
    which is how you see budget MOVE between runs rather than a snapshot.
    """
    reports = await backend().strata_progress(org, slug, history)
    return {"reports": reports, "count": len(reports)}


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


async def create_api_key(
    name: str,
    scopes: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Mint a new vlab API key. Needs `auth:write`.

    WRITES: a new key exists afterwards and can be used immediately. Revoke it
    with `revoke_api_key`; there is no edit.

    THE TOKEN IS SHOWN ONCE AND NEVER AGAIN. It comes back as `token` in this
    response and is not stored anywhere -- the service keeps only its id (the
    `jti`), which is the whole reason a key is revocable at all. `list_api_keys`
    shows names, ids, scopes and expiry, never tokens. If you lose it, revoke
    the key and mint another. Hand it to the human who asked for it and do not
    write it into a file, a config, or a study.

    ATTENUATING, and this is the point of the whole scheme: a key can only mint
    a key no more powerful than itself. Two refusals follow from that, both
    403s:

    * you need `auth:write` to be here at all -- `auth` is never implicitly
      granted, so a `studies:write` key cannot mint anything;
    * OMITTING `scopes` IS A REQUEST FOR FULL ACCESS, not for none. A scoped
      key asking for an unscoped one is refused. Pass the narrowest `scopes`
      the new key actually needs.

    Scopes are `resource:action` over resources studies, responses, stats,
    optimize, meta, auth and actions read, write, `*`; `write` implies `read`
    on the same resource. A sensible authoring key is
    `["studies:write", "meta:read", "optimize:read"]` -- it can build, check
    and plan a study and cannot spend money. Add `optimize:write` only when you
    mean to let it launch ads. An unknown scope is a 400 rather than a silently
    dead key.

    `expires_in_days` is bounded by the server and defaults to its own TTL.
    There is no key that never expires; keys minted before 2026-09-04 are the
    exception and cannot be listed or expired at all.

    Returns `{name, id, token, scopes, expires_at}`. `id` is what
    `revoke_api_key` takes.
    """
    return await backend().create_api_key(name, scopes, expires_in_days)


# --------------------------------------------------------------------------
# Tools: connected accounts
# --------------------------------------------------------------------------

_ACCOUNT_NOTE = """
    WHAT AN ACCOUNT IS. A named credential for a third party, owned by the
    caller's user. The NAME is the whole point: a `data-sources[]` entry names
    one in `credentials_key`, and a Facebook credential is named the same way in
    `general.credentials_key`. A study cannot extract responses, or reconcile
    ads onto Meta, until a credential of the right name and type exists -- so
    "which credentials_key do I use" is answered by `list_accounts`, and
    nothing else answers it for a non-Facebook provider.

    An account is addressed by `(auth_type, name)` and nothing else. Types:
    `typeform`, `fly`, `qualtrics`, `alchemer`, plus `facebook` (and its
    historical twin `facebook_ad_user`) and `api_key`, which exist and are
    listed but cannot be created here.

    SECRETS ARE NEVER RETURNED, by any tool here, on any type. There is no way
    to read a stored credential back; a lost token is re-connected, not
    recovered.
"""


async def list_accounts(auth_type: Optional[str] = None) -> Dict[str, Any]:
    """List the caller's connected accounts, without their secrets. Needs `auth:read`.

    Reads only; writes nothing.

    Returns `{"accounts": [{name, auth_type, created}]}`, sorted by type then
    name. `api_key` rows also carry `id`, the minted key's id. No other field is
    ever returned, because every other field of every credential shape IS the
    secret.

    `auth_type` filters. An unknown one is an empty list, not an error.

    This is `meta_credentials` widened to every provider. `meta_credentials`
    stays: it is org-addressed, it belongs to the Meta proxy that needs it to
    disambiguate a token, and it is reachable with `meta:read` where this needs
    `auth:read` -- an agent that reads a researcher's Meta estate has no
    business enumerating their Typeform and Alchemer credentials too.

    Vlab API KEYS ARE NOT LISTED HERE even though they live in the same table:
    `list_api_keys` is that question, with ids, scopes and expiry. The one
    exception is an `api_key` account row, which is the dashboard's separate
    bookkeeping record of a key it minted, and deleting one does NOT revoke
    anything.
    """
    return {"accounts": await backend().list_accounts(auth_type)}


async def create_account(
    name: str, auth_type: str, credentials: Dict[str, Any]
) -> Dict[str, Any]:
    """Connect a third-party account, or replace one by name. Needs `auth:write`.

    WRITES a credentials row. UPSERT: posting a `name` that already exists
    under the same `auth_type` REPLACES that credential -- there is no separate
    update, and the old secret is gone. The replace is atomic, so a study
    naming this credential is never left pointing at nothing.

    THE SECRET PASSES THROUGH THIS CONVERSATION. Whatever you put in
    `credentials` is a live third-party token: it is in the agent's context, in
    any transcript or log of this session, and in the request to vlab. Prefer
    having the human paste it into the dashboard's Accounts page, or run
    `vlab accounts add --credentials-json` themselves, which reads it from a
    file and never puts it on a command line. Use this tool when the human has
    knowingly handed you the secret for exactly this purpose, and do not echo it
    back afterwards.

    `credentials` must match the provider's shape EXACTLY -- an unknown or
    misspelled key is a 422, never a silently dropped field, because a
    credential missing the one key that matters fails much later as an
    unexplained 401 from the third party:

        typeform   {"key": "..."}
        fly        {"api_key": "..."}
        qualtrics  {"api_key": "..."}
        alchemer   {"api_token": "...", "api_token_secret": "..."}

    TWO TYPES ARE REFUSED, both with a 400 that says what to do instead:

    * `facebook` -- the token comes out of Meta's OAuth code exchange, which
      needs a browser and a human. Connect it on the dashboard's Accounts page;
      then `list_accounts` and `meta_credentials` will show its name. This is
      the one gap in the runbook that no key can close.
    * `api_key` -- that is the dashboard's record of a minted vlab key. Use
      `create_api_key`, which returns the token once.

    Returns the same non-secret row `list_accounts` returns; the secret is not
    echoed back.
    """
    return await backend().create_account(name, auth_type, credentials)


async def delete_account(auth_type: str, name: str) -> Dict[str, Any]:
    """Delete one connected account. Needs `auth:write`.

    WRITES, IRREVERSIBLY: the credential is gone and cannot be recovered, only
    re-connected with the secret again. There is no undo and no trash.

    KNOW WHAT IT BREAKS BEFORE YOU CALL IT. Any study whose `data-sources[]`
    entry names this credential in `credentials_key` stops being able to
    extract responses, and any study whose `general.credentials_key` names it
    stops being able to RECONCILE ONTO META -- the next plan or apply fails to
    authenticate, and ad delivery is not repaired until a credential of that
    name exists again. Nothing checks for you: the confs are not consulted, and
    a credential in use deletes exactly as readily as an unused one.

    Deleting a `facebook` account is allowed -- the dashboard allows it too --
    and it is the expensive one, because re-creating it needs the OAuth flow in
    a browser and cannot be done from here at all.

    Deleting an `api_key` account does NOT revoke that API key: the account row
    is bookkeeping, and revocation is `revoke_api_key` on the key's own id.

    404 -- never 403 -- when you have no such account, so this cannot be used to
    find out whether another user has one by that name.
    """
    await backend().delete_account(auth_type, name)
    return {"deleted": {"auth_type": auth_type, "name": name}}


# The account caveats belong on every accounts tool -- an agent reads one
# description, not the module -- and repeating them by hand is three chances to
# let them drift. Same device as `_META_NOTE` above.
for _fn in (list_accounts, create_account, delete_account):
    _fn.__doc__ = (_fn.__doc__ or "").rstrip() + "\n" + _ACCOUNT_NOTE


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
    copy_study_from,
    compile_strata,
    extract_targeting,
    plan_study,
    apply_instruction,
    study_errors,
    current_data,
    ad_attributions,
    recruitment_stats,
    respondents_over_time,
    cost_over_time,
    strata_progress,
    meta_credentials,
    meta_adaccounts,
    meta_campaigns,
    meta_adsets,
    meta_ads,
    list_api_keys,
    revoke_api_key,
    # Credentials and key minting. Last because they are the setup step a
    # researcher does once, not part of the authoring loop above -- except
    # `list_accounts`, which answers "which credentials_key" and is why they
    # sit together rather than beside the meta_* readers.
    create_api_key,
    list_accounts,
    create_account,
    delete_account,
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
`apply_instruction`. `copy_study_from` initialises one study from another.

Once a study is running, `study_errors`, `current_data`, `ad_attributions`,
`recruitment_stats`, `respondents_over_time` and `cost_over_time` are what it
is doing. The last three read reports that only a plan run refreshes, so an
empty answer usually means "no plan has run yet" rather than "nothing has
happened".

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
