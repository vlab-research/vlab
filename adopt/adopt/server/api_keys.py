"""API-key minting, listing, revocation and scope enforcement.

Phase 0 of `planning/agent-study-authoring.md` §8. The point of all of this is
that handing an API key to an agent should not be handing over the account
permanently.

THE MODEL
---------

A vlab API key is an HS256 JWT *plus* a `credentials` row. The token itself is
never stored (we only ever hold its `jti`), so the row is the only revocable
thing, and validity is **positive**: a key is live iff its row is live. That is
deliberately not a denylist of dead tokens — a denylist has to be complete to be
correct, and grows forever.

The `jti` claim is what ties a token to its row. That is the whole reason the
lookup is keyed on `jti` and not on the token's name: delete a key called
"agent" and mint a new one with the same name, and the old token must stay dead.
Keying on the name would resurrect it.

THREE KINDS OF TOKEN reach this code
------------------------------------

1. **v2 keys** — minted after `20260904000000_api_token_hardening`. They carry
   `https://vlab.digital/token-version: 2`, an `exp`, and a `jti` with a row
   behind it. Row required, expiry enforced, scopes honoured.

2. **legacy keys** — minted before it. This is where vlab diverges from the fly
   precedent (`fly:899443fe`) in a way that matters. vlab never persisted
   *anything* for an API key: `generate_api_token` minted a `jti`, put it in the
   token and threw it away — that is what the
   `# TODO: check payload ("id") against blacklist / whitelist` in `auth.py` was
   marking. So (a) there is nothing to backfill, the jtis in the wild are
   unrecoverable, and (b) **"has a jti" cannot be the discriminator** between
   hardened and legacy, because every vlab key ever minted has one. An explicit
   version claim is the discriminator instead.

   A legacy key is therefore accepted with no row at all — exactly today's
   behaviour, nobody's key breaks — unless a *tombstone* row denies it by name.
   That tombstone is a denylist, with a denylist's weaknesses, and it exists
   only because the alternative for a leaked pre-migration key is "nothing you
   can do". See `legacy_key_revoked` for what it can and cannot promise.

3. **Auth0 RS256 tokens** — the dashboard. Never touched by any of this; they
   have no scopes claim and so are unrestricted, which is what a human session
   in the dashboard already is.

REVOCATION LATENCY
------------------

Row lookups are cached in-process for `CACHE_TTL_SECONDS` (30s), **including
negative results**. Negative caching is the point: replaying random jtis must
not turn into one database read per request. The cost is that revocation is
"dead within 30 seconds", not instant — the revoking replica evicts its own
entry immediately, every other replica waits out the TTL. Short enough that a
leaked key is dead in well under a minute; long enough that a busy agent is not
a database round trip per request.

SCOPES
------

`<resource>:<action>`, `write` implies `read`, and **an absent scopes claim
means unrestricted**. That last rule is what stops every existing key (and every
dashboard session) from breaking the day this ships; it is not an oversight.
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional, Sequence

import orjson
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from pydantic import BaseModel, Field

from ..db import execute, query
from .auth import (
    API_TOKEN_TTL_DAYS,
    MAX_API_TOKEN_TTL_DAYS,
    NAME_CLAIM,
    SCOPES_CLAIM,
    TOKEN_VERSION,
    VERSION_CLAIM,
    AuthError,
    generate_api_token,
)
from .db import db_cnf
from .deps import User, get_current_user, security

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# Row shape
# --------------------------------------------------------------------------

# `credentials` carries UNIQUE(user_id, entity, key), so `key` = the token name
# gives us one live key per (user, name) for free — and, because revocation is a
# row DELETE rather than a soft-delete flag, revoking a key frees its name for
# reuse. A soft-delete flag would have meant you could revoke "mcp-agent" and
# then never create another key called "mcp-agent" again.
API_TOKEN_ENTITY = "api_token"

# Tombstones for kind-2 (legacy) tokens, which have no row of their own to
# delete. Separate entity so it cannot collide with a live key of the same name.
REVOKED_ENTITY = "api_token_revoked"


# --------------------------------------------------------------------------
# Scopes — pure, no IO, no clock
# --------------------------------------------------------------------------

ANY = "*"
READ = "read"
WRITE = "write"
READ_METHODS = ("GET", "HEAD", "OPTIONS")

# The resources a key can be scoped to.
#
# `studies` and `responses` are deliberately NOT one resource. Study
# configuration is the researcher's own work; ad-attributions are a
# respondent-level record of who arrived from which ad. A key that can read a
# study's structure without reading anything about the people in it is the
# distinction worth being able to express, and it is the one an agent authoring
# a study actually needs.
#
# `stats` is aggregate-only (recruitment counts, cost curves, segment progress):
# derived from respondent data but not itself respondent data.
#
# `optimize` is separate from `studies` because an optimize instruction spends
# money on Meta. Being able to hand out "can read and write the config, cannot
# launch ads" is worth a resource of its own.
#
# `meta` is the read-only Meta Graph proxy (`/{org}/meta/...`, see `meta.py`).
# It is its own resource rather than part of `studies` because it reads a
# DIFFERENT system with a DIFFERENT credential: the researcher's Facebook token,
# which can see every ad account, campaign and creative that researcher has on
# Meta — including ones belonging to no vlab study at all. A key scoped to
# `studies:write` is a key that can edit this org's study configuration; it
# should not, by that fact alone, become a window onto the researcher's whole
# Meta estate. Only `meta:read` exists in practice — the proxy is read-only by
# construction — but `meta:write` is expressible so that a future write proxy
# does not have to re-cut the vocabulary.
#
# `auth` is key management and is NEVER implicitly granted: a scoped key that
# could mint an unscoped one is not scoped at all.
RESOURCES = ("studies", "responses", "stats", "optimize", "meta", "auth")
ACTIONS = (READ, WRITE, ANY)

# Paths that carry no authentication at all, so there is nothing to authorize.
# Enumerated rather than inferred, because "route has no auth dependency" is not
# something this layer can see.
PUBLIC_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


def parse_scope(scope: str) -> tuple[str, Optional[str]]:
    resource, _, action = str(scope).partition(":")
    return resource, action or None


def is_known_scope(scope: str) -> bool:
    if scope == ANY:
        return True
    resource, action = parse_scope(scope)
    return resource in RESOURCES and action in ACTIONS


def scope_grants(granted: str, required: str) -> bool:
    """Does holding `granted` satisfy a need for `required`?

    `write` implies `read` on the same resource: every write route here reads
    its own object back, and a key that can edit a study but not see it is not a
    permission anyone means to hand out.
    """
    if granted == ANY:
        return True
    if required == ANY:
        return False

    g_res, g_act = parse_scope(granted)
    r_res, r_act = parse_scope(required)

    if g_res != r_res:
        return False
    if g_act == ANY:
        return True
    if r_act == ANY:
        return False
    return g_act == r_act or (g_act == WRITE and r_act == READ)


def scopes_allow(scopes: Optional[Sequence[str]], required: str) -> bool:
    """`None` (absent claim) is unrestricted. An empty list denies everything."""
    if scopes is None:
        return True
    return any(scope_grants(g, required) for g in scopes)


def action_for_method(method: str) -> str:
    return READ if str(method).upper() in READ_METHODS else WRITE


def required_scope(method: str, path: str) -> Optional[str]:
    """The scope a request needs, or None when the path maps to no resource.

    vlab's routes are NOT prefix-shaped the way fly's `/api/v1/<resource>` ones
    are — the first segment is an `org_id`, so a plain first-segment lookup
    would classify every request by a UUID. The resource lives at segment 2 and,
    under `studies`, at the segment after the slug.

    Returning None means "unknown", and an unknown path is DENIED for a scoped
    key (see `is_authorized`). Fail closed: a route added without being
    classified here should become unreachable for scoped keys, not silently
    reachable by all of them.
    """
    segments = [s for s in str(path or "").split("?")[0].split("/") if s]
    action = action_for_method(method)

    if not segments:
        return None

    # /users/api-key, /users/api-keys/...
    if segments[0] == "users":
        return f"auth:{action}"

    # Everything else is org-scoped: /{org_id}/<area>/...
    if len(segments) < 2:
        return None

    area = segments[1]

    if area == "optimize":
        return f"optimize:{action}"

    # /{org_id}/meta/... — every route under here is the Graph proxy, including
    # /{org_id}/meta/ads/{ad_id}/creative, so the area alone classifies it. The
    # proxy registers only GET routes; a POST would map to `meta:write`, which
    # nothing grants and no route serves, so it fails closed twice over.
    if area == "meta":
        return f"meta:{action}"

    if area == "studies":
        # /{org_id}/studies/{slug}/<tail>
        tail = segments[3] if len(segments) > 3 else ""
        # `validate` is a POST that writes nothing — it assembles the stored
        # confs in memory and returns a report (see `server/validate.py`).
        # Classifying it by method would demand `studies:write` for a pure
        # read, so a read-only key could not check its own study. Pinned to
        # read, deliberately and regardless of method.
        if tail == "validate":
            return f"studies:{READ}"
        if tail in ("", "confs", "copy-from"):
            return f"studies:{action}"
        # ad-attributions and ad-attributions.csv
        if tail.startswith("ad-attributions"):
            return f"responses:{action}"
        if tail in ("recruitment-stats", "segments-progress", "cost-over-time"):
            return f"stats:{action}"
        return None

    return None


def is_authorized(scopes: Optional[Sequence[str]], method: str, path: str) -> bool:
    if scopes is None:
        return True
    if ANY in scopes:
        # `*` means exactly what an absent claim means, including on routes
        # `required_scope` does not know about yet.
        return True
    required = required_scope(method, path)
    if required is None:
        return False
    return scopes_allow(scopes, required)


def normalize_scopes(value: Any) -> Optional[List[str]]:
    """None -> unrestricted. Anything unrecognisable -> [] (deny everything).

    Falling back to unrestricted on a malformed claim would make a corrupted
    token more powerful than a well-formed one.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return [s for s in value.split() if s]
    if isinstance(value, (list, tuple)):
        return [str(s) for s in value]
    return []


def can_grant_scopes(
    caller_scopes: Optional[Sequence[str]], requested: Optional[Sequence[str]]
) -> bool:
    """Attenuation: a key may only mint a key no more powerful than itself.

    A `requested` of None is a request for FULL ACCESS, not for nothing, so it
    is checked as `*`. Reading it as an empty list instead would let any scoped
    key mint an unscoped one and make the whole scheme decorative.
    """
    if caller_scopes is None:
        return True
    wanted = [ANY] if requested is None else list(requested)
    return all(scopes_allow(caller_scopes, r) for r in wanted)


def validate_scopes(requested: Optional[Sequence[str]]) -> Optional[List[str]]:
    """Returns the de-duplicated scope list, or raises HTTPException(400).

    Unknown scopes are rejected rather than ignored: a `studies:reed` that
    silently denied every request would be indistinguishable from a broken key.
    """
    if requested is None:
        return None

    scopes = normalize_scopes(requested)
    if not scopes:
        raise HTTPException(
            status_code=400,
            detail="scopes must be a non-empty list of strings, or omitted for "
            "an unrestricted key",
        )

    unknown = [s for s in scopes if not is_known_scope(s)]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unknown scope(s): {', '.join(unknown)}. "
                f"Valid resources: {', '.join(RESOURCES)}; "
                f"valid actions: {', '.join(ACTIONS)}"
            ),
        )

    # dict.fromkeys rather than set() so the stored order is the requested one,
    # which makes a listed key readable.
    return list(dict.fromkeys(scopes))


# --------------------------------------------------------------------------
# Bounded TTL cache
# --------------------------------------------------------------------------

CACHE_TTL_SECONDS = 30.0
CACHE_MAX_ENTRIES = 5000


class TtlCache:
    """Bounded, TTL'd, negative-caching, thread-safe.

    `get` returns the `miss` sentinel on a miss, so a cached `None` ("this jti
    is known not to exist") is distinguishable from "not looked up yet". That
    distinction is the whole reason this class exists rather than a dict: an
    attacker replaying random jtis must not become one database read per
    request.

    The clock is injectable so expiry is asserted by passing `now` rather than
    by sleeping in a test.
    """

    _MISS = object()

    def __init__(self, ttl_seconds: float, max_entries: int = CACHE_MAX_ENTRIES):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._entries: Dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, now: Optional[float] = None) -> Any:
        now = time.monotonic() if now is None else now
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return self._MISS
            expires_at, value = entry
            if now >= expires_at:
                self._entries.pop(key, None)
                return self._MISS
            return value

    def set(self, key: str, value: Any, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            if key not in self._entries and len(self._entries) >= self.max_entries:
                # dicts iterate in insertion order, so the first key is the
                # oldest write. FIFO, not LRU — cheap, and with a 30s TTL the
                # difference is not worth a linked list.
                self._entries.pop(next(iter(self._entries)), None)
            self._entries[key] = (now + self.ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


_cache = TtlCache(CACHE_TTL_SECONDS)


def clear_api_key_cache() -> None:
    """Drop every cached lookup. For tests, and for nothing else in production."""
    _cache.clear()


def _jti_cache_key(jti: str) -> str:
    return f"jti:{jti}"


def _revoked_cache_key(user_id: str, name: str) -> str:
    # The user id is IN the key, not just checked after the fact: two users may
    # each have a legacy key called "agent", and one revoking theirs must not
    # return a cached "revoked" for the other's.
    return f"revoked:{user_id}\x00{name}"


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def persist_api_token(
    user_id: str,
    name: str,
    jti: str,
    scopes: Optional[List[str]],
    issued_at: datetime,
    expires_at: datetime,
) -> None:
    """Write the credentials row that makes a minted token live.

    Called by `auth.generate_api_token`, not by the routes — see the docstring
    there for why minting and persisting are one operation.
    """
    details: Dict[str, Any] = {
        "name": name,
        "jti": jti,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    # Absent rather than null: `details->>'scopes' IS NULL` and
    # `details->'scopes' = 'null'` must not both be things a reader has to
    # handle, and absent is what "unrestricted" means everywhere else here.
    if scopes is not None:
        details["scopes"] = scopes

    q = """
    INSERT INTO credentials (user_id, entity, key, details)
    VALUES (%s, %s, %s, %s)
    """
    execute(
        db_cnf,
        q,
        (user_id, API_TOKEN_ENTITY, name, orjson.dumps(details).decode("utf8")),
    )


def _select_api_token_row(jti: str) -> Optional[Dict[str, Any]]:
    # Hits unique_api_token_jti (partial, STORING details/user_id/org_id/key),
    # so this is an index-only read. See
    # devops/migrations/20260904000001_api_token_hardening_jti_index.up.sql.
    q = """
    SELECT user_id, key, details
    FROM credentials
    WHERE api_token_jti = %s
    """
    rows = list(query(db_cnf, q, (jti,), as_dict=True))
    return rows[0] if rows else None


def _select_api_token_rows(user_id: str) -> List[Dict[str, Any]]:
    q = """
    SELECT key, details, created
    FROM credentials
    WHERE user_id = %s AND entity = %s
    ORDER BY created DESC
    """
    return list(query(db_cnf, q, (user_id, API_TOKEN_ENTITY), as_dict=True))


def _delete_api_token_row(user_id: str, jti: str) -> Optional[str]:
    """Delete one key. Returns its name, or None when nothing matched.

    Scoped to the caller in SQL rather than checked afterwards, so a miss and
    somebody else's jti are the same answer and this never confirms the
    existence of another user's key.
    """
    q = """
    DELETE FROM credentials
    WHERE user_id = %s AND entity = %s AND api_token_jti = %s
    RETURNING key
    """
    rows = list(query(db_cnf, q, (user_id, API_TOKEN_ENTITY, jti), as_dict=True))
    return rows[0]["key"] if rows else None


def _select_revocation_rows(user_id: str) -> List[Dict[str, Any]]:
    q = """
    SELECT key, created
    FROM credentials
    WHERE user_id = %s AND entity = %s
    ORDER BY created DESC
    """
    return list(query(db_cnf, q, (user_id, REVOKED_ENTITY), as_dict=True))


def _insert_revocation_row(user_id: str, name: str) -> None:
    q = """
    INSERT INTO credentials (user_id, entity, key, details)
    VALUES (%s, %s, %s, '{}')
    ON CONFLICT (user_id, entity, key) DO NOTHING
    """
    execute(db_cnf, q, (user_id, REVOKED_ENTITY, name))


def _revocation_row_exists(user_id: str, name: str) -> bool:
    q = """
    SELECT 1
    FROM credentials
    WHERE user_id = %s AND entity = %s AND key = %s
    LIMIT 1
    """
    return bool(list(query(db_cnf, q, (user_id, REVOKED_ENTITY, name))))


# --------------------------------------------------------------------------
# Cached lookups
# --------------------------------------------------------------------------


def lookup_api_token(jti: str) -> Optional[Dict[str, Any]]:
    key = _jti_cache_key(jti)
    cached = _cache.get(key)
    if cached is not TtlCache._MISS:
        return cached

    row = _select_api_token_row(jti)
    # Cached whether or not it was found — see the module docstring on why the
    # negative half is the important half.
    _cache.set(key, row)
    return row


def legacy_key_revoked(user_id: str, name: str) -> bool:
    """Has this user tombstoned legacy keys called `name`?

    What this CAN promise: a leaked pre-migration key is killable at all, which
    it otherwise is not — nothing was ever persisted for it, so there is no row
    to delete and positive validity has nothing to stand on.

    What it CANNOT promise: precision. Names were never unique before this
    migration (nothing enforced them, because nothing was stored), so a user
    with two legacy keys both called "agent" kills both or neither. That
    imprecision errs towards denying, which is the right direction, and it is
    exactly the hazard `jti` removes for every key minted from now on. The fix
    for a legacy key is to reissue it as a v2 one.
    """
    key = _revoked_cache_key(user_id, name)
    cached = _cache.get(key)
    if cached is not TtlCache._MISS:
        return cached

    revoked = _revocation_row_exists(user_id, name)
    _cache.set(key, revoked)
    return revoked


# --------------------------------------------------------------------------
# The verifier hook — called from auth.verify_api_token
# --------------------------------------------------------------------------


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def assert_token_row_live(claims: Dict[str, Any]) -> None:
    """Raise AuthError unless this token's backing state says it is still live.

    Called by `auth.verify_api_token` AFTER the signature, audience, issuer and
    (when present) `exp` have been checked, so everything here can trust the
    claims. This is the check the `# TODO: check payload ("id") against
    blacklist / whitelist` was standing in for.
    """
    revoked = AuthError(
        {
            "code": "token_revoked",
            "description": "This API key has been revoked or has expired.",
        },
        401,
    )

    version = claims.get(VERSION_CLAIM)
    user_id = claims.get("sub")

    if isinstance(version, int) and version >= TOKEN_VERSION:
        jti = claims.get("jti")
        if not jti:
            # Only reachable by something holding the signing secret; a v2 token
            # without a jti has no row it could ever match, so fail closed.
            raise revoked
        if "exp" not in claims:
            # Same: our mint path always sets one. Refusing an unexpiring v2
            # token means the TTL cannot be dropped by re-signing.
            raise revoked

        row = lookup_api_token(jti)
        if row is None:
            raise revoked
        if row["user_id"] != user_id:
            # A jti is a server-side uuid4 so this should be impossible; if it
            # ever happens it is a bug or an attack, and either way not a login.
            logger.warning("api key jti %s does not belong to sub %s", jti, user_id)
            raise revoked

        expires_at = _parse_iso((row.get("details") or {}).get("expires_at"))
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            # Belt and braces: the JWT's own `exp` is the primary gate and jose
            # already enforced it. Checking the row too means shortening a key's
            # life by editing its row takes effect without reissuing the token.
            raise revoked
        return

    # Legacy (kind 2). No row exists and none is required — this is the
    # compatibility decision: every key minted before the hardening migration
    # keeps working exactly as it did. The only thing that can kill one is a
    # tombstone.
    name = claims.get(NAME_CLAIM)
    if name and user_id and legacy_key_revoked(user_id, name):
        raise revoked


def row_scopes(claims: Dict[str, Any]) -> Optional[List[str]]:
    """Scopes as the credentials row states them, or None if there is no row."""
    jti = claims.get("jti")
    if not jti:
        return None
    row = lookup_api_token(jti)
    if row is None:
        return None
    return normalize_scopes((row.get("details") or {}).get("scopes"))


def effective_scopes(claims: Dict[str, Any]) -> Optional[List[str]]:
    """The scopes actually in force for a verified token.

    The row wins when it has scopes, so narrowing a key takes effect without
    reissuing it. Our own mint path writes both sides identically, so they only
    diverge if somebody edits the row — which is the point.
    """
    version = claims.get(VERSION_CLAIM)
    if isinstance(version, int) and version >= TOKEN_VERSION:
        from_row = row_scopes(claims)
        if from_row is not None:
            return from_row
    return normalize_scopes(claims.get(SCOPES_CLAIM))


def scopes_for_token(token: str) -> Optional[List[str]]:
    """Scopes in force for a raw bearer token, or None for unrestricted.

    Deliberately only inspects HS256 tokens. An Auth0 RS256 token is a human
    dashboard session, carries no scopes claim, and — crucially — re-verifying
    one costs a network fetch of Auth0's JWKS (`auth.verify_token`). Peeking at
    the header first keeps this dependency free of network IO.

    An unverifiable token returns None rather than raising: `get_current_user`
    is what turns a bad token into a 401, and a 403 from here would mask it with
    a worse error.
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return None

    if header.get("alg") != "HS256":
        return None

    # Local import: `auth` imports this module lazily (see verify_api_token), so
    # importing it at module level here would be a cycle in the other direction.
    from .auth import verify_api_token

    try:
        claims = verify_api_token(token)
    except AuthError:
        return None

    return effective_scopes(claims)


# --------------------------------------------------------------------------
# Scope enforcement
# --------------------------------------------------------------------------


def require_scope(scope: str):
    """Dependency factory: `Depends(require_scope("studies:write"))`.

    Note this re-verifies the token that `get_current_user` already verified.
    For an API key that is an HS256 decode plus a cache hit — microseconds — and
    the alternative is threading state through `deps.py`, which is shared with
    other route modules. For an Auth0 token it does nothing at all.
    """

    async def _require(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> None:
        scopes = scopes_for_token(credentials.credentials)
        if not scopes_allow(scopes, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This API key is not scoped for {scope}",
            )

    return _require


async def scope_enforcement_middleware(request: Request, call_next):
    """Deny scoped keys on routes their scopes do not cover.

    Why a middleware and not a dependency on every route: a dependency has to be
    added to each route to have any effect, so a route added without one is
    silently reachable by every scoped key. This is fail-closed instead —
    an unclassified path (`required_scope` returns None) is DENIED for scoped
    keys. Unscoped keys and Auth0 sessions are unaffected either way, so a new
    route is never broken for existing callers, only for scoped ones, which is
    the direction a mistake should point.

    Mount it INSIDE the CORS middleware (i.e. add it to the app before
    `add_middleware(CORSMiddleware, ...)`), so that a 403 from here still gets
    CORS headers. Starlette runs the last-added middleware outermost.
    """
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("authorization") or ""
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return await call_next(request)

    scopes = scopes_for_token(token)
    if not is_authorized(scopes, request.method, request.url.path):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": (
                    "This API key is not scoped for "
                    f"{required_scope(request.method, request.url.path) or request.url.path}"
                )
            },
        )

    return await call_next(request)


def add_scope_enforcement(app) -> None:
    """One-line wiring for `server.py`. See `scope_enforcement_middleware`."""
    app.middleware("http")(scope_enforcement_middleware)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


class CreateApiKeyRequest(BaseModel):
    name: str

    # Both optional, and both default to today's behaviour widened only by the
    # TTL: an unscoped key with a bounded life. A caller that passes neither
    # gets exactly the key the dashboard has always asked for, except that it
    # now expires.
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = Field(
        default=None, ge=1, le=MAX_API_TOKEN_TTL_DAYS
    )


class CreateApiKeyResponseData(BaseModel):
    # name/id/token are the shape `dashboard/src/helpers/api.ts:292` already
    # consumes and MUST NOT change. scopes/expires_at are additive.
    name: str
    id: str
    token: str
    scopes: Optional[List[str]] = None
    expires_at: Optional[str] = None


class CreateApiKeyResponse(BaseModel):
    data: CreateApiKeyResponseData


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    scopes: Optional[List[str]] = None
    created: Optional[datetime] = None
    expires_at: Optional[str] = None
    expired: bool = False


class LegacyRevocationInfo(BaseModel):
    name: str
    created: Optional[datetime] = None


class ListApiKeysResponseData(BaseModel):
    keys: List[ApiKeyInfo]
    legacy_revocations: List[LegacyRevocationInfo]


class ListApiKeysResponse(BaseModel):
    data: ListApiKeysResponseData


class RevokeLegacyKeyRequest(BaseModel):
    name: str


@router.post("/users/api-key", status_code=201)
async def create_api_key(
    key_request: CreateApiKeyRequest,
    user: Annotated[User, Depends(get_current_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CreateApiKeyResponse:
    """Mint a key. Response shape is unchanged from the pre-hardening endpoint."""
    name = key_request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be blank")
    if len(name) > 200:
        raise HTTPException(
            status_code=400, detail="name must be 200 characters or fewer"
        )

    scopes = validate_scopes(key_request.scopes)

    # Attenuation, checked here rather than in the middleware because the
    # middleware only sees the path. A `studies:write` key reaching this route
    # at all already means somebody granted `auth:write` deliberately; this is
    # what stops that key from minting itself a wider one.
    caller_scopes = scopes_for_token(credentials.credentials)
    if not scopes_allow(caller_scopes, "auth:write"):
        raise HTTPException(
            status_code=403, detail="This API key is not scoped for auth:write"
        )
    if not can_grant_scopes(caller_scopes, scopes):
        raise HTTPException(
            status_code=403,
            detail="Cannot mint a key with more scopes than the key minting it",
        )

    ttl_days = key_request.expires_in_days or API_TOKEN_TTL_DAYS
    # The clock is passed in rather than taken twice, so the `expires_at` in the
    # response is byte-identical to the one in the row and in the token's `exp`.
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(days=ttl_days)

    try:
        token, jti = generate_api_token(
            user_id=user.user_id,
            name=name,
            scopes=scopes,
            ttl_days=ttl_days,
            issued_at=issued_at,
        )
    except psycopg.errors.UniqueViolation:
        # unique_entity_key_per_user. Surfaced rather than swallowed: silently
        # returning a second live key with the same name would make the list
        # endpoint ambiguous and revocation-by-name meaningless.
        raise HTTPException(
            status_code=409, detail=f"An API key named '{name}' already exists"
        )

    return CreateApiKeyResponse(
        data=CreateApiKeyResponseData(
            name=name,
            id=jti,
            token=token,
            scopes=scopes,
            expires_at=expires_at.isoformat(),
        )
    )


@router.get("/users/api-keys")
async def list_api_keys(
    user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_scope("auth:read"))] = None,
) -> ListApiKeysResponse:
    """List this user's live keys.

    Legacy (pre-hardening) keys are NOT here and cannot be: nothing was ever
    persisted for them, so the server does not know they exist. `legacy_revocations`
    is the one thing that can be shown about them — the names this user has
    tombstoned.
    """
    now = datetime.now(timezone.utc)
    keys = []
    for row in _select_api_token_rows(user.user_id):
        details = row.get("details") or {}
        expires_at = _parse_iso(details.get("expires_at"))
        keys.append(
            ApiKeyInfo(
                id=str(details.get("jti") or ""),
                name=row["key"],
                scopes=normalize_scopes(details.get("scopes")),
                created=row.get("created"),
                expires_at=details.get("expires_at"),
                expired=expires_at is not None and expires_at <= now,
            )
        )

    revocations = [
        LegacyRevocationInfo(name=r["key"], created=r.get("created"))
        for r in _select_revocation_rows(user.user_id)
    ]

    return ListApiKeysResponse(
        data=ListApiKeysResponseData(keys=keys, legacy_revocations=revocations)
    )


@router.delete("/users/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_scope("auth:write"))] = None,
):
    """Revoke a key by its id (the `jti`). Deleting the row IS the revocation."""
    name = _delete_api_token_row(user.user_id, key_id)
    if name is None:
        # 404 rather than 403 on somebody else's key id, so this never confirms
        # that another user's key exists.
        raise HTTPException(status_code=404, detail="No such API key")

    # Local eviction only. Other replicas keep serving this key until their own
    # cache entry ages out — up to CACHE_TTL_SECONDS. That window is the price
    # of negative caching and is stated here so nobody has to infer it.
    _cache.delete(_jti_cache_key(key_id))

    # Explicit empty response: a 204 must not carry a body, and returning None
    # would have FastAPI serialise `null` into one.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/api-keys/legacy-revocations", status_code=201)
async def revoke_legacy_api_key(
    request: RevokeLegacyKeyRequest,
    user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_scope("auth:write"))] = None,
) -> LegacyRevocationInfo:
    """Tombstone every pre-hardening key of this user with the given name.

    The escape hatch for a leaked key minted before the hardening migration.
    Coarse by construction — see `legacy_key_revoked`. There is deliberately no
    endpoint to remove a tombstone: un-revoking a key you have already declared
    leaked is not an operation worth making one request away.
    """
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be blank")

    _insert_revocation_row(user.user_id, name)
    _cache.delete(_revoked_cache_key(user.user_id, name))
    return LegacyRevocationInfo(name=name, created=datetime.now(timezone.utc))
