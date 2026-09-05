# Letting an agent create studies

Exploration and decision path for giving an AI agent (or a script, or a
notebook) the ability to create and configure a vlab study without driving the
React dashboard by hand.

Status: **Phase 0 deployed (adopt v0.1.83); Phases 1 and 2 implemented and
merged, releasing as adopt v0.1.84; Phases 3–4 not started.** §1–§5 are
findings read out of the code, with the file establishing each claim named
next to it. §7 records the decisions taken and why, §8 is the plan, §10 is
what is still open, and **§11 (Phase 0), §12 (Phase 1) and §13 (Phase 2)
record what actually shipped and the claims the implementations proved
wrong** — several of them load-bearing, so read those before trusting a
detail in §2, §8 or Appendix A.

The short version: an SDK (pipx-installable, shipped as an extra on `adopt`)
that owns a *composable* study-authoring library and validates a whole study
locally before writing anything; a server that stays a dumb writer plus a
validator and proxies Meta; the dashboard keeping its TypeScript compiler under
a conformance test; MCP later, as a shim over the SDK rather than a second
implementation of it.

---

## 1. The finding that should shape the decision

The wire API is not the bottleneck. Every configuration section already has a
create endpoint, and those endpoints already accept API keys. An agent can
authenticate and POST JSON today.

What it cannot do is **decide what JSON to POST**, because the logic that turns
a researcher's intent into a valid study configuration does not live behind the
API. It lives in the browser, in TypeScript, in the dashboard's form
components. `POST /confs/strata` is a dumb writer: it takes the strata you
already computed and stores them. Computing them is
`createStrataFromVariables` in
`dashboard/src/pages/StudyConfPage/forms/strata/strata.ts:53`, which runs in
React and is reachable from nowhere else.

So the real question is not "REST, MCP, or SDK?" — that is packaging. The
question is **where the study compiler lives**, and the answer to that
determines the packaging almost by itself.

---

## 2. The terrain as it actually is

### 2.1 Two services, not one

The dashboard talks to two different backends, and the split is not the one the
directory names suggest.

| | `api/` (Go) | `adopt/adopt/server/` (Python, FastAPI) |
|---|---|---|
| Deployed as | `vlab-dashboard-api.toixo.vlab.digital` | `vlab-study-conf-api.toixo.vlab.digital` |
| Helm service | `dashboard` | `conf-dashboard` (image: `ghcr.io/vlab-research/adopt`) |
| Owns | studies (create/list/read), users, orgs, accounts/credentials, Facebook OAuth token exchange, segments progress | **all study configuration**, optimize, instructions, errors, ad attributions, recruitment stats, API-key minting |
| Auth | Auth0 RS256 **only** | Auth0 RS256 **or** vlab API key (HS256) |

Both hosts are in `devops/values/toixo-prod.yaml`. The dashboard picks between
them per call via `baseURL: process.env.REACT_APP_CONF_SERVER_URL`
(`dashboard/src/helpers/api.ts`).

**The Go API's own study-conf endpoints are dead.** `api/internal/server/server.go`
registers `POST/GET /:org/studies/:slug/conf`, and
`api/internal/types/studyconf.go` carries a full 345-line set of conf structs —
but the dashboard writes every conf to the Python service instead. The only Go
conf caller left in the dashboard is `deleteDestination`
(`dashboard/src/helpers/api.ts:210`), which nothing imports. Those Go types have
also drifted out of agreement with the Python ones that are actually enforced
(the Go `CreativeConf` has `ImageHash`/`Body`/`ButtonText`; the live one has
`template`/`template_campaign`). Treat `api/internal/types/studyconf.go` as
stale, not as a specification.

### 2.2 API keys already exist — and are weaker than they look

`adopt/adopt/server/auth.py` already implements the whole thing:

- `POST /users/api-key` mints an HS256 JWT (`generate_api_token`, line 21).
- `verify_tokens` (line 157) tries Auth0 RS256 first and falls back to the
  HS256 API-key verifier, so **every** endpoint on the Python service accepts
  an API key with no per-route work.
- The dashboard already has a UI for it (`generateApiKey`,
  `dashboard/src/helpers/api.ts:292`).
- Deployed via the `vlab-api-key-envs` secret (`devops/values/toixo-prod.yaml`).

What it lacks, all of it visible in `generate_api_token`:

- **No expiry.** The payload has `iat` but no `exp`. Keys are eternal.
- **No revocation.** A `jti` is generated and put in the token — and then
  thrown away. Nothing is persisted, so nothing can be checked. There is a
  `# TODO: check payload ("id") against blacklist / whitelist` at
  `auth.py:62` marking exactly this.
- **No scopes.** A key is the user, entire. An agent key can read every
  respondent's answers and mutate every study the user owns.
- **No listing.** The user cannot see which keys exist.

This is the same set of holes fly closed in
`fly:899443fe` — see §5.

### 2.3 An API key cannot create a study

Study creation is `POST /:org/studies` on the **Go** service
(`api/internal/server/handler/studies/create.go`), which is Auth0-only. The
Python service can write configuration for a study but has no way to bring one
into existence: `create_study_conf` (`adopt/adopt/server/db.py:151`) inserts
with a subselect against `studies` and simply writes nothing if the study is
absent. (Corrected in §11.3: it does not write nothing — the subselect yields
NULL into a NOT NULL column, so it raises `NotNullViolation` and the caller
gets a 500. Same consequence, louder.)

So today an agent holding an API key must have a human create the study in the
dashboard first. That is the single hardest blocker, and it is a small fix.

### 2.4 The compiler lives in the browser

This is §1 restated concretely. Three pieces of real authoring logic exist only
as dashboard TypeScript:

1. **Strata generation.**
   `dashboard/src/pages/StudyConfPage/forms/strata/strata.ts` — cartesian
   product over variable levels, quota as the product of level quotas, merged
   `facebook_targeting`, per-stratum `metadata`, and a `question_targeting`
   predicate that ANDs each level equality with an `answered` filter on the
   study's finish question. Plus `strataStalenessHint`, which detects when
   saved strata no longer match the variables that produced them.

2. **Targeting extraction from template ad sets.**
   `dashboard/src/pages/StudyConfPage/forms/variables/extract.ts` —
   `extractFromAdset` pulls the declared properties off a Meta ad set, throws
   `PropertyMissingError` when one is absent, and unconditionally forces
   `targeting_automation: {advantage_audience: 0}`. That last line is a
   deliberate policy decision with a real-world failure behind it (Advantage
   audience expansion leaking delivery outside a geographic stratum).

3. **Creative template extraction.** The Creatives form reads the creative blob
   off a template ad through the Meta Graph API **from the browser**, using the
   researcher's stored Facebook token
   (`dashboard/src/pages/StudyConfPage/forms/creatives/Creatives.tsx:79`,
   `facebookRequest` in `dashboard/src/helpers/api.ts:412`). The backend never
   sees Facebook here.

An agent hitting REST directly must reimplement all three, including talking to
the Meta Graph API itself. That is not a documentation problem.

### 2.5 What the server *does* validate

`adopt/adopt/study_conf.py` (1292 lines) is the real schema, in pydantic v2,
and it is genuinely good. Per-section models (`GeneralConf`, `CreativeConf`,
`StratumConf`, the `DestinationConf` discriminated union, the three-way
`RecruitmentConf` union) plus cross-section validators on `StudyConf` itself —
e.g. `check_whatsapp_refs_are_deliverable` (line 1111), which refuses metadata
that would not survive fly's entry regex once percent-encoded.

The catch: **that assembly never happens at write time.** Each `POST
/confs/<type>` validates one section in isolation
(`adopt/adopt/server/server.py:135-227`). The whole `StudyConf` is only
constructed later, by `load_basics` on the optimize path. Cross-section
failures therefore surface hours later in a cron, not at the moment the agent
wrote the bad config. Two of the checks are not even errors — they are
`logging.warning` calls that reach nobody
(`warn_on_incomplete_targeting`, `warn_on_thinned_ref_without_mapping`, in
`adopt/adopt/malaria.py`).

For an agent this is the worst possible shape: writes succeed, and the study is
broken.

### 2.6 One genuinely good affordance already in place

`GET /{org}/optimize/{slug}` computes the full instruction list and **returns it
without executing** — `run_study_opt` (`adopt/adopt/server/server.py:306`)
discards the second half of `update_ads_for_campaign`'s return, and the actual
execution path is the cron's `run_updates` → `run_instructions`
(`adopt/adopt/malaria.py:520`). `POST /{org}/optimize/{slug}/instruction`
then executes exactly one.

That is plan / review / apply, already built. It is the right shape for an
agent and should be the centrepiece of the launch story, not an afterthought.
(Caveat for the docs: the "preview" is not side-effect-free — it calls
`heal_ad_attributions` and reads Meta. It also *writes*: an `adopt_reports`
FACEBOOK_ADOPT row, a respondents-over-time report and a cost-over-time report
— see §11.3. "Preview" is a worse name for it than this section implies.)

---

## 3. What blocks an agent today, in order of severity

1. **No study creation with an API key** (§2.3). Hard blocker; small fix.
2. **No study compiler outside the browser** (§2.4). The agent can write
   configuration but cannot derive it.
3. **No whole-study validation at write time** (§2.5). Failures are deferred to
   a cron.
4. **No Meta Graph access path** (§2.4.2, §2.4.3). Template campaigns, ad sets,
   and creative blobs are read client-side with the researcher's token.
5. **API keys are unbounded and irrevocable** (§2.2). Handing one to an agent
   is handing over the account, permanently.
6. **No agent-facing documentation.** `docs.vlab.digital` documents the
   *concepts* well (`content/vlab/study-configuration/` has a page per conf
   type) but documents the dashboard's UI, not a wire format or a
   programmatic workflow. There is no OpenAPI artifact and no committed JSON
   Schema, though pydantic can emit the latter for free.

---

## 4. Prior art in this repo: the notebook era

Before the dashboard, studies were built in Python notebooks that imported
`adopt` directly. `~/Documents/vlab-research/campaigns/` still holds ~40 of
them — `*-make-strata.ipynb`, one per study — and symlinks `adopt ->
../vlab/adopt/adopt`.

The library they used is still here and still tested:

- `adopt/adopt/campaign_queries.py:66` `create_campaign_for_user` — creates a
  study row.
- `adopt/adopt/campaign_queries.py:117` `create_campaign_confs` — writes a conf.
- `adopt/adopt/configuration.py` — the authoring helpers:
  `format_group_product` (line 101), `location_levels`, `read_share_lookup`,
  `parse_row_sheet`. This is the **ancestor of the dashboard's
  `formatGroupProduct`**, same name, same job.

Two things matter about this.

**It is unused by the server.** Nothing under `adopt/` imports
`configuration.py` outside its own test. It is a preserved authoring library,
not part of any running path.

**It has drifted from the TypeScript that replaced it, and they now disagree.**
Given the same variables, the Python and TS compilers emit different strata:

| | `configuration.py:101` (Python) | `strata.ts:8` (TypeScript) |
|---|---|---|
| metadata key | `stratum_<variable>` | `<variable>` |
| targeting variable ref | `md:stratum_<variable>` | `<variable>` |
| quota | from an Excel `share_lookup` | product of level quotas |
| targeting source | `params` on the group | `facebook_targeting` extracted from the template ad set |

The TypeScript one is what production studies are built with. **Any plan that
"just reuses the Python" is reusing the wrong implementation.** The Python is
excellent raw material and a proven ergonomic model; it is not a shortcut past
porting `strata.ts`.

---

## 5. The fly precedent, and how far it carries

`fly` (branch `feature/mcp-server`) did this three days ago:

- `899443fe` — hardened API keys (jti tied to a credentials row so revocation
  is real and name reuse cannot resurrect a token; 90-day expiry;
  `<resource>:<action>` scopes where absent scopes stay unrestricted for
  backwards compatibility) and mounted an MCP endpoint at `POST /api/v1/mcp`
  inside the existing JWT middleware. Streamable HTTP, stateless. `/mcp` is
  marked *delegated* — path-based scoping cannot work when one POST reaches
  every tool and the tool name is in the body — so `TOOL_SCOPES` in
  `mcp.tools.js` is the real check.
- `00ce7165` — `documentation/agent-api.md`, 716 lines written for an agent
  reader, which found three real bugs in the writing.
- `90cdce61` — collapsed the MCP and REST implementations into one service
  function after review caught the duplication.

**What transfers directly:**

- The auth model. jti-in-a-row revocation, bounded TTL, `<resource>:<action>`
  scopes with absent-means-unrestricted, per-tool scope enforcement for a
  delegated MCP route. vlab needs all of it and has none of it. The migration
  (`fly:devops/migrations/32-api-token-hardening.sql`) is a readable template,
  and vlab's `credentials` table is shaped similarly enough to take the same
  approach.
- The documentation form. `agent-api.md`'s structure — mental model first,
  then endpoints, then a runbook, then an explicit **Known gaps** section
  marking what could not be determined rather than guessing — is the right
  template. Its §1 ("There is no update endpoint. `POST` is the update") is
  precisely the kind of thing vlab needs to say about append-only
  `study_confs`.
- The insistence that tool descriptions are the product surface and belong in
  a pure, testable core.

**What does not transfer:** the shape of the thing.

fly's five tools are thin. `create_survey` is `POST /surveys` with defaults
filled in. There is a genuine mental model to teach (append-only versioning)
but almost no *computation* between what the researcher wants and what the API
stores.

vlab is the opposite. Nine conf types with cross-references (creatives name
destinations; strata name creatives and audiences), a cartesian-product
compiler, Meta Graph reads to fill in targeting and creative blobs, and
whole-study invariants that no single write can check. A five-tool MCP shim
over the existing REST endpoints would let an agent write nine sections of
JSON and would not help it write nine *correct, mutually consistent* sections.
That is the "much more complicated" this repo is.

---

## 6. Options considered

### A. MCP server over the existing REST endpoints
A vlab equivalent of fly's `api/mcp/`, mounted on the FastAPI service.

- **For:** matches the fly precedent; MCP clients connect with no install;
  auth is already solved on that service.
- **Against:** does nothing about §3.2 or §3.3 — the agent still has to invent
  strata and still gets no whole-study check. Every iteration is a network
  round trip.
- **Verdict:** wanted eventually, insufficient alone.

### B. Python SDK + CLI, installed with pipx — **chosen**
A distributable package exposing the pydantic models, a *composable* authoring
library, a local validator, and a `vlab` CLI that pushes over HTTP with an API
key.

- **For:** the models are already Python and are the enforced schema.
  Cross-section validation is just constructing `StudyConf` — locally,
  instantly, with no round trip and no half-written study. Restores the
  notebook workflow. An agent gets a tight `edit → validate → diff → plan →
  apply` loop.
- **Against:** requires an install. Does not, by itself, speak MCP.

### C. SDK core + thin MCP shim over it
B, then A as a wrapper: the MCP tools call the same library the CLI calls.
fly's `90cdce61` is the lesson — it had to be refactored precisely because MCP
was written as a second implementation.

### D. Server-side "compile study" endpoint — **rejected**
Move the compiler into FastAPI: `POST /{org}/studies/{slug}/compile/strata`
derives and writes the derived sections; the dashboard calls it too and deletes
its TypeScript copy.

Rejected, and the reason is the point of the whole project: **the SDK should be
able to do more than the dashboard, not the same thing over HTTP.** A compile
endpoint enshrines the dashboard's single opinion — a cartesian product over
variable levels, quota as the product of level quotas. That is one way to build
strata, not the way. The notebooks in `campaigns/` are the existence proof:
`upswell-generic-geo.ipynb` builds custom lat/lng radius targeting per district
out of a spreadsheet, `read_share_lookup` drives quotas from an Excel tab,
`location_levels` composes geographic levels the Variables form cannot express
at all. Those are exactly the "fancy combinations" a researcher or an agent
should be able to write — and a server endpoint that owns the derivation
forecloses them.

So the server stays a dumb writer plus a validator, and the composition happens
where the caller is.

---

## 7. Decisions taken

| Decision | Choice | Rationale |
|---|---|---|
| Shape | **B → C**: SDK first, thin MCP shim later | The SDK must be more expressive than the dashboard (§6.D). MCP is a front door onto it, never a second implementation. |
| Packaging | **SDK as an extra on `adopt`** | `adopt` already has `[tool.poetry.scripts]`; no extraction work. Accepts that pipx pulls pandas/scipy/cvxpy — revisit only if it actually hurts. |
| Meta access | **Server proxies Meta** | Campaigns, ad sets and creative blobs get read server-side with the stored credential. Works for a pure-MCP client with no install, and keeps the researcher's Facebook token off the agent's machine. |
| Dashboard compiler | **Keep the TypeScript, conformance-test it** | Cutting the dashboard over is real front-end work on a live regenerate/staleness UI, and buys nothing the agent needs. A shared fixture suite asserting Python ≡ TypeScript is enough to stop the §4 drift. |
| Study creation | **Port to FastAPI, deprecate the Go endpoint** | Closes §2.3 and starts the retirement of a service whose conf half is already dead code with drifted types. |

---

## 8. The plan

**Phase 0 — unblock and secure.** Small, independently valuable, no design risk.

- **Port study creation to FastAPI.** `POST /{org}/studies` on the Python
  service, so an API key can create a study. Mark the Go handler
  (`api/internal/server/handler/studies/create.go`) deprecated and point the
  dashboard at the new one. The Go service's conf endpoints are already dead
  (§2.1); this is the first deliberate step of retiring the rest.
- **Harden API keys** along fly's lines: persist the `jti` as a credentials row
  so revocation is real and name reuse cannot resurrect a token; add a bounded
  TTL; add `<resource>:<action>` scopes with absent-means-unrestricted so no
  existing key breaks; add list and revoke endpoints.
  `fly:devops/migrations/32-api-token-hardening.sql` is the template.
  Keep `studies` and `responses` as distinct resources, so a key can read study
  structure without reading respondents' answers.
- **Expose the pydantic JSON Schemas** (`model_json_schema()`) as a committed
  artifact or an endpoint. Free, and every downstream consumer wants it.

**Phase 1 — the compiler, in Python, once.**

Port `strata.ts` and `extract.ts` into `adopt` as pure functions. Carry
`strata.spec.ts` and `extract.test.ts` over as the conformance suite —
translated, not paraphrased — plus a shared fixture set asserting the Python
and TypeScript produce identical output, so the drift of §4 cannot recur
silently. Retire or clearly mark `configuration.py` as the superseded ancestor,
salvaging the pieces worth keeping (`location_levels`, `read_share_lookup`,
`parse_row_sheet`) into the new library rather than deleting them — they are
the composability the SDK is for.

**Phase 2 — Meta proxy endpoints.**

`GET /{org}/meta/adaccounts`, `/campaigns`, `/adsets`, `/ads` on the FastAPI
service, reading with the study owner's stored credential. This is a
straight lift of what `facebookRequest` does client-side today
(`dashboard/src/helpers/api.ts:412`). Scope them under a `meta:read` resource.

**Phase 3 — the SDK.**

Package the models, the authoring library, the validator and an HTTP client as
an extra on `adopt`, with a `vlab` CLI:

- `vlab validate` — local, whole-study, including the two invariants that today
  only reach a log file
- `vlab push` / `vlab diff`
- `vlab plan` — the optimize preview (§2.6)
- `vlab apply` — one instruction

The authoring library is composable primitives, not one blessed pipeline: the
dashboard's cartesian product is *a* helper in it, sitting alongside the
geo/share-lookup helpers, and a caller can bypass all of them and hand-build
strata that the validator still checks.

Also add `POST /{org}/studies/{slug}/validate` to the server — whole-study
assembly, errors and warnings, writes nothing. The SDK does not need it, but
MCP clients and the dashboard do, and it is the same pydantic construction.

**Phase 4 — MCP.**

A shim over the SDK on the FastAPI service, with per-tool scopes (fly's
delegated-route model: `/mcp` admits any authenticated key, a `TOOL_SCOPES`
table is the real check). Tools should be the *smart* operations —
`compile_strata`, `validate_study`, `plan_study` — not one write tool per conf
type.

**Documentation, running alongside from Phase 0.**

- `documentation/agent-api.md` in this repo, in the shape of fly's, including
  its **Known gaps** discipline — what could not be determined is marked, not
  guessed. Written for an agent reader, with an end-to-end runbook from API key
  to first ad.
- Keep `docs.vlab.digital`'s `content/vlab/study-configuration/` as the
  conceptual layer and cross-link, rather than duplicating it.
- MCP tool descriptions carry the mental model — append-only confs, the
  reference graph, what "regenerate strata" means — and are code: tested and
  diffed as such.

---

## 9. Why this order

Phase 0 is worth doing whatever else happens: every path needs an API key that
can create a study and that can be taken back. Phase 1 is the genuinely hard
part and is required by every consumer, so doing it early means the rest is
packaging. Phases 2 and 3 can overlap. Phase 4 is small if Phase 3 is done
right, and large if it is not.

---

## 10. Still open

- **How much of `configuration.py` is worth salvaging.** Needs a read-through
  against real notebook usage in `campaigns/` to separate the still-useful
  composition helpers from the parts that only made sense pre-dashboard.
- **Whether the Go service gets fully retired**, and on what timeline. Phase 0
  starts it; nothing here finishes it. Segments-progress, accounts/credentials
  and the Facebook OAuth exchange still live there.
- **Whether `POST /validate` should also run the Meta-dependent checks**
  (does the template ad set still exist? does it still carry the declared
  properties?). That turns validation into a network call and a slow one, so it
  may want to be a separate `vlab check --live`.


---

## 11. Phase 0: what shipped, and what it proved wrong

Implemented 2026-09-04 on `feature/agent-study-authoring-phase0`. This section
supersedes conflicting details in §2 and Appendix A; where they disagree, this
section was verified against running code and they were not.

### 11.1 What shipped

| Commit | What |
|---|---|
| `83733d5d` | `server/deps.py` — auth dependency extracted so route modules do not have to import `server` |
| `f75100ec` | `VLAB_TEST_PG_URL` — fixtures can point at another database, so concurrent test runs stop truncating each other |
| `489bc680` | `adopt/schemas/*.json` — committed JSON Schemas, `make check-schemas`, own CI job |
| `32980fe8` | `POST /{org_id}/studies` — study creation with an API key; `slugify.py` |
| `9e924444` | `documentation/agent-api.md` — 1077 lines written for an agent reader |
| `70248ea1` | API keys: `exp`, jti-backed revocation, scopes, list/revoke |
| `ee7e21f6` | `copy-from` cross-tenant write fix (found while writing the docs) |

Test suite went from 757 to 829 passing, no regressions. Phase 0's three
planned items are all done; the dashboard was deliberately **not** repointed at
the new study-creation endpoint (the Go one works, and repointing live UI buys
the agent nothing), so `api/.../studies/create.go` carries a deprecation
comment and nothing more.

### 11.2 The API-key correction that would have been an outage

**Appendix A.4 says legacy keys "carry no `jti`" and proposes fly's
discriminator: require a live credentials row iff the token carries one. That
is true of fly and false of vlab.** `generate_api_token` has *always* minted a
`jti` — it just threw it away (that is precisely what the `# TODO: check
payload ("id") against blacklist / whitelist` marked). So every key in
production carries a `jti` with no row behind it, and fly's rule would have
revoked all of them on deploy.

The shipped discriminator is an explicit `https://vlab.digital/token-version: 2`
claim, written only by the new mint path and unforgeable because it is inside
the signature. Version 2 requires a live row, requires `exp`, honours scopes.
An absent claim is a legacy key: accepted with no row and no expiry, exactly as
before. Legacy keys have no row for positive validity to stand on, so their
only lever is a coarse name-matched tombstone — names were never unique when
nothing was stored. **The real migration path is reissue**, and old keys stay
eternal until someone rotates them.

Two smaller A.4 corrections: the `facebook_page_id` computed-column precedent is
**fly's**, not vlab's — vlab had no such column, and the pattern was created
fresh. And CockroachDB will not accept a partial index on a computed column in
the transaction that added the column, so one logical change is two migration
files.

A.4's `exp` claim was **right**: `API_KEY_SECRET` is read only in `auth.py`,
nothing else in the repo signs with it, so vlab can require `exp` where fly
could not.

### 11.3 Other claims the implementation disproved

- **A.1: the name cap is 300 bytes, not characters.** Go's `len()` on a string
  counts bytes; 151 `ñ` is already rejected by the dashboard today.
- **A.1 understates the slug problem.** It suggests testing "spaces,
  punctuation and non-ASCII". The genuinely non-obvious behaviour is
  `languages_substitution.go`'s `init()`, which merges `defaultSub` into every
  language map — quotes are *deleted*, so `Nandan's study` is `nandans-study`,
  not `nandan-s-study`. Reading `enSub`'s literal, which is what the appendix
  points you at, does not reveal this. The port was verified by running the real
  Go implementation over 254,037 inputs and diffing; the first draft had seven
  mismatches, all from this.
- **§2.3: `create_study_conf` does not silently write nothing.** It raises
  `NotNullViolation` and surfaces as a 500.
- **§2.4 understates how dead `variables` is.** It is not merely that the
  compiler lives in the browser — `StudyConf` has no `variables` field at all
  (`study_conf.py:1071`), so pydantic drops it on read. The *output* of the
  compiler is the only thing that exists server-side.
- **§2.6's preview also writes.** Three `adopt_reports` rows, not just
  `heal_ad_attributions` and Meta reads.

### 11.4 New defects found, not fixed — candidates for Phase 1

Reported by the implementation and verified, but deliberately left alone: they
are design decisions, not mechanical fixes.

1. **`InvalidConfigError` derives from `BaseException`** (`study_conf.py:928`),
   so pydantic does not wrap it and Starlette's exception middleware does not
   catch it. Every careful message in the WhatsApp, multi-destination, audience
   and partitioning validators reaches the server log and never the caller, who
   gets a bare 500. This is the most fixable bug on the list and it directly
   undercuts §2.5's hope that validation errors are actionable.
2. ~~**Every conf model is `extra="ignore"`.**~~ **RESOLVED**, adopt v0.1.85.
   A misspelled *optional* field was accepted and silently dropped — the
   likeliest failure mode there is for an agent authoring JSON, and worse than
   §2.5's deferred validation because nothing surfaced at all. Fixed by Option
   1 of `planning/conf-extra-fields.md` §4: strict `extra="forbid"` twins of
   every write-time model (`adopt/adopt/study_conf_strict.py`), recursively
   through nested models, swapped into the nine POST route annotations. The
   load path keeps the lenient classes, so a conf written before a field was
   removed still loads. See that doc's §7 for what was settled and what it
   cost.
3. ~~**`RecruitmentConf` is an untagged union.**~~ **RESOLVED**, adopt v0.1.85.
   The three arms carried no tag, so the server shape-matched on which required
   fields were present — `PipelineRecruitmentExperiment` and
   `DestinationRecruitmentExperiment` separated by exactly `arms` vs
   `destinations`. Now discriminated on `type` (`simple`,
   `pipeline_experiment`, `destination` — the spellings the dashboard was
   already sending and `extra="ignore"` was already dropping), with a
   BeforeValidator inferring the tag from shape so stored confs still load. An
   over-specified body is a 422 naming the offending field rather than a silent
   downgrade to the pipeline arm.
4. **Dangling cross-references fail three different ways**: a bad
   stratum→creative name is a bare `KeyError` (`malaria.py:746`), a bad
   creative→destination name is a clear exception, and a bad audience name is
   dropped at `logging.info` (`malaria.py:689`) — where a dropped *exclusion*
   means the ad set silently re-recruits people it meant to exclude.
   Partitioned audiences are named `<name>-cohort-N` and never `<name>`, so a
   stratum naming one by its conf name always dangles. The SDK's validator
   should own this; it is exactly the whole-study check no single write can do.
5. ~~**`GET /confs/{conf_type}` takes the stored name, not the URL segment**~~
   **RESOLVED**, adopt v0.1.85. `confs/data-sources` wrote `data_sources`, so
   the one URL that could write a section was the one URL that could not read
   it back. Both spellings are now accepted — the underscore too, because that
   is what `GET /confs` returns as a key and was the only spelling that worked
   before.
6. **`devops/helm/migrations/init.sql` looks stale** — it declares `users.id`
   as UUID where the live schema is VARCHAR, and has no `org_id`. Needs its own
   decision.
7. ~~**A `LOOKALIKE` or `PARTITIONED` audience cannot be written as JSON.**~~
   **RESOLVED**, adopt v0.1.85. Found while implementing item 2, not before.
   `AudienceConf.__post_init__` runs at `mode="before"`, so it sees the raw
   body, but `validate()` asserted `isinstance(val, Lookalike)` — that the
   sub-object was already a parsed model. No request body can satisfy that, so
   both subtypes were an unconditional 422 on write, and a stored one would
   have failed `StudyConf` assembly on every cron run. Invisible because every
   test builds the nested models in Python first and the dashboard's audience
   form writes neither subtype (its controls are disabled, "not yet
   available"). `validate()` now checks presence only; shape is the field
   annotation's job, which it was already doing.

   The general lesson is worth more than the fix: a `mode="before"` validator
   sees what the wire sent, and a test that constructs the model in Python
   hands it something the wire never can. Two of the three before-validators in
   `study_conf.py` were written as though they ran after parsing.

### 11.5 Still true, still open

Everything in §10 stands. Phases 1 (§12) and 2 (§13) are done, and of §11.4's
defects only items 4 (dangling cross-references fail three different ways) and
6 (the stale `init.sql`) remain — see §14 for what closing 2, 3, 5 and 7 cost.

Item 2 was the blocker named here for Phase 3, and it is gone: the server no
longer silently drops what it does not recognise, so an SDK that validates
locally is now validating against something the server agrees with. What
remains open for Phase 3 is item 4 — the whole-study reference check that no
single write can do, which is the SDK's own job — plus the SDK and the MCP
shim themselves.

---

## 12. Phase 1: the compiler, in Python, once

Implemented 2026-09-04, the same day Phase 0 deployed. Three agents in
parallel: one port each, and a third building the differential harness
against the real TypeScript before either port existed.

### 12.1 What shipped

| | |
|---|---|
| `adopt/adopt/authoring/strata.py` | Port of `strata.ts`: `create_strata_from_variables`, `format_group_product`, `strata_staleness_hint`, `get_finish_question_ref`. Works on JSON wire shapes; accepts pydantic models by dumping them first. |
| `adopt/adopt/authoring/extract.py` | Port of `extract.ts`: `extract_from_adset`, `is_level_in_sync`, `diff_property_keys`; typed errors under an `ExtractError(Exception)` base. |
| `test_strata.py`, `test_extract.py` | `strata.spec.ts` and `extract.test.ts` translated test-for-test, plus a marked section of extra cases for behaviour the TypeScript leaves implicit. |
| `dashboard/scripts/authoring-conformance.ts` | Runs the **real** TypeScript over 1,142 cases — every spec literal, 98 hand-written edge cases, 1,000 seeded-random (mulberry32) — and records `(fn, args, result \| error)`. Byte-reproducible. |
| `conformance_fixtures.json`, `test_conformance.py` | Replays every recording through the Python. Comparator is stricter than `==`: booleans by identity, floats exact, key sets equal. Negative control: nine seeded divergences all caught; reversing the shallow-merge precedence in the port fails 190 cases. |
| `make -C adopt authoring-fixtures` | Regenerates the fixtures (installs `dashboard/node_modules` if absent). Run it whenever the TypeScript changes. |
| `configuration.py` | Marked superseded in its docstring, kept for `read_share_lookup`, `parse_*_sheet`, `location_levels`. |

Result: 1,147 conformance tests plus 69 translated tests green; the rest of the
adopt suite unchanged at 829.

### 12.2 Decisions the TypeScript left implicit

Each is documented at the point in the port where it bites; the ones that
matter to a caller:

- **The port works on dicts, not `StratumConf`.** The TypeScript is `any` at
  every boundary and conformance is defined against its literal JSON output.
  Building a `StratumConf` from the result is the caller's validation step.
- **`create_strata_from_variables` merges `existing_strata` only for fields
  actually present.** The TypeScript copies `undefined` for a missing
  `creatives`/`audiences`/`excluded_audiences` and `JSON.stringify` drops the
  key, erasing the fresh default; Python has no `undefined`. All three fields
  are required in both type systems, so this only differs for hand-built input.
- **Where the TypeScript throws a `TypeError`, the port raises a named
  exception** (`ValueError` for saved strata with no `answered` term, or an
  empty level list; `TypeError` with a message for an ad set with no
  `targeting`). Those inputs are excluded from the fixtures by construction,
  and the generator's header lists them.
- **`isEqual` → `==`.** Identical on JSON-shaped data; they differ only on
  `NaN` (unrepresentable in JSON) and `True == 1` (Python only, and Meta
  returns one type per field).
- **`quota` accumulates from `1.0`**, so it is a float even for integral level
  quotas — JS has one number type and the JSON shape has to match.

### 12.3 Bugs in the TypeScript, ported faithfully and not fixed

The port reproduces these so the dashboard and the library agree. Fixing any
of them is a dashboard change first, then a fixture regeneration.

1. **`strataStalenessHint`'s `"dummy"` fallback is dead.** `getFinishQuestionRef`
   returns `""` only for an empty array, which the guard above already
   returned on; for a non-empty saved stratum with no `answered` term it
   throws. So the dashboard gets an uncaught `TypeError` rendering the
   staleness banner for any conf whose strata lack `question_targeting` —
   plausible for older or hand-written confs.
2. **Staleness check 1 is not a set comparison** — length plus `saved ⊆ fresh`
   — so duplicate ids (two variables sharing a name) pass while the multisets
   differ.
3. **Staleness never inspects `question_targeting` or `metadata`.** A changed
   finish-question ref is undetectable by construction, because the fresh
   strata are generated *using* the saved ref.
4. **`diffPropertyKeys` filters `targeting_automation` out of the stored keys
   but not out of `current`.** A variable listing `targeting_automation` as a
   property shows the two-line drift banner forever; `extractFromAdset` will
   happily accept that property. `added`/`removed` also do not dedupe.
5. **`strata.spec.ts`'s first case passes `creatives` in the
   `finishQuestionRef` slot** and passes only because the empty-variables
   guard fires first. Translated as-is with a comment.

### 12.4 Still open after Phase 1

- **The salvage of `configuration.py`** (§10) is deferred to Phase 3, when the
  SDK gives `read_share_lookup` / `location_levels` a consumer to shape their
  API around. There is no `campaigns/` directory in this repo to read notebook
  usage from, so the read-through §10 asks for cannot happen here.
- **Regenerating the fixtures needs node and `npm ci` in `dashboard/`**; CI
  does not do it. The committed fixtures are the contract, and a TypeScript
  change that forgets to regenerate them will not be caught until someone runs
  `make -C adopt authoring-fixtures`. A CI job that regenerates and diffs is
  the obvious follow-up.
- **Not yet released.** `adopt` ships the package in its image (`COPY . .`),
  but nothing on the server calls it; the next release picks it up for free
  and the SDK (Phase 3) is its first consumer.

### 12.5 What review found that the fixtures did not

A read-through of the port against the TypeScript (2026-09-05, before merge)
found three divergences on inputs the fixture generator never produces. All
three are fixed on the branch, each with a test in the "beyond the spec"
section of `test_strata.py`, but they are worth recording because they are
exactly the shape of gap the harness has: **it only generates dashboard-shaped
input**, and this library exists for input the dashboard did not write.

1. `quota: null` in a saved stratum. JS coerces `null` to 0 in arithmetic, so
   the TypeScript reports stale; the port read `.get("quota") is None` and
   skipped, conflating null with a missing key (which really is not-stale, via
   NaN). JSON-representable, so a real wrong answer.
2. Non-string level or variable names. `${1.0}` is `"1"` in JS and `"1.0"` in
   Python; `True`/`None` likewise. The stratum id is the merge key, so an
   agent loading `name: 1.0` from YAML wrote strata the dashboard could never
   match. `_js_str` now follows JS for bool, None, int and float.
3. `get_finish_question_ref([{}])` returned `""` because `not {}` is true in
   Python where `!{}` is false in JS; the TypeScript throws. Now raises.

Still open from the same review:

- **The generator's blind spots**: no non-string names, no `quota: null`, no
  pydantic-model inputs, no `variables=None`. The comparator does not compare
  error *messages*, and every TypeError-producing input is excluded by
  construction, so the port's error-type choices (§12.2) are untested by the
  differential. Extending the generator is the right fix; the three cases
  above are pinned in Python only until then.
- **The "nine seeded divergences" negative control left no artifact.** The
  merge-precedence reversal is reproducible (190 of 1,147 fail); the nine
  mutations are not. Committing them as a skipped test block or a make target
  would make the claim checkable.
- **§12.3 bug 1 is a live dashboard crash**, not just a port note: an
  uncaught `TypeError` rendering the staleness banner for any conf whose
  strata lack a `question_targeting`. It should be filed as a dashboard issue.

Item 1 (`InvalidConfigError` derives from `BaseException`) is fixed — it now
derives from `ValueError` (`adopt/adopt/study_conf.py:930`), so pydantic wraps
it and `POST /confs/{conf_type}` returns a 422 with the validator's message
instead of a bare 500. Item 2 (`extra="ignore"`) is investigated but
deliberately not changed: see `planning/conf-extra-fields.md` for the full
model inventory, the dashboard-vs-pydantic field comparison, and the
recommended "strict sibling classes on the POST routes only" shape.

*Superseded in part: the Meta proxy shipped on 2026-09-05, see §13. §12 is
Phase 1's record and lands with PR #254.*

---

## 13. Phase 2: the Meta proxy, what shipped and what the plan got wrong

Implemented 2026-09-05 on `feature/agent-study-authoring-phase2`. Same
discipline as §11: where this disagrees with §8's two-line description of Phase
2, this was verified against running code and §8 was a sketch.

### 13.1 What shipped

| Commit | What |
|---|---|
| `a85bdff1` | `meta` added to `RESOURCES` and to `required_scope`, so `/{org}/meta/...` is a classified path for the fail-closed scope middleware |
| `e2cd216a` | `server/meta.py` — five GET routes, credential resolution, pagination, Meta-error mapping; `db.py` credential helpers; 44 tests |

Test suite 829 → 873, no regressions. The dashboard was deliberately **not**
repointed at the proxy (§13.5).

### 13.2 The routes, and why they are not quite §8's

§8 named `adaccounts`, `campaigns`, `adsets`, `ads`. What shipped:

| Route | Graph call | Dashboard equivalent |
|---|---|---|
| `GET /{org}/meta/credentials` | none — reads `credentials` | none (new) |
| `GET /{org}/meta/adaccounts` | `/me/adaccounts` | `fetchAdAccounts`, `api.ts:475` |
| `GET /{org}/meta/campaigns?account=` | `/act_<id>/campaigns` | `fetchCampaigns`, `api.ts:505` |
| `GET /{org}/meta/adsets?campaign=` | `/<campaign>/adsets` | `fetchAdsets`, `api.ts:537` |
| `GET /{org}/meta/ads?campaign=` or `?adset=` | `/<parent>/ads` | `fetchAds`, `api.ts:570` |
| `GET /{org}/meta/ads/{ad_id}/creative` | `/<ad>?fields=creative{…}` | none (new) |

Three things the plan did not know, all of them read out of the dashboard:

1. **There is no "ads for an ad set" call in the dashboard, and no separate
   creative call.** §2.4.3 describes the Creatives form as reading "the creative
   blob off a template ad", which reads as a per-ad request. It is not: the form
   fetches `/<campaign>/ads` with a `creative{…}` field expansion and picks one
   ad in the browser (`Creative.tsx:53` stores `ad["creative"]` verbatim). So
   `?campaign=` is the primary parameter for `/meta/ads`, `?adset=` is an
   addition, and the standalone creative route is a convenience with no
   precedent to copy.

2. **`fields` is the contract, not the path.** The creative field list
   (`api.ts:583`) is eleven names, and what is in it is exactly what ends up
   stored as `creatives[].template` and therefore deployed. It is reproduced
   verbatim, in order, and asserted as a literal in `test_meta.py` — a "tidy-up"
   that drops a field silently changes what studies ship. Note the dashboard's
   own `Ad` TypeScript interface disagrees with its own request: the interface
   declares `effective_instagram_story_id` and `instagram_actor_id`, which are
   not requested, and omits `contextual_multi_ads`, which is. The request wins.

3. **The dashboard's pagination is broken and must not be copied.** All four
   callers send the page token as `params['cursor']` (`api.ts:495`), but Graph's
   parameter is `after`. Graph ignores `cursor`, so "load more" silently
   re-fetches page one; with `limit: 100` nobody has noticed. The proxy sends
   `after`.

### 13.3 The credential decision, which §8 got wrong

**§8 says "reading with the study owner's stored credential". There is no
study.** These are the endpoints you call *before* you have written a `general`
conf, precisely in order to find out what to put in it — the ad account number,
the template campaign id, the creative blob. A per-study route would be
unusable for the job.

So the resolved credential is the **calling user's**. That is not a weakening:
the API key's `sub` is a user, and the dashboard already reads Meta client-side
with that same user's token. The proxy moves where the read happens, not whose
token it is.

The wrinkle is that a user can hold more than one Facebook credential — the
production study owner in `planning/encoded-ref-probe-runbook.md:524` holds
`Facebook` (entity `facebook`) *and* `virtual-lab-vlab` (entity
`facebook_ad_user`) — and different tokens see different ad accounts. The rule
shipped:

- `?credentials_key=<name>` selects one, and takes exactly the value that goes
  into `general.credentials_key`, so an agent can point the proxy at the
  credential the study will actually run on.
- No parameter, exactly one Facebook credential → that one. The common case.
- No parameter, more than one → **409 naming them**, not a pick. Silently
  choosing would hand back an ad-account list the study cannot use, and the
  failure would surface hours later as a Meta rejection at ad-set create time
  with nothing pointing at the cause.

`GET /{org}/meta/credentials` exists so that the 409 is recoverable without a
human. It also closes a gap that had nothing to do with the proxy: an agent
needs `credentials_key` to write `general`, and no API-key-reachable endpoint
listed the valid values. The Go service's `/accounts` does, but it is Auth0-only
and it returns `details` — access token included — to the browser.

**The lookup is bug-compatible with `get_user_info` on the part that matters,
and not on the part that would leak.** `db.get_facebook_token` matches on
`(user_id, key)` without requiring a *specific* entity, exactly as
`campaign_queries.py:13` does — that query selects `credentials_entity` out of
the general conf and then never joins on it. Being *stricter* than the query
that resolves the token at run time is the dangerous direction: the proxy would
report "no such credential" for a key a study is happily running on. That
looseness is recorded rather than fixed, because fixing it means deciding which
entity is correct, and the codebase has three answers (the dashboard hardcodes
`facebook`, the `studies.credentials_entity` column defaults to
`facebook_ad_user`, `ctwa_probe.py` queries `facebook_ad_user`) precisely
because nothing has ever had to agree.

It does, however, constrain `entity` to `FACEBOOK_CREDENTIAL_ENTITIES` — which
narrows nothing `get_user_info` would have found, since both production
entities are in the set, and closes something review caught after the first
draft shipped. `credentials` holds tokens for other providers (`typeform`,
`fly`, `whatsapp_business`) and several store a field called `access_token`.
With no entity predicate at all, `?credentials_key=<my typeform credential>`
would have sent that token to `graph.facebook.com`. The caller's own token, so
not a cross-tenant leak — but a credential handed to a third party with no
business seeing it. It also made the 404's "Available:" list contradict the
lookup, because that list comes from `list_facebook_credentials`, which always
filtered on entity. The two queries have to accept the same rows or the error
message is a lie.

### 13.4 Decisions worth their own line

**Pagination: follow cursors server-side, up to 10 pages, and say so.** The
response carries `paging: {after, truncated, pages_fetched}`. `truncated: true`
means the cap stopped us, not Meta, and `after` is the resume token. Both
alternatives were worse. A pure passthrough makes every caller page, and an
agent that reads only the first page of ad sets builds a study missing strata
and never finds out. Following forever assembles an unbounded response — a
campaign's ads each carry a full creative blob — in memory behind a synchronous
handler.

**`meta` is its own scope resource, not part of `studies`.** The proxy reads a
different system with a different credential, and that credential can see every
ad account, campaign and creative the researcher has on Meta, including ones
belonging to no vlab study. A key granted `studies:write` to author one study's
config should not become a window onto all of that by implication. The Phase 0
middleware is fail-closed, so this was not optional in any case: an
unclassified `/{org}/meta/...` path is denied to every scoped key.

**`adopt.facebook.api.call` is not reused.** It retries codes 2/17/368/80004
forever at five-minute intervals with no attempt cap, and drains cursors with no
page limit. Both are correct for a cron with hours to spend and fatal in an HTTP
handler. `facebook.state.get_api` *is* reused, so the proxy authenticates
identically to the optimize path — same `appsecret_proof`, same per-request
session, no process-global `FacebookAdsApi.init` (which would be a cross-tenant
credential bug in a multi-user service).

**Meta errors keep their identity.** 400/403/404 pass their status through with
`{code, subcode, type, message, http_status}`; 429 and 5xx become 502; an
unreachable Graph API becomes 502. Never a bare 500 — §11.4's complaint about
`InvalidConfigError` is the same complaint, and this is the half of it Phase 2
could fix without touching `study_conf.py`. `str(FacebookRequestError)` is never
echoed: the SDK interpolates the whole `request_context` into it.

**The token never leaves the server, and that is a test, not a claim.**
`test_the_access_token_never_appears_in_a_response` sweeps all six routes across
four outcomes (success, Meta 4xx, Meta 5xx, network failure) and asserts neither
the token nor its `appsecret_proof` is in the body or the headers.

**Every handler does its work in `asyncio.to_thread`, under `async_timeout`.**
Added after review; the first draft had `async def` handlers calling blocking
psycopg and blocking `requests` directly, which pins the event loop for the
whole request. The worst case — `MAX_PAGES` × `GRAPH_TIMEOUT_SECONDS` — is 200
seconds during which the process would serve nothing at all, `/health`
included, so one slow ad account would read as a dead pod to Kubernetes.
`server.optimize_study` had already established the pattern for exactly this
hazard and the proxy now follows it; `async_timeout` moved from `server.py` to
`deps.py` so `meta.py` could use it without the import cycle. Plain `def`
handlers would also have freed the loop (FastAPI threadpools those) but
`asyncio.wait_for` cannot interrupt a sync handler, so there would be no bound
on how long a client waits.

The regression test is `test_the_event_loop_is_not_blocked_while_meta_is_slow`,
which drives the real ASGI app on a real loop with a slow Graph call and counts
how often an unrelated coroutine gets scheduled meanwhile. Verified
non-vacuous: reverting one handler to the inline form drops it from ~40 ticks
to 2. Cheap validation (ids, mutually-exclusive parameters) deliberately stays
outside the thread, so a malformed request never occupies a worker.

### 13.5 Deliberately not done

- **The dashboard was not repointed.** It works, it holds the token already, and
  repointing live UI buys the agent nothing. The proxy is *shaped* so that it
  could be — same paths, same fields, same nesting — and that shape is what the
  field-list assertions in `test_meta.py` protect. Cutting the dashboard over
  would let the token stop being shipped to the browser at all, which is a real
  security improvement and its own piece of work.
- **No caching.** Every request is a live Graph read. Meta's rate limits are
  per-app and an agent in a loop could hit them; nothing here defends against
  that beyond the page cap.
- **No write proxy.** `meta:write` is expressible and nothing serves it.

### 13.6 Known gaps, marked rather than guessed

- ~~**Whether `conf-dashboard` has `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` in
  production was not verified directly.**~~ **VERIFIED PRESENT, 2026-09-05.**
  Both are on the production `vlab-conf-dashboard` deployment, supplied by the
  `facebook-envs` secret. The key names were inspected; the values were not
  read, and nothing here needs them. So the inference recorded above was
  correct, and the proxy has the credentials it needs — but it is now a fact
  rather than a deduction from "optimize works". The startup check suggested
  here is still worth having for the case where the secret changes; nothing
  fails loudly at boot today.
- **Graph API version drift is unresolved and predates this work.** The
  dashboard pins `v22.0` (`netlify.toml`), the SDK pins `v22.0`
  (`facebook-business = "v22"`), and `facebook/update.py:34` hardcodes `v20.0`
  in a raw `requests` call. The proxy inherits the SDK's version, so it agrees
  with the dashboard — but nobody has decided what the version *should* be, or
  who owns bumping it.
- **Meta's real page-size ceiling per edge was not measured.** `MAX_LIMIT = 500`
  is a guard against absurd requests, not a documented Meta limit; Meta may cap
  lower on some edges and simply return fewer.
- **`limit` interacts with `MAX_PAGES` multiplicatively and nothing enforces a
  total.** A caller asking `limit=500` can pull 5,000 ads with full creative
  blobs in one request. Not observed to be a problem; not defended against
  either.

---

## 14. Closing §11.4 items 2, 3, 5 and 7

Shipped 2026-09-05 as one PR against adopt v0.1.84.
`planning/conf-extra-fields.md` §7 has the full record; this is what a reader
of §11 needs.

### 14.1 What the shape turned out to be

Option 1 of the investigation, unchanged: `XStrict(X)` twins carrying
`model_config = ConfigDict(extra="forbid")`, in a new module
`adopt/adopt/study_conf_strict.py`, swapped into the nine POST route
annotations. No handler body changed — `create_conf` already treats the config
generically via `model_dump()`.

Two things the investigation had not decided, and one it did not know:

**Strictness goes all the way down.** `extra="forbid"` is per-class and says
nothing about nested models, so a twin exists for every model reachable from a
route and every field pointing at one is re-declared to point at the twin. A
typo at `audiences[].lookalike.spec.rati` is as likely and as silent as one at
the top level. The re-declaration is what a future change will forget, so a
test walks the annotations out from each route's type and fails on any model it
reaches that is not strict — the set stays complete without anyone remembering
to keep it complete. Arbitrary-key fields (`facebook_targeting`, `template`,
`extra_metadata`, `metadata`, `config`) stay arbitrary; an unknown key there is
the feature.

**`VariableConf` got a twin like everything else**, though §2 of the
investigation licensed forbidding in place because nothing reloads it. That
licence rests on a fact about today, not a property of the model, and a
`POST /studies/{slug}/validate` endpoint that re-reads stored confs was being
built in parallel. One uniform mechanism costs four lines and removes the need
to remember which model is the exception.

### 14.2 The thing that would have broken production

`extra="forbid"` alone would have 422'd the dashboard on the existing corpus,
not on typos.

The dashboard's edit path re-POSTs whatever `GET /confs` returned, verbatim.
That is the last successful `model_dump()` — so it contains whatever the models
declared on the day that conf was last saved, including fields this repo has
since **removed**. `destination_type` was a REQUIRED field on all three
recruitment classes until `d382000c` (2026-08-30), so every recruitment conf
older than that carries it, and "open a study and extend its end date" would
have become a 422 on studies that had done nothing wrong.
`include_metadata_in_ref` is the same story on destinations until `065bacb8`.

The answer is a closed list of retired keys, accepted and dropped, each cited
to the commit that removed it. Two names one can point at a commit for is a
bounded set; every possible misspelling is not. **A future field removal has to
add a line to that list, next to the removal, or it breaks the dashboard's edit
path** — which is a better prompt than the silence there is today.

This was not in the investigation, which checked the dashboard's *forms*
against the models (§3 there) and found them aligned. Alignment of the forms
was never the question: what round-trips through the edit path is stored JSON,
which is older than any form.

### 14.3 §6 question 2, settled — the legacy default stays, on write too

The strict destination union applies `_default_missing_destination_type`, the
same validator the lenient one uses. Decided the other way first, and reversed
in review; the reversal is the more instructive half.

The case for rejecting a missing `type` on a fresh write was that nothing being
POSTed today predates the field, so an absent tag is an author who forgot it.
True, and beside the point once the twins forbid unknown fields. A typeless body
is defaulted to `messenger` and then validated against the STRICT messenger
model, so anything that is not genuinely messenger-shaped is rejected on its own
type-specific fields — measured: whatsapp on `whatsapp_phone_number` plus a
missing `button_text`, web on `url_template` plus three missing, app on six
extras.

**The multi case decides it.** A multi conf satisfies every field a Messenger
conf requires — that is precisely why, under the old plain union, every multi
destination silently became a Messenger one and Meta rejected every ad on
`vl-pulse-nigeria-smoke`. No required-field check catches it, and neither would
a mandatory tag on a body that simply omits one. It is caught by
`whatsapp_phone_number` being an unknown key, and by nothing else. Forbidding
extras closed that hole; the tag being mandatory never did.

Against zero added protection, rejecting the tag cost the 45 typeless confs
across 11 studies their ability to be re-saved: the dashboard renders no subform
for a destination whose type it cannot read, so it re-POSTs the conf verbatim,
and editing destinations on those studies would have failed. Whether any is live
was never determined. That is production breakage bought with nothing.

The published schema still marks `type` required, so an agent writes it; the
server is lenient on this one key for the legacy corpus, and `adopt/README.md`
records that the file is deliberately stricter than the server there.

§6 question 1 (is there a non-dashboard writer carrying legacy keys?) is
answered only partly: git proves which fields were once declared and removed,
and both are on the retired list. Whether the notebook era or `copy-from` put
anything else in the corpus needs the production query at §5 of that doc, which
was deliberately not run. If such a key exists it is now a 422 on first re-save,
naming the key — legible, and recoverable by adding the name to the list.

### 14.4 The bug found on the way

Item 7 of §11.4: `LOOKALIKE` and `PARTITIONED` audiences could never be written
as JSON, on any path, because a `mode="before"` validator required the
sub-object to already be a parsed pydantic instance. Found because the strict
twins for `Lookalike` and `LookalikeSpec` had no reachable code path to write a
test against.

That is the transferable part. **A `mode="before"` validator sees what the wire
sent; a test that constructs the model in Python hands it something the wire
never can.** Both of `study_conf.py`'s remaining before-validators were written
as though they ran after parsing. `Partitioning.validate_scenario` survives
only because it reads keys rather than types — and under `extra="forbid"` it
now sees unknown keys before the extra check does, so a typo there reports as
"invalid partitioning config" rather than "extra inputs are not permitted". It
still names the key, which is what matters.

---

## Appendix A. Notes for whoever implements Phase 0

Read out of the code while writing this document; recorded here so the port
does not have to rediscover them.

### A.1 There are already two study-creation implementations, and they disagree

| | Go: `api/internal/storage/study.go:112` | Python: `adopt/adopt/campaign_queries.py:66` |
|---|---|---|
| slug | `slug.Make(name)` (gosimple/slug) | `name` verbatim — there is a `# TODO: this makes name = slug!` on the line above |
| `org_id` | set from the URI segment | **not set at all** |
| `credentials_key` | left NULL | required argument, written |

The new FastAPI endpoint must follow the **Go** column semantics, not the
Python ones, because the Go path is what every live study was created with.
Specifically:

- **`org_id` is not optional.** `get_study_id` and `get_study_conf`
  (`adopt/adopt/server/db.py:132`, `:79`) both join
  `orgs_lookup ol ON ol.org_id = s.org_id AND s.org_id = %s`. A study row with
  a NULL `org_id` is invisible to every conf endpoint — it can be created and
  then never configured. `create_campaign_for_user` has exactly this bug, which
  is survivable for notebooks (they wrote confs by direct DB insert too) and
  fatal for anything going through the API.
- **Slug generation must match `gosimple/slug`**, or a study created via the
  API gets a different URL from one created in the dashboard with the same
  name. Worth a test with a name containing spaces, punctuation and
  non-ASCII.
- **Preserve the uniqueness behaviour.** `unique_name UNIQUE(user_id, name)`
  and `unique_slug UNIQUE(user_id, slug)` are per-user, not per-org. The Go
  handler maps the constraint violation to `409` with "The name is already in
  use." (`api/internal/server/handler/studies/create.go`); the port should
  return the same status and a comparable message.
- Name is capped at 300 **bytes** — not characters; Go's `len()` on a string
  counts bytes, so 151 `ñ` is already rejected today (corrected in §11) — and
  rejected when blank, in the Go handler
  rather than in the database.

### A.2 `studies.credentials_key` is vestigial on the modern path

The table carries `credentials_key` and `credentials_entity DEFAULT
'facebook_ad_user'`, with an FK to `credentials(user_id, entity, key)`
(`devops/migrations/20230322111807_init.up.sql:86`). The Go create path leaves
`credentials_key` NULL, which satisfies the FK vacuously.

Facebook credentials are actually resolved from the **general conf**, not from
this column: `get_user_info` (`adopt/adopt/campaign_queries.py:13`) reads
`conf->>'credentials_key'` and `conf->>'credentials_entity'` out of the
`general` study conf and joins `credentials` on those.

So the new endpoint should leave the column NULL like the Go one does. Do not
copy `create_campaign_for_user`'s `key` argument — it will fail the FK unless a
matching credentials row already exists, and it buys nothing.

### A.3 What "deprecate the Go endpoint" means concretely

The Go service's study-conf half is already dead: `POST/GET
/:org/studies/:slug/conf` are registered in
`api/internal/server/server.go` and the only dashboard caller is
`deleteDestination` (`dashboard/src/helpers/api.ts:210`), which nothing
imports. `api/internal/types/studyconf.go` (345 lines) has drifted from the
pydantic models that are actually enforced and should not be used as a
reference for the port.

Still live on the Go service and **not** in scope for Phase 0: users/orgs
(`POST /users`), accounts and credentials, the Facebook OAuth token exchange
(`POST /facebook/token`), and segments progress. Retiring those is a separate
decision (§10).

### A.4 The fly hardening design, in one paragraph

So the Phase 0 auth work does not have to re-read the commit. Validity is
**positive**: a key is live iff its credentials row is live, tied by a `jti`
claim, so revocation is a row delete and reusing a name cannot resurrect a
revoked token. The `jti` is written into `details` by the application and
surfaced as a *computed, stored* column with a partial unique index, so the
verifier's lookup is an index seek rather than a JSONB scan — vlab's
`credentials` table already does this for `facebook_page_id` — **wrong, that
precedent is fly's `media`/`message_templates` tables; vlab had no such column
and Phase 0 created the pattern fresh (§11.2)**. Lookups are
cached with a bounded TTL cache that caches **negative** results too, so
replaying random jtis cannot become a database amplification attack; the
tradeoff is that revocation is "dead within a minute", not instant, and the
docs must say so. Legacy keys carry no `jti` but do carry the token-name
claim, so they stay revocable by (user, name) — with the one hazard that name
reuse defeats it, which is exactly what `jti` fixes going forward.
**⚠ That last sentence is true of fly and FALSE of vlab — see §11.2. vlab has
always minted a `jti` and discarded it, so "requires a row iff it has a jti"
would revoke every key in production. Do not carry fly's discriminator over.** Scopes are
`<resource>:<action>`, `write` implies `read`, and **an absent scopes claim
means unrestricted** so no existing key breaks. On `exp`: fly could not
require it because its signing secret is shared with services that mint their
own unexpiring internal JWTs. **vlab does not have that constraint** —
`API_KEY_SECRET` is read in exactly one place, `adopt/adopt/server/auth.py`,
and nothing else in the repo signs with it. So the vlab verifier *can* require
`exp` on newly-minted keys, and should.

Source: `fly:899443fe`, `fly:devops/migrations/32-api-token-hardening.sql`,
`fly:dashboard-server/api/auth/auth.core.js`.


### A.5 There is no vlab staging environment — test Phase 0 locally

*Resolved 2026-09-04 against `gke_toixotoixo_europe-west1-b_toixo`. This
section previously left it undetermined whether staging's `conf-dashboard` was
crashlooping for want of `vlab-api-key-envs`. The answer is neither of the two
possibilities it offered.*

**There is no vlab release in staging at all.** `helm list -A` shows `vlab`
deployed only in `vprod` (revision 141). The `vstag` namespace carries only the
`gbv` release — the fly/chatbot stack — and all 14 of its deployments are
`gbv-*`. There is no `vlab-conf-dashboard` there, no
`sh.helm.release.v1.vlab.*` secret, and no ingress for
`staging.vlab-study-conf-api.toixo.vlab.digital` (vstag's four ingresses are
all gbv/fly hosts).

So `devops/values/toixo-staging.yaml` describes a deployment that does not
exist. Two other planning documents already record this —
`planning/migration-job-fix.md:288` ("`toixo-staging.yaml` and
`curiouslearning.yaml` are **not live**", confirmed 2026-07-19) and
`planning/encoded-ref-probe-runbook.md:145` ("vlab **staging is unusable**").
This section's framing was wrong to treat the missing secret as the problem.

**A correction to the premise, too.** `curiouslearning.yaml` has no `services:`
key at all — it uses a legacy top-level `dashboard:` mapping, and
`devops/helm/templates/services.yaml:1` ranges over `.Values.services`. So
`conf-dashboard` was never rendered in that environment regardless of secrets,
and it is a different cluster besides.

**Production is healthy and needs nothing.** `vlab-api-key-envs` exists in
`vprod` (3 keys, created 662 days ago) and `vlab-conf-dashboard` has been
Running for days behind a `/health` liveness probe. That is itself the proof
that all three variables are set: `adopt/adopt/server/auth.py:16-18` reads them
at module import with `environs`' `env()`, which raises when one is missing, so
the process could not have started otherwise. (Secret *contents* were not
inspected; the running pod is sufficient evidence.)

**What this changes for Phase 0.** The prerequisite this section asked for —
"add the secret to staging, it's a one-line values change" — is not one line
and is not worth doing. `toixo-staging.yaml` pins adopt `v0.0.106` (roughly
eighty releases behind prod's `v0.1.82`) and has no `migrations:` block, so the
chart's pre-upgrade migration hook has no target
(`planning/encoded-ref-handover.md:226`). Standing staging up is its own
project, not a warm-up for API-key work.

**Test locally instead — the harness already exists and CI already uses it.**

```
make -C adopt test-db   # CockroachDB v24.1.28 on :5433, migrated
make -C adopt test
```

`devops/Makefile:33` brings up the container and runs the real migrations, and
`adopt/adopt/server/test_server.py:18-22` already sets `API_KEY_DOMAIN`,
`API_KEY_AUDIENCE` and `API_KEY_SECRET` before importing the app, then drives
it through a FastAPI `TestClient` against that database. Both halves of Phase 0
— study creation on the Python service, and jti-backed key revocation with
`exp` and scopes — are exercisable end to end there, against the real schema,
with no cluster involved. `.github/workflows/adopt.yaml` runs exactly these two
commands on every PR touching `adopt/`, so the tests written for Phase 0 gate
merges for free.

The only thing local testing cannot cover is behaviour that depends on
production credentials or on Meta — which is Phase 2's problem, not Phase 0's.
