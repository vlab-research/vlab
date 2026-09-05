# Letting an agent create studies

Exploration and decision path for giving an AI agent (or a script, or a
notebook) the ability to create and configure a vlab study without driving the
React dashboard by hand.

Status: **Phase 0 implemented; Phases 1–4 not started.** §1–§5 are findings
read out of the code, with the file establishing each claim named next to it.
§7 records the decisions taken and why, §8 is the plan, §10 is what is still
open, and **§11 records what Phase 0 actually shipped and the six claims below
that the implementation proved wrong** — several of them load-bearing, so read
§11 before trusting a detail in §2 or Appendix A.

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
2. **Every conf model is `extra="ignore"`.** A misspelled *optional* field is
   accepted and silently dropped. For a dashboard user the form supplies the
   names; for an agent authoring JSON this is the likeliest failure mode there
   is, and vlab's answer is to accept the write and discard the field. **This
   is worse than the deferred-validation problem of §2.5, because nothing ever
   surfaces at all**, and it should be settled before the SDK ships.
3. **`RecruitmentConf` is an untagged union.** The three arms carry no tag, so
   the server shape-matches on which required fields are present —
   `PipelineRecruitmentExperiment` and `DestinationRecruitmentExperiment` are
   separated by exactly `arms` vs `destinations`. Add one optional field to
   either and they become mutually satisfiable. Same defect class as the
   destination union, which per the comments at `study_conf.py:1090` cost a
   live ad rejection on 2026-08-30. An over-specified body already resolves to
   the pipeline arm and silently drops `destinations`.
4. **Dangling cross-references fail three different ways**: a bad
   stratum→creative name is a bare `KeyError` (`malaria.py:746`), a bad
   creative→destination name is a clear exception, and a bad audience name is
   dropped at `logging.info` (`malaria.py:689`) — where a dropped *exclusion*
   means the ad set silently re-recruits people it meant to exclude.
   Partitioned audiences are named `<name>-cohort-N` and never `<name>`, so a
   stratum naming one by its conf name always dangles. The SDK's validator
   should own this; it is exactly the whole-study check no single write can do.
5. **`GET /confs/{conf_type}` takes the stored name, not the URL segment** —
   `confs/data-sources` writes `data_sources`, so reading back with the hyphen
   raises. Latent; the dashboard only uses `GET /confs`.
6. **`devops/helm/migrations/init.sql` looks stale** — it declares `users.id`
   as UUID where the live schema is VARCHAR, and has no `org_id`. Needs its own
   decision.

### 11.5 Still true, still open

Everything in §10 stands. Phases 1–4 are untouched: the compiler is still only
in browser TypeScript, there is still no Meta proxy, no SDK and no MCP. Item 2
above (`extra="ignore"`) is the one that most deserves settling before Phase 3
starts, because an SDK that validates locally is worth much less if the server
silently drops what it does not recognise.

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
