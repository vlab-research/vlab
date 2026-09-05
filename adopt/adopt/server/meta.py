"""Read-only Meta Graph proxy.

Phase 2 of `planning/agent-study-authoring.md` §8, and the decision recorded in
§7 ("Meta access: **Server proxies Meta**").

WHY THIS EXISTS
---------------

Three pieces of study authoring need to read Meta before they can write vlab
config, and today all three happen in the browser with the researcher's
Facebook token (`facebookRequest`, `dashboard/src/helpers/api.ts:412`):

* the ad-account list, to fill in `general.ad_account`;
* a template campaign's ad sets, whose `targeting` is what
  `adopt.authoring.extract.extract_from_adset` turns into a variable level's
  `facebook_targeting`;
* a template ad's `creative` blob, which is stored verbatim as
  `creatives[].template`.

An agent holding a vlab API key could do none of that without also being handed
the researcher's Facebook token — a credential with a far wider blast radius
than the vlab key, no expiry the agent controls, and no way to revoke it
without disconnecting the researcher's account. So the server reads Meta
instead, with the token it already stores, and the agent never sees it.

THE CONTRACT IS THE DASHBOARD'S
-------------------------------

Paths, `fields` lists and response shape are lifted from the four
`facebookRequest` callers in `dashboard/src/helpers/api.ts:475-615` so that the
dashboard could later be repointed here without a client change. Where this
diverges it is deliberate and marked; there are exactly three divergences, all
below: `after` instead of `cursor` (the dashboard's cursor param is inert),
ads addressable by ad set as well as campaign, and a standalone creative route.

WHY NOT `facebook/api.py`
-------------------------

`adopt.facebook.api.call` is the service's existing Graph wrapper and is wrong
for a request path in two ways. It retries codes 2/17/368/80004 forever at
five-minute intervals with no attempt cap — correct for a cron that has hours,
fatal for an HTTP handler that has seconds. And it drains cursors eagerly with
no page limit, so one call against a large ad account can pull unbounded data.
This module therefore calls `FacebookAdsApi.call` directly, with a request
timeout, no retries, and an explicit page cap.

It does reuse `facebook.state.get_api`, so the proxy authenticates exactly the
way the optimize path does — same `appsecret_proof`, same per-call session
object, no process-global `FacebookAdsApi.init`.
"""

import asyncio
import logging
import re
import uuid
from typing import Annotated, Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from environs import Env
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError
from fastapi import APIRouter, Depends, HTTPException, Query

from ..facebook.state import get_api
from .api_keys import require_scope
from .db import get_facebook_token, list_facebook_credentials, user_in_org
from .deps import User, async_timeout, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

env = Env()


# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------

# A researcher waiting on the dashboard gets 10s (`facebookRequest`'s
# AbortController). An agent can afford more, and a page cap means we may make
# several round trips inside one request, so this is the budget for ONE Graph
# call, not for the handler.
GRAPH_TIMEOUT_SECONDS = 20

# The pagination decision, stated once (docs: documentation/agent-api.md).
#
# Cursors are followed SERVER-SIDE up to this many pages, and the endpoint is
# LOUD when it stops: the response carries `paging.truncated: true` and the
# cursor to resume from. The alternative — a pure passthrough that always makes
# the caller page — was rejected because the overwhelmingly common case is a
# researcher with a handful of ad accounts and one template campaign, and an
# agent that silently reads only the first page of ad sets will build a study
# missing strata and never notice.
#
# Following forever was rejected too: an ad account with thousands of ads,
# each carrying a full creative blob, is tens of megabytes assembled in memory
# behind a synchronous handler.
MAX_PAGES = 10
DEFAULT_LIMIT = 100
MAX_LIMIT = 500

# The whole-handler budget, derived from the two limits above rather than
# picked: MAX_PAGES Graph calls that each take the full GRAPH_TIMEOUT_SECONDS,
# plus slack for the two database reads. It is a backstop against a socket that
# neither returns nor times out, not a scheduling policy — the page cap is the
# real bound on how much work one request can do.
#
# Deliberately generous rather than tight. A 504 here loses the resume cursor
# (the caller gets an error body, not a `paging.after`), so a request that is
# slow but genuinely making progress must be allowed to finish. The optimize
# routes use the same decorator with 300s.
HANDLER_TIMEOUT_SECONDS = MAX_PAGES * GRAPH_TIMEOUT_SECONDS + 20


# --------------------------------------------------------------------------
# Field lists — the dashboard's, verbatim
# --------------------------------------------------------------------------

# `dashboard/src/helpers/api.ts:487` — 'name, id, account_id'. The spaces are
# dropped here (Graph tolerates them, but they are an accident of the JS
# literal, not part of the contract).
AD_ACCOUNT_FIELDS = "name,id,account_id"

# api.ts:517
CAMPAIGN_FIELDS = "name,id"

# api.ts:549. `targeting` is the load-bearing one: it is the entire input to
# `adopt.authoring.extract.extract_from_adset`, which needs `id` and
# `targeting` and uses `name` for error messages.
ADSET_FIELDS = "name,id,targeting"

# api.ts:583-595, verbatim and in the same order. This list is what ends up
# stored as a creative `template`, so adding or removing a field here changes
# what a study deploys. `contextual_multi_ads` is in the request but not in the
# dashboard's `Ad` TypeScript interface; `effective_instagram_story_id` and
# `instagram_actor_id` are in the interface but not in the request. The request
# is what actually runs, so the request is what is reproduced.
CREATIVE_FIELDS = ",".join(
    [
        "id",
        "name",
        "actor_id",
        "asset_feed_spec",
        "degrees_of_freedom_spec",
        "effective_instagram_media_id",
        "effective_object_story_id",
        "instagram_user_id",
        "object_story_spec",
        "contextual_multi_ads",
        "thumbnail_url",
    ]
)

# api.ts:598 — the creative arrives NESTED under each ad, via field expansion,
# not as a second request.
AD_FIELDS = f"id,name,creative{{{CREATIVE_FIELDS}}}"


# --------------------------------------------------------------------------
# Id validation
# --------------------------------------------------------------------------

# Graph object ids are numeric strings. This is validated rather than trusted
# because ids are interpolated into a URL PATH, not a query string: an id of
# `me/adaccounts` or `..` would silently retarget the request. Meta ids are
# also `<account>_<object>`-shaped in some APIs, hence the optional second
# part.
_ID_RE = re.compile(r"^\d+(_\d+)?$")

# `act_` + digits. The dashboard passes the bare numeric `account_id` and
# prefixes it (`api.ts:529`); an agent reading `/meta/adaccounts` sees the
# already-prefixed `id` field. Both are accepted so neither caller has to know
# which form it holds.
_ACCOUNT_RE = re.compile(r"^(act_)?\d+$")


def _validate_id(value: str, what: str) -> str:
    if not _ID_RE.match(value or ""):
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{value}' is not a valid Meta {what} id. "
                "Meta object ids are numeric."
            ),
        )
    return value


def normalize_account_id(value: str) -> str:
    """`123` or `act_123` -> `act_123`."""
    if not _ACCOUNT_RE.match(value or ""):
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{value}' is not a valid ad account id. Pass either the "
                "numeric account_id (e.g. 1234567890) or the prefixed id "
                "(e.g. act_1234567890)."
            ),
        )
    return value if value.startswith("act_") else f"act_{value}"


# --------------------------------------------------------------------------
# Credential resolution
# --------------------------------------------------------------------------
#
# THE DECISION, and why it is not what §8 of the plan says.
#
# The plan wrote "reading with the study owner's stored credential". These
# routes have no study — they are the endpoints you call *before* you have
# written a `general` conf, precisely so that you can find out what to put in
# it. So there is no study owner to read, and the credential resolved here is
# the CALLING USER'S.
#
# That is not a weakening. The API key identifies a user (`sub`), and the
# dashboard already reads Meta client-side with that same user's token; the
# proxy just moves where the read happens. What it does mean is that the token
# in play may not be the one the study will eventually run on, if the `general`
# conf names a different `credentials_key`. Hence:
#
#   * `?credentials_key=` selects one explicitly, and takes exactly the value
#     that goes into `general.credentials_key`, so an agent can point the proxy
#     at the study's own credential and see what the study will see.
#   * With no `credentials_key` and exactly one Facebook credential, that one is
#     used. This is the overwhelmingly common case.
#   * With no `credentials_key` and MORE than one, the request FAILS with a 409
#     naming them, rather than picking. Ad accounts differ per token, so a
#     silent pick would hand the agent an ad account the study cannot use and
#     the failure would surface much later, at ad-set create time, as a Meta
#     rejection with no obvious cause.
#
# `GET /{org}/meta/credentials` exists so the 409 is recoverable without a
# human: it lists the names, and never the tokens.


class ResolvedCredential:
    __slots__ = ("key", "token")

    def __init__(self, key: str, token: str):
        self.key = key
        self.token = token


def resolve_credential(user_id: str, credentials_key: Optional[str]):
    """Pick the Facebook token to read with. Raises HTTPException, loudly."""
    if credentials_key:
        token = get_facebook_token(user_id, credentials_key)
        if not token:
            available = [c["key"] for c in list_facebook_credentials(user_id)]
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No Facebook credential named '{credentials_key}' with an "
                    "access token. "
                    + (
                        f"Available: {', '.join(available)}."
                        if available
                        else "This account has no Facebook credentials at all; "
                        "connect one in the dashboard's Accounts page."
                    )
                ),
            )
        return ResolvedCredential(credentials_key, token)

    credentials = list_facebook_credentials(user_id)

    if not credentials:
        raise HTTPException(
            status_code=400,
            detail=(
                "This account has no connected Facebook credential, so there "
                "is no token to read Meta with. A human must connect a "
                "Facebook account in the dashboard (Accounts page); the OAuth "
                "exchange is Auth0-only and cannot be done with an API key."
            ),
        )

    if len(credentials) > 1:
        names = ", ".join(f"'{c['key']}'" for c in credentials)
        raise HTTPException(
            status_code=409,
            detail=(
                "This account has more than one Facebook credential and each "
                f"can see a different set of ad accounts ({names}). Pass "
                "?credentials_key=<name> to choose — use the same value you "
                "put in the study's general conf. GET /{org_id}/meta/credentials "
                "lists them."
            ),
        )

    key = credentials[0]["key"]
    token = get_facebook_token(user_id, key)
    if not token:
        # list_facebook_credentials already required a non-null access_token,
        # so this is only reachable if the row changed between the two reads.
        raise HTTPException(
            status_code=409,
            detail=f"The Facebook credential '{key}' no longer has an access token.",
        )
    return ResolvedCredential(key, token)


# --------------------------------------------------------------------------
# The Graph call
# --------------------------------------------------------------------------


def _api_for(token: str) -> FacebookAdsApi:
    """Same construction as the optimize path (`facebook/state.py:188`).

    Built per request rather than cached: the session carries the access token
    and an `appsecret_proof` derived from it, so a cache keyed on anything less
    than the token would be a cross-tenant credential leak.
    """
    api = get_api(env, token)
    api._session.timeout = GRAPH_TIMEOUT_SECONDS
    return api


def _meta_error(e: FacebookRequestError) -> HTTPException:
    """Map a Meta rejection onto a status and a structured body.

    Never `str(e)`. The SDK's `__str__` interpolates `request_context`, which
    carries the full request params — and the SDK also stringifies the request
    for its own logging. Only the four documented error accessors are copied
    out, all of which are Meta's own words about what was wrong; none of them
    can contain the access token, which travels on the session's params and
    never on the call's.
    """
    http_status = e.http_status()
    code = e.api_error_code()
    message = e.api_error_message() or e.get_message()

    if http_status in (400, 403, 404):
        # The caller asked for something Meta will not give them: a bad id, an
        # object on an account this token cannot see, an expired token (code
        # 190). All actionable by the caller, so pass the status through.
        status_code = http_status
    else:
        # 429, 5xx, or anything unrecognised: not the caller's request, but the
        # upstream. 502 says "the thing I depend on failed", which is true and
        # is not a bare 500.
        status_code = 502

    return HTTPException(
        status_code=status_code,
        detail={
            "message": f"Meta rejected the request: {message}",
            "meta_error": {
                "code": code,
                "subcode": e.api_error_subcode(),
                "type": e.api_error_type(),
                "message": message,
                "http_status": http_status,
            },
        },
    )


def _graph_get(api: FacebookAdsApi, path: Tuple[str, ...], params: Dict[str, Any]):
    try:
        response = api.call("GET", path, params=params)
    except FacebookRequestError as e:
        # Logged with the path but never the params, for the same reason the
        # response omits them.
        logger.warning(
            "Meta graph GET /%s failed: code=%s status=%s",
            "/".join(path),
            e.api_error_code(),
            e.http_status(),
        )
        raise _meta_error(e)
    except Exception as e:
        # Connection reset, DNS, read timeout — the SDK does not wrap these.
        # A network failure talking to Meta is emphatically not a 500 from us.
        logger.warning(
            "Meta graph GET /%s failed: %s", "/".join(path), type(e).__name__
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Could not reach the Meta Graph API "
                    f"({type(e).__name__}). This is transient; retry."
                ),
                "meta_error": None,
            },
        )

    body = response.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Meta returned an unexpected response shape.",
                "meta_error": None,
            },
        )
    return body


def _after_from_url(url: Optional[str]) -> Optional[str]:
    """The `after` query parameter of a Meta `paging.next` URL, if it has one.

    A fallback for the case where a page carries `paging.next` but no
    `paging.cursors.after`. Meta normally sends both, but not universally —
    some edges paginate with `offset`/`until` instead and still populate
    `next`, and cursor-paginated edges have been observed to omit `cursors` on
    a page. Without this, such a page comes back as
    `{"truncated": true, "after": null}`: the caller is correctly told the list
    is incomplete and given nothing to resume with, which is the one
    unrecoverable shape this endpoint could return.

    Returns None rather than raising on anything unparseable — the caller then
    reports `after: null`, which is the honest answer and no worse than before.
    """
    if not url:
        return None
    try:
        after = parse_qs(urlparse(url).query).get("after")
    except ValueError:
        return None
    return after[0] if after else None


def paged_get(
    api: FacebookAdsApi,
    path: Tuple[str, ...],
    fields: str,
    limit: int,
    after: Optional[str],
) -> Dict[str, Any]:
    """Follow Meta's cursors up to `MAX_PAGES`. See the MAX_PAGES comment.

    Meta signals "there is more" with `paging.next`, and hands the resume token
    back as `paging.cursors.after`. `after` is present on the LAST page too, so
    `next` is the only reliable end-of-collection test.
    """
    collected: List[Any] = []
    cursor = after
    pages = 0
    has_more = False

    while pages < MAX_PAGES:
        params: Dict[str, Any] = {"fields": fields, "limit": limit, "pretty": 0}
        if cursor:
            # NOT `cursor`. The dashboard sends `params['cursor']`
            # (`api.ts:495`), which Graph does not recognise, so its "load
            # more" silently re-fetches page one. Reproducing the contract
            # does not extend to reproducing that.
            params["after"] = cursor

        body = _graph_get(api, path, params)
        page = body.get("data")
        collected.extend(page if isinstance(page, list) else [])
        pages += 1

        paging = body.get("paging") or {}
        next_url = paging.get("next")
        cursor = (paging.get("cursors") or {}).get("after") or _after_from_url(next_url)
        has_more = bool(next_url)
        if not has_more:
            break

    return {
        "data": collected,
        "paging": {
            # The cursor to resume from, or None when the collection is
            # exhausted. Taken from `paging.cursors.after`, falling back to the
            # `after` in `paging.next` — see `_after_from_url` for why a page
            # can have one and not the other, and why `truncated: true` with a
            # null cursor is the one answer this endpoint must not give.
            "after": cursor if has_more else None,
            # True iff we stopped because of MAX_PAGES, not because Meta ran
            # out. An agent that ignores this reads an incomplete list; it is
            # in the body rather than only in the docs so that ignoring it is
            # a choice.
            "truncated": has_more,
            "pages_fetched": pages,
        },
    }


# --------------------------------------------------------------------------
# Shared dependencies
# --------------------------------------------------------------------------


def _check_org(user_id: str, org_id: str) -> None:
    """404 unless the caller is a member of `org_id`.

    Note what this does and does not do. `credentials` are user-scoped (see
    `db.list_facebook_credentials`), so org membership does not narrow WHICH
    Meta data is visible — the caller's own token decides that. It is here for
    consistency with every other route on this service, and so that the org
    segment cannot be used to probe which orgs exist.
    """
    try:
        # `orgs_lookup.org_id` is UUID, so an unparseable id would otherwise
        # blow up in the driver as a 500. A malformed org id is definitionally
        # not an org the caller belongs to, so it gets the same answer as one
        # they simply are not in — the same reasoning as `studies.py`.
        uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")

    if not user_in_org(user_id, org_id):
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_id}")


CurrentUser = Annotated[User, Depends(get_current_user)]

# Belt and braces with the middleware. `scope_enforcement_middleware` already
# denies a scoped key without `meta:read` before routing, and is the fail-closed
# half; this dependency is the one that survives the middleware being
# reordered, and it puts the requirement in the route signature where a reader
# of this file can see it.
RequireMetaRead = Annotated[None, Depends(require_scope("meta:read"))]

LimitQuery = Annotated[int, Query(ge=1, le=MAX_LIMIT)]


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
#
# EVERY HANDLER BELOW IS `async def` AND DOES ITS WORK IN `asyncio.to_thread`.
#
# That is not decoration. All the work here is blocking: `user_in_org` and the
# credential lookups are synchronous psycopg, and `FacebookAdsApi.call` is
# synchronous `requests`. Run directly in an `async def` handler, a single
# request would pin the event loop for as long as Meta took to answer — up to
# `HANDLER_TIMEOUT_SECONDS` in the worst case — and while it did, this process
# would serve nothing at all, `/health` included. One slow ad account would
# read as a dead pod.
#
# `server.py` already established the pattern for exactly this hazard:
# `optimize_study` does its Meta work with `await asyncio.to_thread(...)` under
# `@async_timeout(300)`. These routes follow it, with the timeout derived from
# this module's own limits.
#
# Plain `def` handlers would also have kept the loop free — FastAPI runs those
# in its threadpool — but `asyncio.wait_for` cannot interrupt a sync handler,
# so there would be no way to bound how long a client waits. `async def` plus
# `to_thread` gets both. Note what the timeout can and cannot do: it frees the
# loop and answers the client, but the worker thread runs to completion
# regardless (see `deps.async_timeout`). The thread terminates on its own
# because every Graph call carries `GRAPH_TIMEOUT_SECONDS` as a socket timeout.
#
# Cheap, non-blocking validation (ids, mutually-exclusive parameters) stays
# OUTSIDE the thread, so a malformed request is rejected without occupying a
# worker at all.


@router.get("/{org_id}/meta/credentials")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def list_credentials(
    org_id: str,
    user: CurrentUser,
    _: RequireMetaRead = None,
):
    """The caller's Facebook credentials by name. Never their tokens.

    Exists because `credentials_key` is otherwise undiscoverable: an agent
    needs it both to disambiguate this proxy (see `resolve_credential`) and to
    write `general.credentials_key`, and no API-key-reachable endpoint listed
    it before. The Go service's `/accounts` does, but it is Auth0-only and it
    returns `details` — including the access token — to the browser.
    """

    def _work():
        _check_org(user.user_id, org_id)
        return {
            "data": [
                {
                    "key": c["key"],
                    "entity": c["entity"],
                    "created": c["created"].isoformat() if c.get("created") else None,
                }
                for c in list_facebook_credentials(user.user_id)
            ]
        }

    return await asyncio.to_thread(_work)


@router.get("/{org_id}/meta/adaccounts")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def list_ad_accounts(
    org_id: str,
    user: CurrentUser,
    credentials_key: Optional[str] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    after: Optional[str] = None,
    _: RequireMetaRead = None,
):
    """`GET /me/adaccounts` — the dashboard's `fetchAdAccounts` (api.ts:475).

    `account_id` is the bare number that goes in `general.ad_account`; `id` is
    the same thing prefixed `act_`. Both are returned because the dashboard
    returns both and the two are used in different places.
    """

    def _work():
        _check_org(user.user_id, org_id)
        credential = resolve_credential(user.user_id, credentials_key)
        return paged_get(
            _api_for(credential.token),
            ("me", "adaccounts"),
            AD_ACCOUNT_FIELDS,
            limit,
            after,
        )

    return await asyncio.to_thread(_work)


@router.get("/{org_id}/meta/campaigns")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def list_campaigns(
    org_id: str,
    user: CurrentUser,
    account: str = Query(..., description="Ad account id, act_123 or 123"),
    credentials_key: Optional[str] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    after: Optional[str] = None,
    _: RequireMetaRead = None,
):
    """`GET /act_<id>/campaigns` — the dashboard's `fetchCampaigns` (api.ts:505).

    No status filter, matching the dashboard: a template campaign is very often
    paused or completed, so filtering to active ones would hide exactly the
    campaigns an author is looking for.
    """
    account_id = normalize_account_id(account)

    def _work():
        _check_org(user.user_id, org_id)
        credential = resolve_credential(user.user_id, credentials_key)
        return paged_get(
            _api_for(credential.token),
            (account_id, "campaigns"),
            CAMPAIGN_FIELDS,
            limit,
            after,
        )

    return await asyncio.to_thread(_work)


@router.get("/{org_id}/meta/adsets")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def list_adsets(
    org_id: str,
    user: CurrentUser,
    campaign: str = Query(..., description="Campaign id"),
    credentials_key: Optional[str] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    after: Optional[str] = None,
    _: RequireMetaRead = None,
):
    """`GET /<campaign>/adsets` — the dashboard's `fetchAdsets` (api.ts:537).

    Each returned ad set is directly the input to
    `adopt.authoring.extract.extract_from_adset` (on
    `feature/agent-study-authoring-phase1`, PR #254), which is why `targeting`
    is in the field list and must stay there.
    """
    _validate_id(campaign, "campaign")

    def _work():
        _check_org(user.user_id, org_id)
        credential = resolve_credential(user.user_id, credentials_key)
        return paged_get(
            _api_for(credential.token),
            (campaign, "adsets"),
            ADSET_FIELDS,
            limit,
            after,
        )

    return await asyncio.to_thread(_work)


@router.get("/{org_id}/meta/ads")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def list_ads(
    org_id: str,
    user: CurrentUser,
    campaign: Optional[str] = Query(None, description="Campaign id"),
    adset: Optional[str] = Query(None, description="Ad set id"),
    credentials_key: Optional[str] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    after: Optional[str] = None,
    _: RequireMetaRead = None,
):
    """`GET /<campaign|adset>/ads` — the dashboard's `fetchAds` (api.ts:570).

    Each ad carries its creative NESTED under `creative`, via field expansion,
    exactly as the dashboard receives it — the Creatives form stores
    `ad["creative"]` verbatim as the `template`
    (`dashboard/.../forms/creatives/Creative.tsx:53`).

    The dashboard only ever asks by campaign; `adset` is the one addition, and
    it is here because the plan asked for it and because Graph serves
    `/<adset>/ads` identically. Exactly one of the two is required: defaulting
    would mean guessing which id an ambiguous caller meant.
    """
    if bool(campaign) == bool(adset):
        raise HTTPException(
            status_code=400,
            detail="Pass exactly one of ?campaign=<id> or ?adset=<id>.",
        )

    parent = campaign or adset
    _validate_id(parent, "campaign" if campaign else "ad set")

    def _work():
        _check_org(user.user_id, org_id)
        credential = resolve_credential(user.user_id, credentials_key)
        return paged_get(
            _api_for(credential.token),
            (parent, "ads"),
            AD_FIELDS,
            limit,
            after,
        )

    return await asyncio.to_thread(_work)


@router.get("/{org_id}/meta/ads/{ad_id}/creative")
@async_timeout(HANDLER_TIMEOUT_SECONDS)
async def get_ad_creative(
    org_id: str,
    ad_id: str,
    user: CurrentUser,
    credentials_key: Optional[str] = None,
    _: RequireMetaRead = None,
):
    """The creative blob off one ad — what becomes `creatives[].template`.

    The dashboard has no equivalent call: it reads a whole campaign's ads and
    picks one in the browser. This route exists for the agent that already has
    an ad id (from `/meta/ads`, or from a researcher who pasted one) and wants
    the one object it is going to store, without pulling every creative in the
    campaign to find it.

    Unpaginated by construction — an ad has exactly one creative.
    """
    _validate_id(ad_id, "ad")

    def _work():
        _check_org(user.user_id, org_id)
        credential = resolve_credential(user.user_id, credentials_key)
        return _graph_get(
            _api_for(credential.token),
            (ad_id,),
            {"fields": f"id,name,creative{{{CREATIVE_FIELDS}}}", "pretty": 0},
        )

    body = await asyncio.to_thread(_work)

    creative = body.get("creative")
    if not creative:
        # Meta answered about the ad but there is no creative on it. A 404 on
        # the *creative* rather than a 200 with a null body, because an agent
        # storing `template: null` writes a study that fails much later.
        raise HTTPException(
            status_code=404,
            detail=(
                f"Ad {ad_id} exists but has no creative readable with this "
                "credential."
            ),
        )

    return {"data": creative}
