# API key hardening

Implementation notes for the auth half of Phase 0 in
`planning/agent-study-authoring.md` §8. Written alongside the code; the code
comments carry the reasoning at the call site, this file carries the parts that
have no single call site — the compatibility decision, the corrections to the
plan document, and the operational consequences.

Status: **implemented and tested locally**, not deployed. Not wired into
`server.py` (that is a separate change; see "Wiring" below).

## What exists now

| Piece | Where |
|---|---|
| `api_token_jti` computed column + partial unique index | `devops/migrations/20260904000000_api_token_hardening.up.sql`, `…000001_api_token_hardening_jti_index.up.sql` |
| Mint (persists the row), verify, scope model, cache, routes | `adopt/adopt/server/api_keys.py` |
| Claims, TTL, the version discriminator, the verifier hook | `adopt/adopt/server/auth.py` |
| Tests (32) | `adopt/adopt/server/test_api_keys.py` |

Endpoints: `POST /users/api-key` (shape unchanged from the pre-hardening one),
`GET /users/api-keys`, `DELETE /users/api-keys/{jti}`,
`POST /users/api-keys/legacy-revocations`.

## Three corrections to `agent-study-authoring.md` Appendix A.4

1. **"vlab's `credentials` table already does this for `facebook_page_id`" is
   false.** There is no computed column anywhere in vlab's migrations. That
   precedent is in *fly's* `credentials`/`media`/`message_templates`. The
   pattern had to be created here from scratch — it does work on CockroachDB
   v24.1.28, verified, and the verifier's lookup is an index-only seek.

2. **The computed column cannot be created in the same migration as its
   index.** golang-migrate runs each file in one transaction, and CockroachDB
   refuses to index a column that is still non-public inside the transaction
   that added it:

   ```
   pq: cannot create partial index on column "api_token_jti" (8) which is not public
   ```

   Hence two migration files for one logical change. This is the only reason
   they are split.

3. **jti-presence cannot be the legacy discriminator in vlab, though it is in
   fly.** A.4 describes fly's model accurately — "legacy keys carry no `jti`" —
   and that sentence is simply not true of vlab. `generate_api_token` has always
   minted a `jti`; it just threw it away instead of storing it. So *every* key in
   production carries a `jti` with no row behind it, and "requires a row iff it
   has a jti" would revoke every key in existence on deploy.

   A.4's other claim about `exp` — that vlab, unlike fly, has no internal
   services sharing `API_KEY_SECRET` — **is** true. Verified by grep: the secret
   is read only in `adopt/adopt/server/auth.py`, and nothing else in the repo
   signs with it. New keys therefore carry a mandatory `exp` (90 days by
   default, `expires_in_days` overridable up to 365).

## The compatibility decision

An explicit `https://vlab.digital/token-version: 2` claim, written only by the
new mint path, is the discriminator.

- **version >= 2** → a live `credentials` row keyed by `jti` is required, `exp`
  is required, scopes are honoured. Revocation is a row delete.
- **claim absent (legacy)** → accepted with no row, no expiry, unrestricted —
  byte-for-byte today's behaviour. Nobody's key breaks.

A legacy token cannot forge its way across that line: the claim is inside the
signature.

The cost is honest and worth stating plainly: **existing keys stay eternal and
unscoped until they are reissued.** The only lever over them is a tombstone row
(`entity = 'api_token_revoked'`, `key = <token name>`) matched against the
token-name claim. That is a denylist, and it is coarse — names were never unique
before this migration, because nothing was stored to make them unique, so a user
with two legacy keys called "agent" tombstones both or neither. It errs towards
denying, which is the right direction for a leak, and it is the entire reason
`jti` exists for keys minted from now on.

**The migration path for a researcher is: list your keys, notice the old ones
are not listed at all (nothing was ever persisted for them), and reissue.**

## Scopes

`<resource>:<action>`; `write` implies `read`; `*` is unrestricted; an **absent**
scopes claim is unrestricted; an **empty list** denies everything.

Resources: `studies`, `responses`, `stats`, `optimize`, `auth`.

`studies` and `responses` are distinct as the plan requires — study
configuration is the researcher's own work, ad-attributions are a
respondent-level record. `stats` is aggregate-only. `optimize` is separate
because an instruction spends money on Meta. `auth` is never implicitly granted,
and minting is attenuating: a key can only mint a key no more powerful than
itself, with "no scopes requested" read as a request for full access rather than
for nothing.

### Why enforcement is a middleware and not per-route dependencies

fly maps `/api/v1/<resource>` — the first path segment *is* the resource. vlab's
first segment is an `org_id`, so the resource lives at segment 2 and, under
`studies`, at the segment after the slug. `required_scope` encodes that.

A per-route `Depends(require_scope(...))` was rejected as the primary mechanism
because a route added without one is silently reachable by every scoped key. The
middleware is fail-closed instead: a path `required_scope` does not classify is
**denied** for scoped keys. Unscoped keys and Auth0 sessions are unaffected, so
a newly added route can only break for scoped callers — the direction a mistake
should point. `require_scope` still exists and guards the key-management routes
themselves, so the router is safe even if the middleware is never installed.

## Operational consequences

- **Revocation is "dead within 30 seconds", not instant.** Lookups are cached
  in-process for 30s including negative results. Negative caching is the point —
  replaying random jtis must not become one database read per request — and the
  latency is the price. The revoking replica evicts locally; the others wait out
  the TTL.
- **Down-migrating is an outage for agent keys**, not a no-op: with no jti
  column the verifier cannot find a row for a v2 token. Legacy keys are
  unaffected. The rows themselves survive, so re-running the up migration
  restores everything.
- **`devops/helm/migrations/init.sql` was not updated.** It looks stale (it
  declares `users.id` as UUID where the live schema is VARCHAR, and has no
  `org_id` anywhere), and the golang-migrate chain is the live path. Worth a
  separate decision about whether that file should exist at all.

## Wiring (not done here)

`server.py` still carries the pre-hardening inline `POST /users/api-key`. It
keeps working — `generate_api_token` now persists the row itself, deliberately,
so that minting and persisting cannot come apart — but it offers no scopes, no
listing and no revocation. To switch over:

1. Delete `CreateApiKeyRequest`, `CreateApiKeyResponseData`,
   `CreateApiKeyResponse` and the `@app.post("/users/api-key")` handler.
2. Drop `generate_api_token` from the `from .auth import …` line.
3. `from .api_keys import router as api_keys_router, add_scope_enforcement`
4. `add_scope_enforcement(app)` **before** `app.add_middleware(CORSMiddleware, …)`,
   so CORS stays outermost and a 403 still carries CORS headers.
5. `app.include_router(api_keys_router)`

Turning scope enforcement on for real also means every route added later must be
classified in `required_scope`, or it becomes unreachable for scoped keys.
