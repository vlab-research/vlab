# Study configuration API for agents

A reference for a program — an AI agent, a script, a notebook — that holds a
vlab API key and wants to configure a study and get ads running, without
driving the React dashboard.

Everything below was read out of the code, and the file that establishes each
claim is named next to it. Where a behaviour could not be determined from the
repository it is marked **undetermined** rather than guessed; those are
collected in §9.

**Read §4 before you write anything.** vlab's write endpoints validate one
configuration section at a time and never assemble the study, so a sequence of
`201`s does not mean you built a working study. This is the single most
dangerous property of the API for an automated caller.

The conceptual documentation for each configuration section — what a stratum
*means*, why you would use a lookalike audience — lives at
<https://docs.vlab.digital/vlab/study-configuration/> and is cross-linked from
§3 rather than repeated here. This document is the wire format and the
workflow.

---

## Authentication

### Two services, two base URLs

The dashboard talks to two backends and the split does not follow the directory
names. Both hosts are declared in
`devops/values/toixo-prod.yaml` (lines 44–68).

| | Go service | Python (FastAPI) service |
|---|---|---|
| Host (prod) | `vlab-dashboard-api.toixo.vlab.digital` | `vlab-study-conf-api.toixo.vlab.digital` |
| Source | `api/` | `adopt/adopt/server/` |
| Helm service name | `dashboard` | `conf-dashboard` |
| Owns | studies (list/read; create, now deprecated in favour of the Python route), users, orgs, accounts and credentials, the Facebook OAuth exchange, one legacy segments-progress route | **study creation and all study configuration**, optimize, instructions, study errors, ad attributions, recruitment stats, the read-only Meta Graph proxy, API keys (mint, list, revoke) |
| Auth | Auth0 RS256 **only** (`api/internal/server/server.go:43`) | Auth0 RS256 **or** a vlab API key |

**Everything in this document is on the Python service** unless it says
otherwise. An API key is accepted on every route there (subject to its scopes)
and on no route on the Go service.

The Go service also registers `POST/GET /:org/studies/:slug/conf`
(`api/internal/server/server.go:77-78`) with a full set of conf structs in
`api/internal/types/studyconf.go`. **Those are dead.** The dashboard writes
every conf to the Python service instead, and the Go types have drifted out of
agreement with the pydantic models that are actually enforced — the Go
`CreativeConf` still carries `ImageHash`/`Body`/`ButtonText` where the live
model has `template`/`template_campaign`. Do not use that file as a
specification and do not call those routes.

### Getting a key

```
POST /users/api-key
Authorization: Bearer <Auth0 access token, or an API key scoped auth:write>
{ "name": "hpv-agent",
  "scopes": ["studies:write", "meta:read", "optimize:read"],  // optional; omit = unrestricted
  "expires_in_days": 30 }                         // optional; default 90, max 365

201 { "data": { "name": "hpv-agent", "id": "<jti>", "token": "eyJ…",
                "scopes": ["studies:write", "optimize:read"],
                "expires_at": "2026-10-04T…+00:00" } }
```

`adopt/adopt/server/api_keys.py` (`create_api_key`); minting in
`generate_api_token` (`adopt/adopt/server/auth.py`). `name`, `id` and `token`
are the shape the dashboard already consumes; `scopes` and `expires_at` are
additive. A blank name is `400`; a name over 200 characters is `400`; a name
you already hold a live key under is
`409 {"detail": "An API key named 'hpv-agent' already exists"}`. Revoke the old
one first, or pick another name — revocation frees the name.

Note the bootstrap: **minting a key requires a token you already have.** For
the first key that is an Auth0 token, which means a browser login; the
dashboard has a button for it (`generateApiKey`,
`dashboard/src/helpers/api.ts:292`). After that a key can mint further keys
*if* it holds `auth:write`, and only ever narrower ones (see Scopes). An agent
cannot mint its own first key; a human hands it one.

The key is an HS256 JWT carrying `iss`, `aud`, `iat`, `exp`, `jti`, `sub` (the
user id), `type: "api_key"`, `https://vlab.digital/token-name`,
`https://vlab.digital/token-version: 2` and, when scoped,
`https://vlab.digital/scopes`. Send it as `Authorization: Bearer <token>` on
every request. `verify_tokens` (`auth.py`) tries the Auth0 RS256 verifier
first and falls back to the HS256 API-key verifier, so every route on this
service accepts either.

### What the key is

Since `20260904000000_api_token_hardening` (adopt v0.1.83) a key is a JWT
**plus a row** in `credentials` (`entity = "api_token"`, `key = <name>`, the
`jti` in `details`). The token itself is never stored. Validity is positive: a
key is live iff its row is live, so the row is the only thing that has to be
deleted to kill it, and there is no denylist to keep complete. The whole model
is written up at the top of `api_keys.py`; what matters to a caller:

- **Expiry.** Every key has an `exp`. Default 90 days, `expires_in_days` up to
  365. An expired key is `401`.
- **Revocation.** `DELETE /users/api-keys/{id}` — the `id` from the mint
  response, which is the `jti`. `204`; `404` if the id is not one of *your*
  live keys (never `403`, so it does not confirm someone else's key exists).
  The revoking replica drops the key immediately; **other replicas keep
  honouring it for up to 30 seconds** (`CACHE_TTL_SECONDS`), because row
  lookups — including misses — are cached in-process. Treat revocation as
  "dead within a minute".
- **Scopes.** Optional, and absent means unrestricted. Details below.
- **Listing.** `GET /users/api-keys` →
  `{"data": {"keys": [{id, name, scopes, created, expires_at, expired}],
  "legacy_revocations": [{name, created}]}}`. Needs `auth:read`.

**Scopes** are `<resource>:<action>` with resources `studies`, `responses`,
`stats`, `optimize`, `meta`, `auth` and actions `read`, `write`, `*`; the bare
`*` means everything. `write` implies `read` on the same resource. Which route
needs which is `required_scope` in `api_keys.py`:

| Route | Scope |
|---|---|
| `/{org}/studies`, `…/{slug}`, `…/{slug}/confs/…`, `…/{slug}/copy-from` | `studies` |
| `…/{slug}/ad-attributions`, `…/ad-attributions.csv` | `responses` |
| `…/{slug}/recruitment-stats`, `…/segments-progress`, `…/cost-over-time` | `stats` |
| `/{org}/optimize/…` (plan, instruction, errors) | `optimize` |
| `/{org}/meta/…` (the Meta Graph proxy, §2.5) | `meta` |
| `/users/api-key`, `/users/api-keys/…` | `auth` |

`studies` and `responses` are separate on purpose: configuration is the
researcher's work, ad-attributions are respondent-level records. `optimize` is
separate from `studies` because applying an instruction spends money on Meta.
`meta` is separate from everything because it reads a *different system with a
different credential* — the researcher's Facebook token, which can see every ad
account, campaign and creative they have on Meta, including ones belonging to no
vlab study at all; a key that can edit one study's config should not become a
window onto all of that by implication. `auth` is never implied by anything: a
key can only mint keys if it was given `auth:write`, and then only with a subset
of its own scopes (`403 "Cannot mint a key with more scopes than the key minting
it"`).

Enforcement is a middleware that runs *before routing*, and it **fails
closed**: a scoped key on a path the table above does not classify is
`403 {"detail": "This API key is not scoped for <path>"}`, even if the route
would otherwise accept it. A scoped key on a classified path it lacks is
`403 {"detail": "This API key is not scoped for studies:write"}`. Unscoped keys
and Auth0 sessions never see either. For an agent authoring a study, the useful
grant is `["studies:write", "meta:read", "optimize:read"]`: read Meta for the
ad account, template targeting and creative blob, write every section, run the
plan endpoint, and be unable to launch ads, read respondents, or mint keys.

Narrowing an existing key does not need a reissue — the row's scopes win over
the token's when they differ (`effective_scopes`) — but there is no endpoint
for it; that is a SQL edit.

### Keys minted before 2026-09-04

Everything above applies to keys carrying `token-version: 2`. Keys minted
before the hardening deploy carry no version claim, and vlab never stored
anything for them, so they take a **legacy path** that is exactly the old
behaviour: no row required, no expiry, no scopes, no listing. They remain
permanent, unrestricted credentials for the account until reissued.

The one lever a legacy key has is a tombstone by name:

```
POST /users/api-keys/legacy-revocations   { "name": "old-agent-key" }
201 { "name": "old-agent-key", "created": "…" }
```

It denies every legacy key of yours whose `token-name` claim is that name.
Names were never unique before the migration, so two legacy keys both called
`agent` die together or not at all; that errs toward denying, which is the
right direction. There is deliberately no un-revoke. The real fix for a legacy
key is to revoke it by name and mint a v2 key in its place — and if you were
handed a key before that date, ask for a reissued one, because nothing you can
do makes the old one expire.

### Failures

A token that verifies as neither Auth0 nor an API key is
`401 {"detail": "Could not validate credentials"}` with a
`WWW-Authenticate: Bearer` header (`adopt/adopt/server/deps.py`). The response
never distinguishes which verifier rejected it, **nor why** — signature, wrong
audience, expired, revoked and tombstoned all collapse to the same body. If a
key stops working, `GET /users/api-keys` with a working credential tells you
whether it is still listed and whether `expired` is set; a `401` on that call
too means the key is gone.

A `403` is always a scope problem. The body names the scope or path that was
wanted, or, when minting, says the requested scopes exceed the caller's.

---

## 1. The mental model

### 1.1 `study_confs` is append-only. `POST` is the update.

There is no `PUT`, no `PATCH` and no `DELETE` for any configuration section.
The table is

```sql
CREATE TABLE study_confs(
  created   TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  study_id  UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  conf_type string NOT NULL,
  conf      JSON NOT NULL
);
```

(`devops/migrations/20230322111807_init.up.sql:17`) — no primary key, no
uniqueness on `(study_id, conf_type)`. `create_study_conf`
(`adopt/adopt/server/db.py:151`) is a plain `INSERT … RETURNING *`.

**Changing a study's creatives means POSTing the whole creatives list again.**
You get a new row with a later `created`; the previous row stays exactly where
it is. Every reader takes the newest row per `conf_type`
(`get_all_study_confs`, `db.py:104`, a `ROW_NUMBER() OVER (PARTITION BY
conf_type ORDER BY created DESC)`), so the newest write wins and the history is
kept.

Three consequences that bite:

- **Every section POST is a full replace of that section.** For the six
  array-valued sections there is no way to add one creative or edit one
  stratum. Read the current list, modify it, POST the whole list back.
- **There is no delete.** Removing a destination means POSTing the
  destinations list without it. Removing a *section* entirely is not possible
  through the API — the newest row is always the effective one, and there is no
  way to write "no such section". (`deleteDestination` in
  `dashboard/src/helpers/api.ts:210` points at the dead Go route and has no
  caller anywhere in the dashboard.)
- **There is no concurrency control.** Two writers who each read-modify-write
  the same section will silently lose one of the two edits.

### 1.2 What reading back gives you

`GET /{org_id}/studies/{slug}/confs` returns
`{"data": {"<conf_type>": <conf>, …}}` — the newest row per type, and only the
types that have ever been written. This is the read you want.

`GET /{org_id}/studies/{slug}/confs/{conf_type}` returns one section. Its
`conf_type` path segment goes **straight into the SQL** (`db.py:79`), so it
takes the *stored* name, not the POST path segment. Those differ for two of the
nine: you POST to `confs/data-sources` and `confs/inference-data`, but the rows
are stored as `data_sources` and `inference_data` (`create_data_sources_conf`
and `create_inference_data_conf`). Since adopt v0.1.85 `GET /confs/{conf_type}`
accepts either spelling, so reading back with the hyphen works; before that it
found nothing and raised, surfacing as a `500`.

### 1.3 The reference graph

This is the part an agent most needs and it is written down nowhere else. The
nine sections are not independent documents: they are joined by **names**, and
almost none of those joins is checked when you write.

```
   general.credentials_key ──▶ credentials.key  (row must exist, per user)

   strata[].creatives[] ──▶ creatives[].name
                                creatives[].destination ──▶ destinations[].name

   strata[].audiences[]          ──▶ a live Meta custom audience NAME
   strata[].excluded_audiences[] ──▶ a live Meta custom audience NAME
                                          ▲
                                          │ audiences[] CREATES these,
                                          │ but does not always NAME them
                                          │ after audiences[].name — see below
                                      audiences[].name

   strata[].question_targeting  ──variable names──▶ inference_data
                                                     .data_sources[*]
                                                     .extraction_confs[].name

   inference_data.data_sources  ──keys are──▶ data_sources[].name

   recruitment.destinations[]  (DestinationRecruitmentExperiment only)
        ── matched by substring against generated campaign names,
           and used to filter creatives[].destination

   variables  ──▶ nothing on the server. See §1.5.
```

Edge by edge, with the resolver and what a dangling name actually does:

| Edge | Resolved at | Dangling name does |
|---|---|---|
| `strata[].creatives[]` → `creatives[].name` | `hydrate_strata`, `adopt/adopt/malaria.py:737,746` | **bare `KeyError`** out of a list comprehension, no message naming the stratum — the whole study's reconciliation run dies |
| `creatives[].destination` → `destinations[].name` | `get_destination_for_creative`, `adopt/adopt/marketing.py:942` | `Exception("Config Problem: destination <n> is not configured. Destination options: […]")` — a good message, and it kills the run |
| `strata[].audiences[]`, `strata[].excluded_audiences[]` → a Meta custom-audience name | `_add_aud`, `adopt/adopt/malaria.py:685` | **silently dropped at `logging.info`.** A dangling *exclusion* means the ad set runs with no exclusion and re-recruits people it meant to exclude |
| `strata[].question_targeting` variables → `ExtractionConf.name` | `missing_targeting_variables`, `adopt/adopt/study_conf.py` | **`logging.warning` only** (§4) |
| `inference_data.data_sources` keys → `data_sources[].name` | swoosh, `inference/swoosh/inference_data.go:642` | events from the unmapped source are skipped and folded into one aggregated extraction error; the inverse (a key naming a source that produces nothing) is not reported at all |
| `data_sources[].credentials_key` → `credentials.key` | `inference/connector/connector.go:52` | the study is silently not collected — the code's own comment at `connector.go:83` calls it "a form of silent failure" |
| `general.credentials_key` → `credentials.key` | `get_user_info`, `adopt/adopt/campaign_queries.py:13` | `Exception("Could not find credentials for study id: …")`, raised before anything else loads |

Two of these deserve their own warning.

**`strata[].audiences` does not point at `audiences[].name`.** It points at a
custom audience *on the Meta ad account*, matched by name
(`adopt/adopt/facebook/state.py:301`). The `audiences` conf is what *creates*
those audiences on Meta, but it does not always name them after itself
(`adopt/adopt/audiences.py:101-135`):

- `subtype: "CUSTOM"` → the audience is named `<name>`
- `subtype: "LOOKALIKE"` → creates `<name>-origin` *and*, once the origin holds
  at least `lookalike.target` users, `<name>`
- `subtype: "PARTITIONED"` → creates `<name>-cohort-1`, `<name>-cohort-2`, … and
  **never** a plain `<name>`

So a stratum naming a partitioned audience by its conf name will always dangle
and will always be dropped at INFO level. And on the *first* runs of any study,
before the audience cron has created anything on Meta, every audience reference
dangles and targeting is silently unfiltered.

**`general.credentials_entity` is inert.** `get_user_info`
(`campaign_queries.py:13`) selects it and then joins on `credentials.key` and
`user_id` only — `entity` is never used. The value the dashboard writes is
`"facebook"` with `credentials_key: "Facebook"`, both hardcoded
(`dashboard/src/pages/StudyConfPage/forms/general/General.tsx:26-27`), matching
the credential the Facebook OAuth exchange creates
(`api/internal/server/handler/facebook/token_test.go:25`). Copy those two
values unless you know otherwise.

### 1.4 Names are also Meta object names

The names you choose are not internal identifiers. Reconciliation matches live
Meta objects to desired ones **by name** (`_diff`,
`adopt/adopt/facebook/reconciliation.py:313`):

- `stratum.id` becomes the **ad set name** (`create_adset`,
  `adopt/adopt/marketing.py:111`)
- `creative.name` becomes the **ad name** (`create_ad`, `marketing.py:162`)
- `recruitment.ad_campaign_name` (or `<base>-<arm>`) becomes the **campaign
  name** (`base_campaign_name` on each of the three recruitment classes)

Therefore **renaming is deletion plus creation.** Change a `stratum.id` and the
next reconciliation deletes the old ad set — with its learning, its history and
its ads — and creates a new one. There is no rename. Choose ids and creative
names once.

`strata[].id` must additionally be unique across the list, which *is* checked,
though only at run time: `uniqueness` (`malaria.py:679`) raises
`Exception("Strata IDs combinations are not unique")`. Creative names are not
checked for uniqueness anywhere; duplicates collapse silently in a dict
(`malaria.py:737`, last one wins).

### 1.5 The `variables` conf is inert on the server

`StudyConf` (`adopt/adopt/study_conf.py`) declares `general`,
`destinations`, `audiences`, `creatives`, `strata`, `recruitment`,
`inference_data` and `data_sources`. **It has no `variables` field**, and it
sets no `model_config`, so pydantic's default `extra="ignore"` silently drops
the `variables` conf when `get_study_conf` (`malaria.py:58`) assembles the
study from the stored rows. (That default is unchanged on the load path, and
deliberately so — the `extra="forbid"` models added in v0.1.85 are used on
write only, §2.1.)

`variables` exists so the dashboard can regenerate strata from it and show a
staleness banner. Nothing in adopt reads it, and neither
`Level.template_campaign` / `Level.template_adset` nor
`CreativeConf.template_campaign` has a single read site under `adopt/` — they
are dashboard bookkeeping, read only by
`dashboard/src/pages/StudyConfPage/components/TemplateCampaignWrapper.tsx`.

**So: strata are the real configuration; variables are a convenience.** An
agent may skip `variables` entirely and POST strata directly. If you do write
`variables`, understand that nothing derives strata from it server-side. The
derivation is available in Python as `adopt.authoring.strata` (§6 step 7), a
conformance-tested port of the dashboard's TypeScript; it is a library call,
not an endpoint.

---

## 2. The endpoints

All paths are on the Python service. `{org_id}` is a UUID, `{slug}` is the
study's slug.

### 2.1 Writing a configuration section

```
POST /{org_id}/studies/{slug}/confs/{section}
Authorization: Bearer <api key>
Content-Type: application/json
```

| Section (path) | Stored `conf_type` | Body | Model |
|---|---|---|---|
| `general` | `general` | object | `GeneralConf` |
| `recruitment` | `recruitment` | object | `RecruitmentConf` (3-way union) |
| `destinations` | `destinations` | **array** | `list[DestinationConf]` |
| `creatives` | `creatives` | **array** | `list[CreativeConf]` |
| `audiences` | `audiences` | **array** | `list[AudienceConf]` |
| `variables` | `variables` | **array** | `list[VariableConf]` |
| `strata` | `strata` | **array** | `list[StratumConf]` |
| `data-sources` | `data_sources` | **array** | `list[DataSourceConf]` |
| `inference-data` | `inference_data` | object | `InferenceDataConf` |

Routes: the nine `create_*_conf` handlers in `adopt/adopt/server/server.py`.
Models: `adopt/adopt/study_conf.py`, and their write-time `extra="forbid"`
twins in `adopt/adopt/study_conf_strict.py`.

**Response — `201`.** The inserted row, `RETURNING *`:

```json
{"data": {"created": "...", "study_id": "...", "conf_type": "general",
          "conf": { …the stored configuration… }}}
```

**An unknown field is a `422` that names it.** Since adopt v0.1.85 the nine
POST routes validate through `extra="forbid"` models
(`adopt/adopt/study_conf_strict.py`), so a misspelled key is rejected rather
than accepted and discarded:

```json
{"detail": [{"type": "extra_forbidden",
             "loc": ["body", 0, "levels", 0, "facebok_targeting"],
             "msg": "Extra inputs are not permitted"}]}
```

`loc` is the full path to the offending key, so this works at any depth — a
typo inside `strata[].question_targeting.vars[]` is caught exactly like one at
the top level. Three kinds of key are still free-form by design and always will
be, because vlab does not own their vocabulary:

- **Meta spec objects** — `strata[].facebook_targeting`, `creatives[].template`.
  The keys are Meta's.
- **Connector config** — `data-sources[].config`, typed `Any`. Its shape depends
  on the `source` (a Typeform form id, a BigQuery dataset, …), so nothing is
  validated inside it and a typo there is still silent. §3's `data-sources`
  section has the per-source shapes.
- **User-chosen metadata** — `general.extra_metadata`, `strata[].metadata`,
  `destinations[].additional_metadata`. The keys are the researcher's.

Before v0.1.85 the models ran on pydantic's default, `extra="ignore"`: a typo'd
field name was not an error, it simply did not exist in the stored conf. If you
are talking to an older deployment, assume every optional field you send may
have been discarded, and read it back (§2.3) to find out.

**Reading is still lenient, deliberately.** The strict models are used on write
only. adopt loads stored confs through the *lenient* originals, so a conf
written before a field was removed still loads and still runs — otherwise
removing a field would halt reconciliation on every study that predates the
removal. Two names are on a closed list of retired fields that a write accepts
and drops rather than rejecting, because stored confs still carry them:
`recruitment.destination_type` (required until 2026-08-30) and
`destinations[].include_metadata_in_ref` (replaced by `ref_mode` on
2026-08-24). Do not send either in new configuration.

**Defaults are filled in.** `create_conf` stores `config.model_dump()`, not your
request body, so POSTing a `general` conf without `extra_metadata` stores
`"extra_metadata": {}`. Read the `201` body if you want to know what was
actually saved.

**Failure modes.**

| Condition | Result |
|---|---|
| Missing or wrong-typed field, unknown destination `type`, list where an object was expected | `422` with FastAPI's per-field detail — legible and actionable |
| **Unknown field, at any depth** | `422`, `type: "extra_forbidden"`, with the full path to the key in `loc`. Since adopt v0.1.85 — before that it was a `201` and the field was discarded |
| A recruitment body carrying fields from two arms (e.g. both `arms` and `destinations`) | `422` naming the field that does not belong to the arm. Since v0.1.85 — before that it silently became a `PipelineRecruitmentExperiment` |
| A model validator raising `InvalidConfigError` (bad WhatsApp phone number, unsafe `initial_shortcode`, invalid `audiences[].subtype`, invalid `partitioning` combination) | `422`, with the validator's message verbatim in the `detail`. Since adopt v0.1.84 — before that it was a bare `500`; see below |
| Study does not exist, or is not in `{org_id}`, or you are not in that org | `500`. The insert's study subselect yields `NULL` against a `NOT NULL` column |
| Unparseable auth | `401` |

> **`InvalidConfigError` is a `422` since adopt v0.1.84.** It used to derive
> from `BaseException` (`InvalidConfigError`, whose docstring records it), so pydantic did not
> wrap it in a `ValidationError`, Starlette's `except Exception` middleware
> did not see it, and uvicorn emitted a bare `500` with the explanatory
> message reaching only the server log. It now derives from `ValueError`, so
> pydantic wraps it and FastAPI returns `422` with the message in `detail`.
> If you are talking to a deployment older than v0.1.84, a `500` from a conf
> POST usually means "your configuration is wrong in a way the model knows
> how to describe, and you cannot see the description"; the models affected
> are `FlyWhatsAppDestination`, `FlyMultiDestination` (phone number,
> shortcode), `AudienceConf` (subtype), and `Partitioning`.

> **A missing study is also a `500`, not a `404`.** `create_study_conf`
> (`db.py:151`) inserts `(SELECT s.id FROM studies s JOIN orgs_lookup … )` as
> the `study_id`. With no matching study the subselect is `NULL` and
> `study_confs.study_id` is `NOT NULL`, so psycopg raises and nothing catches
> it. Confirm the study first with a read (§2.3) rather than reading a `500`
> as a transient failure. (Note: `planning/agent-study-authoring.md` §2.3 says
> this path "simply writes nothing"; the schema says otherwise.)

### 2.2 `POST /{org_id}/studies/{slug}/copy-from`

```json
{ "source_study_slug": "some-other-study" }
```

Copies the newest row of every conf type **except `general`** from the source
study into this one (`copy_confs`, `adopt/adopt/server/db.py:185`). `201` with
the copied confs; `404` if the source has no configuration to copy. This is
what the dashboard's "Initialize" step uses, and it is the fastest way to stand
up a study that resembles an existing one.

Both ends are scoped to your user and org. A destination slug that is not one
of your studies in this org is `404 {"detail": "Study not found: <slug>"}`
before anything is read; a source with nothing to copy is the `404` above.
(Before adopt v0.1.83 the destination was resolved by slug alone, with no user
or org predicate — slugs are unique per *user*, not globally — so naming a slug
you did not own wrote into somebody else's study. Fixed in `ee7e21f6`, with a
regression test in `adopt/adopt/server/test_copy_confs.py`.)

### 2.3 Reading

- `GET /{org_id}/studies/{slug}/confs` — newest row per conf type, as a map.
  The read you want. Raises (→ `500`) if the study has no confs at all.
- `GET /{org_id}/studies/{slug}/confs/{conf_type}` — one section. Since adopt
  v0.1.85 either spelling works: the URL segment you POSTed to
  (`confs/data-sources`) or the stored type name `GET /confs` returns as a key
  (`data_sources`). Before that only the stored name worked, so the one URL
  that could write those two sections was the one URL that could not read them
  back. Still raises (→ `500`) when the section is absent.
- `GET /{org_id}/studies/{slug}/ad-attributions` — the frozen (ad → stratum,
  creative, survey) mapping as a table .
- `GET /{org_id}/studies/{slug}/ad-attributions.csv` — the same, as a CSV
  download, for left-joining onto a survey export by `ad_id`
  . Every mapping row is included, including ads Meta no
  longer has.
- `GET /{org_id}/optimize/{slug}/errors` — current open errors and warnings for
  the study, derived from `study_run_events`: the newest event per
  `(source, fingerprint)` whose severity is `error` or `warning` and that was
  seen in the last 90 minutes (`db.py:18`). Errors sort before warnings.
  **This is the closest thing to a health check an agent has, and it is worth
  polling after any configuration change.** It degrades to an empty list rather
  than failing if the events table is absent.
  Its coverage is narrower than the name suggests: `study_run_events` is
  written only by swoosh, the data-extraction service
  (`inference/swoosh/events.go:37`, source `"inference"`). **adopt writes no
  events at all**, so nothing in §4 — the two warnings, a dangling creative
  name, a failed reconciliation — appears here. An empty error list is not
  evidence that ad building is healthy.
- `GET /{org_id}/optimize/{slug}/current-data` — the inference data rows the
  optimizer is currently reading (`get_current_data`).
- `GET /{org_id}/studies/{slug}/recruitment-stats` — per-stratum spend, reach,
  CPM, respondents, price per respondent. `404` if the study, its confs, or its
  strata are missing (`get_recruitment_stats`).
- `GET /{org_id}/studies/{slug}/segments-progress` — cumulative participants per
  stratum over time, from a pre-computed report. Returns `{"data": []}` when no
  report exists yet rather than failing (`get_segments_progress`).
- `GET /{org_id}/studies/{slug}/cost-over-time` — cumulative spend and marginal
  cost per respondent (`get_cost_over_time`).
- `GET /health` — `"OK"`, unauthenticated.

`recruitment-stats` and `segments-progress` read the **last stored report**,
not live Meta, so they are empty until an optimization run has happened.

### 2.4 `POST /{org_id}/studies` — creating a study

```
POST /{org_id}/studies
{ "name": "HPV vaccine uptake, Lagos 2026" }

201 { "data": { "id": "<uuid>", "name": "HPV vaccine uptake, Lagos 2026",
                "slug": "hpv-vaccine-uptake-lagos-2026", "createdAt": 1756944000000 } }
```

`adopt/adopt/server/studies.py`, a port of the Go handler
(`api/internal/server/handler/studies/create.go`, now marked deprecated)
that accepts an API key. Needs `studies:write`. Same rules as the dashboard:

- **Name** must not be blank (`400 "The name cannot be empty."`) and is capped
  at **300 UTF-8 bytes**, not characters (`400 "The name cannot be larger than
  300 characters."` — the wording is Go's, the count is bytes, so a long
  non-Latin name trips it early). Stored untrimmed.
- **Slug** is derived server-side with `slugify.py`, a verified port of
  `gosimple/slug` — the same function the dashboard uses, so the same name
  yields the same URL from either path. Lower-cased, transliterated,
  non-alphanumerics collapsed to `-`; **apostrophes and quotes are deleted, not
  replaced**, so `Nandan's study` is `nandans-study`. Read the slug from the
  `201`; you need it for every subsequent call.
- **Uniqueness** is per user, not per org: `409 "The name is already in use."`
  on a duplicate name, and a different name that slugifies onto a slug you
  already hold is `409` with a message that names the slug.
- A name that slugifies to nothing (emoji only, say) is `400`; the Go route
  would create an unaddressable study, this one refuses.
- `org_id` must be an org you belong to, else `404 "Organization not found"`
  — also for a malformed id. Membership is checked by the insert itself
  (`INSERT … SELECT FROM orgs_lookup WHERE user_id AND org_id`), so there is
  no window between check and write.

`createdAt` is milliseconds since the epoch, matching the dashboard.

### 2.5 `GET /{org_id}/meta/…` — reading Meta without a Facebook token

Three things you need before you can write a study live on Meta, not in vlab:
the ad account number for `general.ad_account`, a template ad set's `targeting`
(which becomes each variable level's `facebook_targeting`), and a template ad's
creative blob (which becomes `creatives[].template`, stored verbatim). Until
2026-09-05 the only way to get them was to hold the researcher's Facebook
token yourself. Now the server reads Meta for you, with the token it already
stores, and **you never see it**.

All of these are `GET`, all need `meta:read`, and all are read-only —
`adopt/adopt/server/meta.py`. The paths, `fields` and response nesting are
lifted from what the dashboard requests today (`dashboard/src/helpers/api.ts`),
so a creative blob read here is identical to one read in the browser.

| Route | Returns |
|---|---|
| `GET /{org}/meta/credentials` | your Facebook credentials by name — `[{key, entity, created}]`. Never tokens. |
| `GET /{org}/meta/adaccounts` | `[{id, account_id, name}]` — `account_id` is the bare number that goes in `general.ad_account`; `id` is the same prefixed `act_`. |
| `GET /{org}/meta/campaigns?account=<act_123 or 123>` | `[{id, name}]`, every campaign regardless of status — a template campaign is usually paused. |
| `GET /{org}/meta/adsets?campaign=<id>` | `[{id, name, targeting}]`. `targeting` is the whole point. |
| `GET /{org}/meta/ads?campaign=<id>` *or* `?adset=<id>` | `[{id, name, creative: {…}}]` — the creative arrives **nested**, via field expansion, exactly as the dashboard receives it. Exactly one of the two parameters. |
| `GET /{org}/meta/ads/{ad_id}/creative` | `{"data": {…creative…}}` — the one blob, when you already have an ad id. `404` if the ad has no readable creative (rather than a `null` you would store). |

**Which Facebook credential.** A user can hold more than one, and different
tokens see different ad accounts, so:

- Pass `?credentials_key=<name>` to choose. It takes exactly the value that
  goes into `general.credentials_key`, so you can point the proxy at the
  credential the study will actually run on.
- Omit it and you get your one Facebook credential, if you have exactly one.
- Omit it with more than one and the request is
  `409` naming them — the proxy will not pick, because a wrong pick surfaces
  hours later as an unexplained Meta rejection at ad-set create time.
  `GET /{org}/meta/credentials` lists the names.
- No Facebook credential at all is `400` with a message saying so. **A human
  must connect the account**; the OAuth exchange is Auth0-only (§6 step 1) and
  no API key can do it.

**Pagination.** Every list route returns

```json
{"data": [ … ], "paging": {"after": "<cursor|null>", "truncated": false, "pages_fetched": 2}}
```

Cursors are followed **server-side**, up to 10 pages. `truncated: true` means
the page cap stopped it, not Meta; pass `paging.after` back as `?after=<cursor>`
to continue. `truncated: false` means you have the whole collection and `after`
is `null`. `?limit=` defaults to 100, max 500, and multiplies with the page cap
— `limit=500` can pull 5,000 objects in one request, which for `/meta/ads` is a
lot of creative blobs.

**Errors.** Meta's rejections keep their identity rather than collapsing into a
`500`. `detail` here is an **object**, not a string:

```json
{"detail": {"message": "Meta rejected the request: Error validating access token: Session has expired.",
            "meta_error": {"code": 190, "subcode": null, "type": "OAuth",
                           "message": "…", "http_status": 400}}}
```

A Meta `400`/`403`/`404` passes its status through (bad id, object not visible
to this token, expired token — all yours to act on). Meta `429` and `5xx`, and
a Graph API that cannot be reached at all, become `502` with
`"meta_error": null` for the latter. Retry a `502`; do not retry a `400`.

A request that has not finished in 220 seconds is
`504 {"detail": "Operation timed out after 220 seconds"}` — the same decorator
the optimize routes use. You should never see it: the budget is the arithmetic
worst case of the page cap and the per-call socket timeout, so it fires only
when something upstream has genuinely hung. Note a `504` carries no
`paging.after`, so there is nothing to resume from; if you are near the cap,
lower `?limit=` rather than retrying identically.

**What this is not.** There is no write proxy — `meta:write` is expressible and
nothing serves it. There is no caching: every call is a live Graph read against
Meta's per-app rate limits, so do not poll these in a loop.

---

## 3. The nine conf types

Field lists are from `adopt/adopt/study_conf.py`. Everything without a stated
default is required. Conceptual documentation is linked per section; this is
the wire shape and the traps.

**Machine-readable schemas exist: `adopt/schemas/*.json`** — JSON Schema
(2020-12) generated from the same pydantic models, one file per wire conf type,
plus `index.json` mapping each to its endpoint and body kind, and
`study-conf.json` for the assembled whole. Regenerated by `make schemas` and
drift-checked in CI. Program against those; read this section for what the
schema cannot say. `adopt/README.md` ("JSON Schemas for study configuration")
lists the four things the models enforce that JSON Schema cannot express.

**The per-section files describe the WRITE shape**, i.e. what `POST` accepts:
they carry `"additionalProperties": false`, so validating your body against the
file tells you whether the server will take it. That is the shape you want when
you are about to send something. `study-conf.json` is the one exception and
says so in its `$comment` — it describes what adopt *loads*, which deliberately
still tolerates keys the models no longer declare, so it permits additional
properties where the others do not. A conf that validates on load and not
against these files is that asymmetry working, not drift.

### `general` — object

Concepts: <https://docs.vlab.digital/vlab/study-configuration/general/>

```json
{
  "name": "HPV Nigeria",
  "credentials_key": "Facebook",
  "credentials_entity": "facebook",
  "ad_account": "1234567890",
  "opt_window": 48,
  "extra_metadata": {}
}
```

`ad_account` is the numeric ad account id **without** the `act_` prefix — Meta's
`account_id`, not its `id`. `FacebookState` raises outright if the prefix is
present (`adopt/adopt/facebook/state.py:269`) and adds it back itself.
`opt_window` is in hours and is the lookback the optimizer uses for spend and
performance (`make_window`, `malaria.py:68`). `extra_metadata` is merged into
every ad's ref and into the frozen attribution blob, **after** the stratum's own
metadata, so a key present in both is won by `extra_metadata`
(`Stratum.metadata` assembly in `study_conf.py`). `credentials_key` must match a `credentials.key` row
belonging to the study's owner; `credentials_entity` is stored and never read
(§1.3).

### `recruitment` — object, a three-way union discriminated on `type`

Concepts: <https://docs.vlab.digital/vlab/study-configuration/recruitment/>

`RecruitmentConf` is `Union[SimpleRecruitment, PipelineRecruitmentExperiment,
DestinationRecruitmentExperiment]`, discriminated on `type` since adopt
v0.1.85:

| `type` | Class |
|---|---|
| `"simple"` | `SimpleRecruitment` |
| `"pipeline_experiment"` | `PipelineRecruitmentExperiment` |
| `"destination"` | `DestinationRecruitmentExperiment` |

**Send the tag.** It is not required — omit it and adopt infers the arm from
shape, which is what keeps the confs stored before the tag existed loading and
re-saving — but the tag is the only way to be certain which arm you get, and a
tagged body that carries a field from another arm is a `422` rather than a
different strategy than you asked for.

Common to all three: `objective`, `optimization_goal`, `min_budget`,
`start_date`, `end_date`, and the optional `incentive_per_respondent` (0),
`efficiency_weight` (1.0 — 1.0 is variance-focused, 0.0 cost-focused) and
`optimizer_version` (`"closed_form"` | `"lbfgs"`, default `closed_form`).

- **`SimpleRecruitment`** — `ad_campaign_name`, `budget`, `max_sample`. One
  campaign. This is the normal case.
- **`PipelineRecruitmentExperiment`** — `ad_campaign_name_base`,
  `budget_per_arm`, `max_sample_per_arm`, `arms`, `recruitment_days`,
  `offset_days`. Campaigns are `<base>-1` … `<base>-N`, staggered in time. Its
  end-date consistency check exists but is never called: `validate_dates`
  (`PipelineRecruitmentExperiment.validate_dates`) carries a `TODO: this is useless` because pydantic
  could not run root validators on a union arm.
- **`DestinationRecruitmentExperiment`** — `ad_campaign_name_base`,
  `budget_per_arm`, `max_sample_per_arm`, `destinations` (a list of destination
  names). Campaigns are `<base>-<destination>`, one arm per destination.

> **Over-specifying is now an error, and used to be silent.** A body carrying
> both the pipeline fields and `destinations` resolved to
> `PipelineRecruitmentExperiment` — union order won and `destinations` was
> dropped as an unknown field, so a study configured as a destination
> experiment could run as a pipeline one with nothing reporting it. Since
> v0.1.85 it is a `422` naming `destinations`. Send exactly the fields of the
> arm you want, and name the arm.

**`start_date` and `end_date` are the study's on/off switch.** The cron only
touches studies where `start_date < now < end_date`, via the `study_state` view
over the newest recruitment conf
(`devops/migrations/20230322111807_init.up.sql:92`,
`adopt/adopt/recruitment_data.py:271`). A study whose window has not opened, or
has closed, is invisible to every automated job — no ads, no optimization, no
errors.

`DestinationRecruitmentExperiment.destinations` entries are **not checked
against the destinations conf**. They are matched by substring against the
generated campaign names (`marketing.py:1158`, so arms `["wa", "wa2"]` are
ambiguous) and used to filter `creatives[].destination` (`marketing.py:1166`).
An arm no creative points at yields an ad set with no ads, which fails later
with a message about a stratum naming no creative (`marketing.py:1396-1399`) — a
misleading description of the actual cause. Arms also always divide the budget
by `len(destinations)`, whether or not each arm has creatives.

### `destinations` — array, discriminated on `type`

Concepts: <https://docs.vlab.digital/vlab/study-configuration/destination/>

Five types (`_TaggedDestination` in `study_conf.py`). All accept an optional
`ref_mode: "metadata" | "encoded"`; absent means `"metadata"`.

```json
[{"type": "messenger", "name": "mess", "initial_shortcode": "hpvintro",
  "welcome_message": "Welcome!", "button_text": "Start",
  "additional_metadata": {}},

 {"type": "whatsapp", "name": "wa", "initial_shortcode": "hpvintro",
  "welcome_message": "Welcome!", "whatsapp_phone_number": "+1-541-920-2635"},

 {"type": "multi", "name": "both", "initial_shortcode": "hpvintro",
  "welcome_message": "Welcome!", "button_text": "Start",
  "whatsapp_phone_number": "+1-541-920-2635"},

 {"type": "web", "name": "site", "url_template": "https://x.example/{ref}"},

 {"type": "app", "name": "app", "facebook_app_id": "…",
  "app_install_link": "…", "deeplink_template": "…",
  "app_install_state": "…", "user_device": [], "user_os": []}]
```

Traps, all documented at length in the model's own comments:

- **`type` is a discriminator and it is load-bearing. Send it.** It was a
  plain shape-matched union until 2026-08-30, and under that union every
  `multi` destination silently became a `messenger` destination
  (the comment above `_TaggedDestination`). An unknown `type` is a `422`.

  An **absent** `type` is read as `"messenger"`, on write as well as on read
  (`_default_missing_destination_type`), because 45 stored
  confs predate the field and still have to be re-saveable. That is a
  concession to the legacy corpus, not an API — the committed schemas mark
  `type` required, and new configuration should write it.

  It is nonetheless safe, and worth understanding why: a typeless body is
  defaulted to `messenger` and then validated against the messenger model,
  which since v0.1.85 forbids unknown fields. So anything that is not genuinely
  messenger-shaped is rejected on its own fields — a `whatsapp` body on
  `whatsapp_phone_number`, a `web` body on `url_template`. The `multi` case is
  the one that matters: it satisfies every field messenger requires, so no
  required-field check could ever catch it, and it fails on
  `whatsapp_phone_number` being an unknown key. Forbidding extras is what
  closed the 2026-08-30 hole; the tag being mandatory was never what closed
  it.
- **`"web"` and `"website"` are both accepted** and mean the same class
  (`WebDestination`). Both reached production.
- **`whatsapp_phone_number` is the phone number, not the `phone_number_id`.**
  It must be 7–15 digits after punctuation is stripped; sending an id is
  rejected with a `422` naming the field (§2.1).
- **`initial_shortcode` must be `[A-Za-z0-9_-]+`** for `whatsapp` and `multi`.
  fly recovers the shortcode from the ad's autofill text, which a human may
  also type by hand, and a literal space lands the respondent in a fallback
  survey belonging to someone else. Also a `422` (§2.1).
- **`ref_mode: "encoded"` requires a matching read.** See §4.

### `creatives` — array

Concepts: <https://docs.vlab.digital/vlab/study-configuration/creative/>

```json
[{"name": "creative-a",
  "destination": "mess",
  "template": { …a Meta ad creative blob… },
  "template_campaign": "optional, ignored by the server",
  "tags": null}]
```

`template` is the creative object read off an existing Meta ad — it is passed
through into the ad that gets created, with the ref, welcome message and
call-to-action injected according to the destination
(`create_creative`, `adopt/adopt/marketing.py:1023`). Read it with
`GET /{org_id}/meta/ads?campaign=<template_campaign>` and store `ad["creative"]`
verbatim (§2.5); the dashboard reads the same fields in the browser with the
researcher's token, so the two produce the same blob.

`template["actor_id"]` is read to derive the page id every audience is scoped
to (`adopt/adopt/audiences.py:150`); a template lacking it raises a bare
`KeyError("actor_id")`. `template_campaign` and `tags` have no read site under
`adopt/`.

### `audiences` — array

Concepts: <https://docs.vlab.digital/vlab/study-configuration/audience/>

```json
[{"name": "respondents", "subtype": "CUSTOM", "question_targeting": null,
  "lookalike": null, "partitioning": null}]
```

`subtype` is `"CUSTOM"`, `"LOOKALIKE"` or `"PARTITIONED"`, and each requires its
own sub-object (`AudienceConf.__post_init__`):

- `LOOKALIKE` requires `lookalike: {target: int, spec: {country, ratio,
  starting_ratio}}`
- `PARTITIONED` requires `partitioning: {min_users, min_days?, max_days?,
  max_users?}` in one of exactly three valid combinations — `{min_users}`,
  `{min_users, min_days}`, or `{min_users, max_users, max_days}`
  (`Partitioning.validate_scenario`)

Both of those raise `InvalidConfigError`, so a bad subtype, a missing
sub-object, or an invalid partitioning combination is a `422` carrying the
message (§2.1). And remember §1.3: the names these produce on Meta are not
always `name`.

> **`LOOKALIKE` and `PARTITIONED` could not be written at all before adopt
> v0.1.85.** `__post_init__` runs at `mode="before"`, so it saw your raw JSON,
> but it required the sub-object to already be a parsed `Lookalike` /
> `Partitioning` instance — which no request body can be. Every such POST was a
> `422` reading "requires a <class 'adopt.study_conf.Lookalike'> value", and a
> stored one would have broken `StudyConf` assembly on every cron run. Only
> `CUSTOM` worked. If you are on an older deployment, these two subtypes are
> unavailable over HTTP; there is no payload that gets past it.

### `variables` — array

Concepts: <https://docs.vlab.digital/vlab/study-configuration/variables/>

```json
[{"name": "gender", "properties": ["genders"],
  "levels": [{"name": "men", "template_campaign": "…", "template_adset": "…",
              "facebook_targeting": {"genders": [1]}, "quota": 0.5}]}]
```

Stored, never read by the server (§1.5).

### `strata` — array. The real configuration.

Concepts: <https://docs.vlab.digital/vlab/study-configuration/strata/>

```json
[{"id": "gender:men,age:25-34",
  "quota": 0.25,
  "creatives": ["creative-a"],
  "audiences": [],
  "excluded_audiences": ["respondents"],
  "facebook_targeting": {"genders": [1], "age_min": 25, "age_max": 34,
                         "geo_locations": {"countries": ["NG"]},
                         "targeting_automation": {"advantage_audience": 0}},
  "question_targeting": {"op": "and", "vars": [
      {"op": "equal", "vars": [{"type": "variable", "value": "gender"},
                               {"type": "constant", "value": "men"}]},
      {"op": "answered", "vars": [{"type": "variable", "value": "finished"}]}]},
  "metadata": {"gender": "men", "age": "25-34"}}]
```

- `id` is the ad set name (§1.4) and must be unique within the list.
- `quota` is a share, and the dashboard computes it as the product of the level
  quotas of the variables composing the stratum
  (`dashboard/src/pages/StudyConfPage/forms/strata/strata.ts:26`).
- `facebook_targeting` keys are validated at run time against Meta's
  `Targeting.Field` enum: an unknown key raises
  `Exception("Targeting config invalid, key: <k> does not exist!")`
  (`marketing.py:103`). This is *not* checked at write time.
  `targeting_automation: {advantage_audience: 0}` is forced on every ad set
  regardless of what you store (`marketing.py:119`) — Advantage+ audience
  expansion is deliberately never used, because it leaks delivery outside a
  geographic stratum.
- `question_targeting` is a tree of `{op, vars}` where a leaf is
  `{type: "variable" | "constant", value}`. The variable names must be produced
  by the `inference_data` conf (§4).
- `metadata` is the stratum's key/value identity. It rides in the ad's ref when
  `ref_mode` is `metadata`, and it is frozen into the ad_attributions row
  either way. Keys and values must survive fly's entry pattern if any
  WhatsApp-carrying destination is in `metadata` mode (§4).

### `data-sources` — array (stored as `data_sources`)

Concepts: <https://docs.vlab.digital/vlab/study-configuration/data_sources/>

```json
[{"name": "fly", "source": "typeform", "credentials_key": "…", "config": null}]
```

`source` and `credentials_key` are resolved by the Go connector, which selects
the study only when a `credentials` row matches `entity = source` and
`key = credentials_key` (`inference/connector/connector.go:52`). No match means
the study is silently never collected.

### `inference-data` — object (stored as `inference_data`)

Concepts: <https://docs.vlab.digital/vlab/study-configuration/data_extraction/>

```json
{"data_sources": {
   "fly": {
     "user_variable": null,
     "extraction_confs": [
       {"location": "variable", "mapping": "raw", "key": "q_gender",
        "name": "gender", "functions": [], "value_type": "categorical",
        "aggregate": "last"}]}}}
```

The outer keys must equal `data_sources[].name` entries (§1.3). Per
`ExtractionConf` (`study_conf.py`) and its consumer
(`inference/swoosh/inference_data.go`):

| Field | Values |
|---|---|
| `location` | `"variable"` or `"metadata"` — where to read (`inference_data.go:329`) |
| `mapping` | `"raw"` (default) or `"ad_table_lookup"`. The only field pydantic actually validates against a list (`ExtractionConf.mapping_must_be_known`) |
| `key` | for `raw`, the field or metadata key holding the value; for a lookup, the key holding the *token* (fly stamps it at `metadata.vt`) |
| `name` | the output variable name, and for a lookup also *which* stratum variable to pull from the frozen row |
| `functions` | `[]`, or entries `{function, params}` where `function` is `"select"`, `"vlab-kv-pair-select"` or `"regexp-extract"` (`inference_data.go:120`) |
| `value_type` | only `"continuous"` changes behaviour (cast to float, `extraction_functions.go:139`); `"categorical"`, `"metadata"`, `"existence"` are the other values used in this repo, and anything else passes the raw value through |
| `aggregate` | `"first"`, `"last"`, `"max"`, `"min"` — anything else is a run-time error in swoosh (`inference_data.go:247`) |

Only `mapping` is validated by pydantic. A misspelled `location`,
`value_type`, `aggregate` or `function` is accepted by the API and fails, or
silently mis-extracts, in swoosh.

---

## 4. What is validated, and what is not

**Read this twice.** It is the difference between a study that recruits and one
that spends money on nothing.

### Each POST validates one section, in isolation

`create_general_conf`, `create_strata_conf` and the other seven
(`adopt/adopt/server/server.py`) each parse *their* body against *their*
model and store it. Nothing looks at any other section. The complete
`StudyConf` — the object that carries every cross-section invariant — is only
constructed later, by `get_study_conf` (`adopt/adopt/malaria.py:58`) on the
optimize path, which is reached from the cron and from the endpoints in §5.

So:

> **A `201` means "this section parsed". It does not mean the study works.**
> You can POST nine perfectly valid sections that name each other incorrectly,
> receive nine `201`s, and have a study that will never create a single ad —
> and unless you ask for a plan (§5) you will not find out until a cron run
> hours later, in a log you cannot read. The study-errors endpoint will not
> tell you: adopt writes no events to it (§2.3).

The failure is not even uniform. From §1.3: a bad creative reference is a bare
`KeyError`; a bad destination reference is a clear `Exception`; a bad audience
reference is an INFO line and silently degraded targeting.

### Two checks are warnings that reach nobody

`update_ads_for_campaign` runs two whole-study checks
(`adopt/adopt/malaria.py:262-263`) and both are `logging.warning`:

- **`warn_on_incomplete_targeting`** (`malaria.py:208`) — a stratum whose
  `question_targeting` names a variable that no `inference_data` extraction conf
  produces. Such a predicate can never match: the stratum counts zero
  respondents and **the optimizer moves its budget to the strata that appear to
  be working.** Nothing errors, nothing appears in the dashboard, and the study
  looks like it is running.
- **`warn_on_thinned_ref_without_mapping`** (`malaria.py:226`) — a destination
  with `ref_mode: "encoded"` while no extraction conf uses
  `mapping: "ad_table_lookup"`. The ref no longer carries the stratum and
  nothing resolves the token, so **every** stratum counts zero and the
  optimizer reallocates on empty data.

Both are deliberately warnings (see the reasoning in `StudyConf`'s comments),
and both are invisible to the API. **They are your responsibility to check
before you write.** Concretely:

1. Collect every `{"type": "variable"}` value in every stratum's
   `question_targeting`. Every one of them must appear as an
   `extraction_confs[].name` in the `inference_data` conf.
2. If any destination sets `ref_mode: "encoded"`, at least one extraction conf
   must set `mapping: "ad_table_lookup"`.

You can run both checks locally against the pydantic models today —
`missing_targeting_variables` and `thins_its_ref_without_reading_the_mapping`
are pure functions over a `StudyConf`.

### One cross-section check is a hard failure — and it fails the whole study

`check_whatsapp_refs_are_deliverable` refuses a study
where a WhatsApp or multi destination in `metadata` mode could publish a
stratum whose metadata will not survive fly's entry pattern once
percent-encoded. It fails closed: the study creates **no ads at all**, rather
than ads that recruit people into the wrong survey.

Because it runs on `StudyConf` assembly, it fails at *optimize time*, not at
write time. A study broken this way accepts every POST and then produces
nothing.

### The failure timeline

```
  you POST            201  ──────────────────────────────▶  looks fine
                                                  │
  cron `adopt-ads`, every 2 hours at :30 ─────────┤
  (devops/values/toixo-prod.yaml:132-137)         │
                                                  ▼
                        load_basics → StudyConf assembly
                          ├─ cross-section validators raise    → whole study dead
                          ├─ two checks log a warning          → invisible
                          └─ hydrate_strata resolves names     → KeyError / Exception
```

### What you can do about it

1. **Construct `StudyConf` locally before you push.** Import
   `adopt.study_conf`, build the object from your nine sections plus an `id` and
   a `user` stub, and every cross-section validator runs instantly and for
   free. This is by far the highest-value thing an agent can do, and it costs
   nothing.
2. **Run the plan (§5) and read the instruction list.** It assembles the whole
   `StudyConf`, so every cross-section validator runs, and a failure comes back
   as `500 {"detail": "<the real message>"}`. It is the only way to see an
   adopt-side configuration failure over HTTP. If the list is empty when you
   expected ads, something is wrong.
3. **Poll `GET /{org}/optimize/{slug}/errors` after writing** — but know what
   it covers: swoosh's extraction errors only, never adopt's (§2.3).

---

## 5. Plan, review, apply

This is the best affordance vlab already has for an agent, and it maps cleanly
onto the shape an agent wants.

### `GET /{org_id}/optimize/{slug}` — plan

Computes the full instruction list for the study **and returns it without
executing anything**. `run_study_opt` (`adopt/adopt/server/server.py`)
calls `update_ads_for_campaign` and discards the report half; actual execution
lives in the cron's `run_updates` → `run_instructions` (`malaria.py:490`,
`:190`).

```json
{"data": [{"node": "adset", "action": "create", "id": null,
           "params": { … }}]}
```

`node` is one of `campaign`, `adset`, `ad`, `adcreative`, `custom_audience`;
`action` is `create`, `update`, `delete` or `add_users`
(`adopt/adopt/facebook/update.py:82`). `id` is set for updates and deletes.

Five-minute timeout (`async_timeout` on the route), `504` if exceeded, `500` with
`{"detail": "<message>"}` on any error — and this is the one place where a
run-time configuration failure is actually reported back to you in the
response body. **Use it as your validator.**

> **The "preview" is not side-effect-free.** `update_ads_for_campaign`
> (`malaria.py:251`) does five things before returning instructions: it calls
> `heal_ad_attributions`, which writes `ad_attributions` rows; it reads Meta
> (campaigns, ad sets, ads, custom audiences); it writes a
> `FACEBOOK_ADOPT` row to `adopt_reports`; and it writes a respondents-over-time
> and a cost-over-time report. It creates no Meta objects and spends no money,
> but it is a write, and on a large study it is a slow one.

### `POST /{org_id}/optimize/{slug}/instruction` — apply exactly one

```json
{"node": "adset", "action": "create", "id": null, "params": { … }}
```

`201 {"data": {"timestamp": "…", "instruction": { … }}}`. Failures are `500`
with `{"detail": "<message>"}`.

Post an instruction back **exactly as the plan returned it**. `params` is
handed to the Meta SDK verbatim (`GraphUpdater.execute`,
`adopt/adopt/facebook/update.py:82`). After an `ad`/`create` the handler
re-reads the campaign and heals attributions, because ads created one-at-a-time
through this path once went unmapped and their respondents were dropped
(`optimize_study`, with the incident in the comment).

### The loop is genuinely iterative, and you must re-plan between applies

Reconciliation is layered, and each layer only appears once the layer above it
exists on Meta:

- If the campaign does not exist, `update_instructions_for_campaign`
  (`marketing.py:1466-1472`) returns **exactly one** instruction —
  `campaign`/`create` — and returns early. Nothing else is planned.
- If the campaign exists but an ad set does not, the ad set's creator
  (`reconciliation.py:380`) emits only `adset`/`create`. **Its ads are not
  planned in the same pass**, because ads are only diffed for an ad set that
  matched an existing one (`reconciliation.py:373`).
- Only on a third pass, with the ad set live and matched by name, does
  `ad_dif` (`reconciliation.py:345`) emit `ad`/`create` with the real
  `adset_id`.

So the minimum path from a configured study to a live ad is
**plan → apply → plan → apply → plan → apply**. An instruction list you cached
five minutes ago is stale the moment you apply anything from it.

### You may not need to apply at all

The `adopt-ads` cron runs `malaria_ads.py` every two hours at :30
(`devops/values/toixo-prod.yaml:132`) and does the whole plan-and-apply loop
itself for every study inside its recruitment window. Applying instructions
by hand buys you immediacy and a chance to review; it is not required. If you
have written a correct configuration, waiting is a valid strategy — and the
cron's runs are what keeps the study reconciled thereafter.

---

## 6. End-to-end runbook

Steps 1 and 3 are one-time per researcher and **cannot be done by an agent**.
Everything else is the agent's.

1. **A human connects a Facebook account.** The OAuth exchange is
   `POST /facebook/token` on the *Go* service
   (`api/internal/server/server.go:89`), Auth0-only, driven from the dashboard's
   Accounts page. It writes a `credentials` row with `entity = "facebook"` and
   `key = "Facebook"`. Without it the study cannot resolve a Meta token and
   `get_user_info` fails before anything else runs.

2. **Create the study.** `POST /{org_id}/studies {"name": "…"}` on this
   service (§2.4), with your API key. Read the `slug` from the `201`; you need
   it for every subsequent call. (The dashboard still uses the Go route; the
   two derive identical slugs.)

3. **A human mints you an API key** (see Authentication — ask for
   `["studies:write", "meta:read", "optimize:read"]` unless you need to launch ads) and
   tells you the `org_id`. There is no endpoint an API key can call that lists organisations
   — `POST /users` on the Go service returns them (`{data: {id, orgs: [{id,
   name}]}}`) but is Auth0-only, and the dashboard keeps the current org in
   `sessionStorage['current-vlab-org']`, not in the URL. The org id has to be
   handed to you.

4. **Read whatever is already there.**
   `GET /{org_id}/studies/{slug}/confs`. On a fresh study this raises; treat
   that as "empty". Consider `copy-from` (§2.2) if a similar study exists.

5. **Write `general`.** `credentials_key: "Facebook"`,
   `credentials_entity: "facebook"`, the numeric `ad_account`, an `opt_window`
   in hours.

   Do not guess the first three. `GET /{org_id}/meta/credentials` (§2.5) gives
   you the `key` and `entity` of every Facebook credential this account holds —
   `"Facebook"`/`"facebook"` is the dashboard's hardcoded pair and the common
   case, but it is not guaranteed. `GET /{org_id}/meta/adaccounts` gives you
   `account_id`, which is what `ad_account` wants (the bare number, not the
   `act_`-prefixed `id`).

6. **Write `destinations`,** then **`creatives`** naming them, then
   **`audiences`**. Order does not matter to the server — nothing is checked
   across sections — but it matters to you, because you have to know the
   destination names before you can write creatives.

   The creative `template` blob is a Meta ad creative read off an existing ad.
   The dashboard reads it in the browser with the researcher's Facebook token;
   **you read it through the proxy** (§2.5), which requests the same fields and
   returns the same nesting:

   ```
   GET /{org_id}/meta/campaigns?account=<account_id>   -> pick the template campaign
   GET /{org_id}/meta/ads?campaign=<campaign_id>       -> [{id, name, creative: {…}}]
   ```

   Store `ad["creative"]` **verbatim** as the creative's `template`, and the
   campaign's id as `template_campaign`. Do not reshape it; adopt diffs the
   stored blob against the live ad field by field
   (`adopt/adopt/facebook/field_contract.py`), and an "improved" blob is a
   perpetual no-op rewrite. If you already have an ad id,
   `GET /{org_id}/meta/ads/{ad_id}/creative` returns just the blob.

7. **Write `strata`.** These are the real configuration (§1.5) and the hardest
   part. The dashboard derives them from `variables` with a cartesian product —
   quota as the product of level quotas, merged `facebook_targeting`, a
   per-stratum `metadata` map and a `question_targeting` predicate ANDing each
   level equality with an `answered` filter on the study's finish question
   (`createStrataFromVariables`,
   `dashboard/src/pages/StudyConfPage/forms/strata/strata.ts:53`). The same
   function exists in Python as
   `adopt.authoring.strata.create_strata_from_variables(variables,
   finish_question_ref, creatives, audiences, existing_strata)`, which takes
   and returns the JSON wire shapes and is held identical to the TypeScript by
   a replayed fixture set of 1,142 cases (`adopt/adopt/authoring/`). Use it,
   or hand-write the strata — hand-writing is legitimate, the server only ever
   stores what you send — but do not write a third derivation.

   The `facebook_targeting` values themselves come from a template ad set on
   Meta. Read the ad sets through the proxy and extract from one:

   ```
   GET /{org_id}/meta/adsets?campaign=<campaign_id>
   -> {"data": [{"id": "…", "name": "geo-lagos", "targeting": {…}}], "paging": {…}}
   ```

   ```python
   from adopt.authoring.extract import extract_from_adset

   adsets = resp["data"]
   adset = next(a for a in adsets if a["name"] == "geo-lagos")

   facebook_targeting = extract_from_adset(
       adset,
       ["geo_locations", "age_min", "age_max", "genders"],
   )
   # -> {"geo_locations": {…}, "age_min": 18, "age_max": 65, "genders": [1],
   #     "targeting_automation": {"advantage_audience": 0}}
   ```

   The ad set object goes in **unchanged** — `extract_from_adset` reads `id`
   and `targeting` off it and uses `name` for error messages, which is exactly
   the shape `/meta/adsets` returns, on purpose. It raises
   `PropertyMissingError` when a declared property is absent rather than
   defaulting, and unconditionally forces
   `targeting_automation: {advantage_audience: 0}` — a deliberate policy
   decision with a real failure behind it (Advantage audience expansion leaking
   delivery outside a geographic stratum), which is why it overwrites even a
   `targeting_automation` you asked for by name.

   Check `paging.truncated` before you conclude an ad set is not there: a
   truncated page means you are looking at part of the campaign.

   If you build targeting by hand instead, set `targeting_automation` yourself;
   adopt forces it at ad-set build time anyway (`marketing.py:119`), but your
   stored conf will otherwise disagree with what is deployed.

8. **Write `data-sources` and `inference-data`.** Then check, yourself, that
   every variable named in every stratum's `question_targeting` appears as an
   `extraction_confs[].name`. Nothing else will (§4).

9. **Write `recruitment` last.** Its `start_date`/`end_date` window is what
   makes the study visible to the crons (§3), so writing it last means the
   automation only sees a complete study.

10. **Validate.** Build a `StudyConf` locally from what you wrote (§4), then
    `GET /{org_id}/optimize/{slug}` and read the instruction list. On a fresh
    study a correct configuration returns exactly one `campaign`/`create` per
    campaign the recruitment conf names — one for `SimpleRecruitment`, one per
    arm for the two experiment types — and nothing else.

11. **Apply, re-plan, apply, re-plan, apply** (§5) — or wait up to two hours
    and let the cron do it.

12. **Watch.** Re-run the plan periodically — it is the only adopt-side health
    signal over HTTP. `GET /{org_id}/optimize/{slug}/errors` for swoosh's
    extraction problems (§2.3); `GET /{org_id}/studies/{slug}/recruitment-stats`
    and `/segments-progress` once a run has produced reports;
    `/ad-attributions.csv` to join respondents back to strata.

---

## 7. What an agent cannot do today

Stated plainly, because each of these will otherwise look like a bug in your
client.

1. **Discover its own `org_id`.** No API-key-reachable endpoint lists orgs.
2. **Write anything to Meta through vlab, or connect a Facebook account.**
   *Reading* Meta is solved — that is §2.5, and it is read-only by
   construction. But the OAuth exchange that creates the credential in the
   first place (`POST /facebook/token` on the Go service) is Auth0-only, so a
   human has to connect the account before the proxy has a token to read with.
   And nothing an API key can call writes to Meta except an optimize
   instruction (§5), which is a different thing entirely.
3. **Derive strata from variables *over HTTP*.** The compiler is a library
   (`adopt.authoring`, §6 step 7), not an endpoint; an agent that is not
   running Python has to call it out of process or hand-write strata. Do not
   use `adopt/adopt/configuration.py` for this: it is the pre-dashboard
   ancestor, marked superseded, and its output disagrees with the dashboard's
   in metadata keys, targeting refs, ids and quotas.
4. **Get a whole-study validation over HTTP.** The closest thing is the plan
   endpoint (§5), which is slow, reads Meta and writes rows.

---

## 8. What landed recently

### 2026-09-05 — adopt v0.1.85: unknown fields are a `422`

Not yet released; check the adopt version in `devops/values/toixo-prod.yaml`
before relying on any of it. The change with the widest blast radius for an
agent since this document was written.

**An unknown field is a `422` naming it, at any depth** — §2.1. The nine POST
routes validate through `extra="forbid"` twins of the models
(`adopt/adopt/study_conf_strict.py`), recursively, so a typo inside
`strata[].question_targeting.vars[]` or `variables[].levels[]` fails the same
way one at the top level does. Reading stays lenient, deliberately: adopt still
loads a stored conf carrying keys the models no longer declare, because
otherwise removing a field would halt reconciliation on every study written
before the removal. Two such retired names (`recruitment.destination_type`,
`destinations[].include_metadata_in_ref`) are accepted and dropped on write;
that list is closed and everything else is an error.

**A typeless destination is still read as `messenger`** — §3, unchanged, on
write as well as on read. Worth a line here because forbidding unknown fields
changes what that default can let through: a typeless body that is really a
`whatsapp`, `multi`, `web` or `app` destination now fails on its own
type-specific fields, so the default can only ever admit a genuinely
messenger-shaped conf. Write the `type` anyway; the schemas require it.

**The recruitment union is discriminated on `type`** — §3, §4. Values are
`simple`, `pipeline_experiment`, `destination`. Omitting the tag still works
(the arm is inferred from shape, which is what keeps existing confs saveable),
but a body carrying fields from two arms is now a `422` instead of silently
becoming a pipeline conf.

**`LOOKALIKE` and `PARTITIONED` audiences can be written as JSON at all** — §3.
They never could: a `mode="before"` validator required the sub-object to
already be a parsed pydantic instance, so every such POST was a `422` no
payload could satisfy, and a stored one would have broken `StudyConf` assembly
on every cron run.

**`GET /confs/data-sources` reads back what `POST /confs/data-sources` wrote** —
§2.3. Same for `inference-data`.

**The committed JSON Schemas describe the write shape** — §3. They now carry
`"additionalProperties": false`, so validating locally tells you whether the
server will accept the body. `study-conf.json` stays lenient and says so.

### 2026-09-05 — adopt v0.1.84: Phase 1, Phase 2, and `422` for `InvalidConfigError`

Three PRs, one release. Check the adopt version in
`devops/values/toixo-prod.yaml` before relying on any of it.

**`InvalidConfigError` is a `422`, not a `500`** (PR #255). Every conf POST
that trips a cross-field validator now returns the validator's message in
`detail` — §2.1's failure-mode table and the WhatsApp / audience / partitioning
notes in §4 were rewritten accordingly. The item that used to be §7.5 ("see why
a `500` happened") is closed. The `extra="ignore"` behaviour was unchanged in
this release and investigated in `planning/conf-extra-fields.md`; v0.1.85 above
is the fix.

**The strata compiler is Python** (PR #254): `adopt.authoring.strata` and
`adopt.authoring.extract`, held identical to the dashboard's TypeScript by a
replayed fixture set — §6 step 7. Three divergences the fixtures could not
reach (null saved quotas, non-string level names, an empty first stratum) were
found in review and fixed before merge; §12.5 of the planning doc has them.

**The Meta Graph proxy** (PR #256; Phase 2 of `planning/agent-study-authoring.md`,
§13 there records the decisions and what the plan got wrong):

- **`GET /{org_id}/meta/…`** — §2.5. Ad accounts, campaigns, ad sets, ads and
  creative blobs, read server-side with the researcher's stored Facebook token,
  which never reaches the caller. Paths and `fields` are the dashboard's, so a
  creative blob read here is identical to one read in the browser.
- **A `meta` scope resource** — folded into the table in "Authentication".
  `meta` is deliberately not implied by `studies`.
- **`GET /{org_id}/meta/credentials`** — the first API-key-reachable way to
  discover a valid `general.credentials_key`.

This closes the item that used to be §7.2 ("read anything from Meta through
vlab"). §7.3 narrows to "over HTTP": the compiler is a Python library, not an
endpoint.

### 2026-09-04 — Phase 0

Phase 0 of `planning/agent-study-authoring.md` shipped as PR #251 and was
deployed to production as adopt **v0.1.83** with migrations **v0.3.0** (helm
revision 142). This document was revised against that release; if a claim here
disagrees with `adopt/adopt/server/`, the code is right and the doc is stale.

- **Study creation on this service** — §2.4, §6 step 2.
- **Hardened API keys** — the whole of "Authentication": persisted `jti`,
  mandatory `exp`, scopes, list and revoke, and the legacy-key tombstone.
- **Committed JSON Schemas** — `adopt/schemas/*.json`, kept current by
  `make -C adopt check-schemas` in CI; folded into §3.
- **`copy-from` cross-tenant write fixed** — §2.2.

**Phase 1 landed the same day and released in v0.1.84 (above):** the strata
compiler and the ad-set targeting extractor as Python
(`adopt/adopt/authoring/strata.py`, `extract.py`), each TypeScript test
translated, plus a differential suite that replays 1,142 recorded runs of the
real TypeScript through the port (`dashboard/scripts/authoring-conformance.ts`
→ `conformance_fixtures.json` → `test_conformance.py`, regenerated with
`make -C adopt authoring-fixtures`). `configuration.py` is marked superseded.
See §6 step 7 and §12 of the planning doc.

What the plan claimed and implementation disproved is in §11 of the planning
doc; the defects found are in §11.4 there — items 1, 2, 3 and 5 are now fixed
(`InvalidConfigError` in v0.1.84; unknown fields, the untagged recruitment
union and the unreadable hyphenated conf type in v0.1.85), and item 7 records
the audience-subtype bug found while fixing item 2. Beyond Phase 0, the direction — a composable Python authoring SDK,
server-side Meta proxy endpoints, `POST /{org}/studies/{slug}/validate`, and an
MCP shim over the SDK — is recorded in the same document.

---

## 9. Known gaps

Marked here rather than guessed at.

- **The Meta proxy (§2.5) has never been run against real Meta.** Every test
  mocks `FacebookAdsApi.call`. The request shapes are copied from the
  dashboard's live calls and the error mapping is exercised against
  SDK-constructed `FacebookRequestError`s, but no response in this
  documentation was observed coming back from `graph.facebook.com`.
- ~~**Whether the deployed `conf-dashboard` has `FACEBOOK_APP_ID` and
  `FACEBOOK_APP_SECRET` was not verified.**~~ **Closed 2026-09-05.** Both are
  present on the production `vlab-conf-dashboard` deployment, supplied by the
  `facebook-envs` secret. Key names were inspected; values were not read.
- **The Graph API version the proxy uses is the SDK's**, currently `v22.0`
  (`facebook-business = "v22"`), which happens to match the dashboard's
  `REACT_APP_FACEBOOK_API_VERSION`. Nothing enforces that they stay in step,
  and a third place (`adopt/adopt/facebook/update.py:34`) hardcodes `v20.0`.
- **Meta's real page-size ceiling per edge is unmeasured.** `?limit=` is capped
  at 500 as a guard against absurd requests, not because Meta accepts 500
  everywhere; Meta may quietly return fewer.
- **Exact HTTP status for an `InvalidConfigError` in production is inferred,
  not observed.** The exception provably escapes FastAPI (measured with a
  `TestClient` against `list[DestinationConf]`), and the installed uvicorn's
  `BaseException` handler emits a `500`
  (`adopt/.venv/.../uvicorn/protocols/http/h11_impl.py:411`). The behaviour
  behind the deployed ingress was not observed.
- **The `500` on a POST to a nonexistent study is inferred from the schema**
  (`study_confs.study_id` is `NOT NULL`, the subselect yields `NULL`), not
  observed at run time. It is definitely not a `404`.
- **`value_type` vocabulary.** Only `"continuous"` has a behaviour
  (`inference/swoosh/extraction_functions.go:139`). `"categorical"`,
  `"metadata"` and `"existence"` appear in this repo's tests and fixtures; the
  full set of values used operationally is undetermined, and nothing validates
  it.
- **`AppDestination` field semantics.** `app_install_state`, `user_device` and
  `user_os` are passed through to Meta; their accepted values were not traced
  and no App destination fixture was found.
- **`CreativeConf.tags`** has no read site under `adopt/` and no consumer was
  identified. Treat it as free-form annotation.
- **`recruitment.objective` and `optimization_goal`** are free strings; the
  valid pairs are Meta's, and adopt deliberately does not guess on Meta's
  behalf — a `CONVERSATIONS` check for multi-destination studies was removed
  on 2026-08-30 after Meta was measured to accept a pairing its own
  documentation forbids (the "NO optimization_goal CHECK" comment in
  `StudyConf`). Meta reports the real
  constraint at ad-set create time, which means at apply time (§5), not at
  write time.
- **Whether the dashboard validates cross-section names client-side** before
  POSTing was not audited. It does not matter for an API caller — the server
  does not — but it explains why these dangling references are rare in
  dashboard-built studies.
- **`studies.credentials_key` / `credentials_entity` columns** exist on the
  table with a foreign key
  (`devops/migrations/20230322111807_init.up.sql:86`) but the Go create path
  leaves them `NULL` and Facebook credentials are resolved from the `general`
  conf instead (`campaign_queries.py:13`). Whether anything still reads the
  columns is undetermined; nothing in `adopt/` does.
- **How many stored confs carry a retired key is unmeasured.** Two names are
  provably once-declared-and-removed (`recruitment.destination_type`,
  `destinations[].include_metadata_in_ref`) and are accepted-and-dropped on
  write for that reason (§2.1). Whether any *other* key is out there — from the
  notebook era, or propagated between studies by `copy-from`, which copies
  stored JSON verbatim — was not checked against production data. If one exists,
  it is now a `422` on the first re-save of that conf, naming the key.
  `planning/conf-extra-fields.md` §5 sketches the query that would say.
- **`PipelineRecruitmentExperiment` end-date consistency is unenforced.**
  `validate_dates` (`PipelineRecruitmentExperiment.validate_dates`) exists, carries a
  `TODO: this is useless`, and is called from nowhere. An inconsistent
  `arms`/`offset_days`/`recruitment_days`/`end_date` combination is accepted
  silently; what it does to the wave arithmetic at run time was not traced.
