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
| Owns | studies (create/list/read), users, orgs, accounts and credentials, the Facebook OAuth exchange, one legacy segments-progress route | **all study configuration**, optimize, instructions, study errors, ad attributions, recruitment stats, API-key minting |
| Auth | Auth0 RS256 **only** (`api/internal/server/server.go:43`) | Auth0 RS256 **or** a vlab API key |

**Everything in this document is on the Python service** unless it says
otherwise. An API key is accepted on every route there and on no route on the
Go service.

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
Authorization: Bearer <Auth0 access token>
{ "name": "hpv-agent" }

201 { "data": { "name": "hpv-agent", "id": "<uuid>", "token": "eyJ…" } }
```

`adopt/adopt/server/server.py:497`, minting in
`generate_api_token` (`adopt/adopt/server/auth.py:21`).

Note the bootstrap: **minting a key requires a token you already have**, and
today that is an Auth0 token, which means a browser login. The dashboard has a
button for it (`generateApiKey`, `dashboard/src/helpers/api.ts:292`). An agent
cannot mint its own first key; a human hands it one.

The key is an HS256 JWT carrying `iss`, `aud`, `iat`, `jti`, `sub` (the user
id), `https://vlab.digital/token-name` and `type: "api_key"`. Send it as
`Authorization: Bearer <token>` on every request. `verify_tokens`
(`auth.py:157`) tries the Auth0 RS256 verifier first and falls back to the
HS256 API-key verifier, so no route needed per-route work to accept keys and
every route accepts them.

### What the key is today, honestly

All four of these are visible in `generate_api_token` and
`verify_api_token` (`adopt/adopt/server/auth.py:21`, `:50`):

- **No expiry.** The payload has `iat` and no `exp`. Keys are eternal.
- **No revocation.** A `jti` is generated, put in the token, and thrown away —
  nothing is persisted, so nothing can be checked. There is a
  `# TODO: check payload ("id") against blacklist / whitelist` at `auth.py:62`
  marking exactly this gap.
- **No scopes.** A key *is* the user. A key handed to an agent can read every
  respondent's data and mutate every study that user owns.
- **No listing.** There is no endpoint that says which keys exist.

Treat an API key as a permanent, unrestricted credential for the account.
Handing one to an agent is handing over the account, permanently.

> **This section is scheduled to change.** Hardened keys — persisted `jti`,
> bounded TTL, `<resource>:<action>` scopes, list and revoke endpoints — are
> being built now (§8). Nothing above describes them; it describes what is
> deployed.

### Failures

A token that verifies as neither Auth0 nor an API key is
`401 {"detail": "Could not validate credentials"}` with a
`WWW-Authenticate: Bearer` header (`adopt/adopt/server/deps.py:30`). The
response never distinguishes which verifier rejected it.

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
are stored as `data_sources` and `inference_data`
(`adopt/adopt/server/server.py:187`, `:197`). Reading back with the hyphenated
form finds nothing and raises, which surfaces as a `500`. Use `confs` and read
the map.

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
| `strata[].question_targeting` variables → `ExtractionConf.name` | `missing_targeting_variables`, `adopt/adopt/study_conf.py:1269` | **`logging.warning` only** (§4) |
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
  name** (`study_conf.py:656`, `:731`, `:823`)

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

`StudyConf` (`adopt/adopt/study_conf.py:1071`) declares `general`,
`destinations`, `audiences`, `creatives`, `strata`, `recruitment`,
`inference_data` and `data_sources`. **It has no `variables` field**, and it
sets no `model_config`, so pydantic's default `extra="ignore"` silently drops
the `variables` conf when `get_study_conf` (`malaria.py:58`) assembles the
study from the stored rows.

`variables` exists so the dashboard can regenerate strata from it and show a
staleness banner. Nothing in adopt reads it, and neither
`Level.template_campaign` / `Level.template_adset` nor
`CreativeConf.template_campaign` has a single read site under `adopt/` — they
are dashboard bookkeeping, read only by
`dashboard/src/pages/StudyConfPage/components/TemplateCampaignWrapper.tsx`.

**So: strata are the real configuration; variables are a convenience.** An
agent may skip `variables` entirely and POST strata directly. If you do write
`variables`, understand that nothing derives strata from it server-side — the
derivation lives in browser TypeScript (§7).

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

Routes: `adopt/adopt/server/server.py:110-197`. Models:
`adopt/adopt/study_conf.py`.

**Response — `201`.** The inserted row, `RETURNING *`:

```json
{"data": {"created": "...", "study_id": "...", "conf_type": "general",
          "conf": { …the stored configuration… }}}
```

**The server normalises what you send, and the normalisation is lossy.**
`create_conf` (`server.py:100`) stores `config.model_dump()`, not your request
body. Two consequences:

- **Unknown keys are silently dropped.** pydantic's default is `extra="ignore"`
  and `model_dump()` emits only declared fields. A typo'd field name is not an
  error; it simply does not exist in the stored conf. Verified against
  pydantic 2.5.2 with `StratumConf`.
- **Defaults are filled in.** POSTing a `general` conf without `extra_metadata`
  stores `"extra_metadata": {}`. Read the `201` body if you want to know what
  was actually saved.

**Failure modes.**

| Condition | Result |
|---|---|
| Missing or wrong-typed field, unknown destination `type`, list where an object was expected | `422` with FastAPI's per-field detail — legible and actionable |
| A model validator raising `InvalidConfigError` (bad WhatsApp phone number, unsafe `initial_shortcode`, invalid `audiences[].subtype`, invalid `partitioning` combination) | **`500 Internal Server Error` with the body `Internal Server Error` and no explanation.** See below |
| Study does not exist, or is not in `{org_id}`, or you are not in that org | `500`. The insert's study subselect yields `NULL` against a `NOT NULL` column |
| Unparseable auth | `401` |

> **`InvalidConfigError` does not become a `422`.** It derives from
> `BaseException`, not `ValueError` (`adopt/adopt/study_conf.py:930`), so
> pydantic does not wrap it in a `ValidationError` and Starlette's error
> middleware — which catches `Exception` — does not see it either. uvicorn's
> catch-all (`h11_impl.py:411`) logs it and emits a bare `500`. **The
> explanatory message, which is often excellent, only reaches the server log.**
> Measured by driving `list[DestinationConf]` through a FastAPI `TestClient`.
> A `500` from a conf POST therefore usually means "your configuration is
> wrong in a way the model knows how to describe, and you cannot see the
> description". The models that behave this way are:
> `FlyWhatsAppDestination`, `FlyMultiDestination` (phone number, shortcode),
> `AudienceConf` (subtype), and `Partitioning`.

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

Two caveats. The source is scoped to your user and org; **the destination is
not** — the insert resolves it with a bare
`(SELECT id FROM studies WHERE slug = %s)`, with no user or org predicate and
no `LIMIT`. Slugs are unique per user (`unique_slug UNIQUE(user_id, slug)`,
`devops/migrations/20230322111807_init.up.sql:14`), not globally, so if anyone
else owns a study with the same slug the call either writes to the wrong study
or fails outright on a multi-row subquery. Prefer explicit section POSTs when
the slug is not distinctive.

### 2.3 Reading

- `GET /{org_id}/studies/{slug}/confs` — newest row per conf type, as a map.
  The read you want. Raises (→ `500`) if the study has no confs at all.
- `GET /{org_id}/studies/{slug}/confs/{conf_type}` — one section, by the
  *stored* type name (§1.2). Raises (→ `500`) when absent.
- `GET /{org_id}/studies/{slug}/ad-attributions` — the frozen (ad → stratum,
  creative, survey) mapping as a table (`server.py:264`).
- `GET /{org_id}/studies/{slug}/ad-attributions.csv` — the same, as a CSV
  download, for left-joining onto a survey export by `ad_id`
  (`server.py:236`). Every mapping row is included, including ads Meta no
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
  optimizer is currently reading (`server.py:401`).
- `GET /{org_id}/studies/{slug}/recruitment-stats` — per-stratum spend, reach,
  CPM, respondents, price per respondent. `404` if the study, its confs, or its
  strata are missing (`server.py:559`).
- `GET /{org_id}/studies/{slug}/segments-progress` — cumulative participants per
  stratum over time, from a pre-computed report. Returns `{"data": []}` when no
  report exists yet rather than failing (`server.py:672`).
- `GET /{org_id}/studies/{slug}/cost-over-time` — cumulative spend and marginal
  cost per respondent (`server.py:741`).
- `GET /health` — `"OK"`, unauthenticated.

`recruitment-stats` and `segments-progress` read the **last stored report**,
not live Meta, so they are empty until an optimization run has happened.

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
(`study_conf.py:1154`). `credentials_key` must match a `credentials.key` row
belonging to the study's owner; `credentials_entity` is stored and never read
(§1.3).

### `recruitment` — object, an untagged three-way union

Concepts: <https://docs.vlab.digital/vlab/study-configuration/recruitment/>

`RecruitmentConf` is `Union[SimpleRecruitment, PipelineRecruitmentExperiment,
DestinationRecruitmentExperiment]` (`study_conf.py:873`) with **no
discriminator field**. pydantic tells the arms apart by shape, so the field set
you send selects the arm.

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
  (`study_conf.py:714`) carries a `TODO: this is useless` because pydantic
  could not run root validators on a union arm.
- **`DestinationRecruitmentExperiment`** — `ad_campaign_name_base`,
  `budget_per_arm`, `max_sample_per_arm`, `destinations` (a list of destination
  names). Campaigns are `<base>-<destination>`, one arm per destination.

> **The union is ambiguous if you over-specify.** A body carrying both the
> pipeline fields and `destinations` resolves to
> `PipelineRecruitmentExperiment` — union order wins and `destinations` is
> silently dropped. Measured against pydantic 2.5.2. Send exactly the fields of
> the arm you want.

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

Five types (`study_conf.py:526`). All accept an optional
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

- **`type` is a discriminator and it is load-bearing.** It was a plain
  shape-matched union until 2026-08-30, and under that union every `multi`
  destination silently became a `messenger` destination
  (`study_conf.py:496-525`). An unknown `type` is now a `422`; an *absent*
  `type` is defaulted to `messenger`, because 45 stored confs predate the field
  (`_default_missing_destination_type`, `study_conf.py:478`).
- **`"web"` and `"website"` are both accepted** and mean the same class
  (`study_conf.py:168`). Both reached production.
- **`whatsapp_phone_number` is the phone number, not the `phone_number_id`.**
  It must be 7–15 digits after punctuation is stripped; sending an id is
  rejected. The rejection is an `InvalidConfigError`, so it arrives as an
  unexplained `500` (§2.1).
- **`initial_shortcode` must be `[A-Za-z0-9_-]+`** for `whatsapp` and `multi`.
  fly recovers the shortcode from the ad's autofill text, which a human may
  also type by hand, and a literal space lands the respondent in a fallback
  survey belonging to someone else. Also an `InvalidConfigError` → `500`.
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
(`create_creative`, `adopt/adopt/marketing.py:1023`). Reading that blob is
today a browser operation with the researcher's Facebook token (§7).

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
own sub-object (`AudienceConf.__post_init__`, `study_conf.py:1028`):

- `LOOKALIKE` requires `lookalike: {target: int, spec: {country, ratio,
  starting_ratio}}`
- `PARTITIONED` requires `partitioning: {min_users, min_days?, max_days?,
  max_users?}` in one of exactly three valid combinations — `{min_users}`,
  `{min_users, min_days}`, or `{min_users, max_users, max_days}`
  (`Partitioning.validate_scenario`, `study_conf.py:956`)

Both of those raise `InvalidConfigError`, so a bad subtype or an invalid
partitioning combination is an unexplained `500` (§2.1). And remember §1.3: the
names these produce on Meta are not always `name`.

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
`ExtractionConf` (`study_conf.py:35`) and its consumer
(`inference/swoosh/inference_data.go`):

| Field | Values |
|---|---|
| `location` | `"variable"` or `"metadata"` — where to read (`inference_data.go:329`) |
| `mapping` | `"raw"` (default) or `"ad_table_lookup"`. The only field pydantic actually validates against a list (`study_conf.py:69`) |
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
(`adopt/adopt/server/server.py:110-197`) each parse *their* body against *their*
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

Both are deliberately warnings (see the reasoning at `study_conf.py:1276`),
and both are invisible to the API. **They are your responsibility to check
before you write.** Concretely:

1. Collect every `{"type": "variable"}` value in every stratum's
   `question_targeting`. Every one of them must appear as an
   `extraction_confs[].name` in the `inference_data` conf.
2. If any destination sets `ref_mode: "encoded"`, at least one extraction conf
   must set `mapping: "ad_table_lookup"`.

You can run both checks locally against the pydantic models today —
`missing_targeting_variables` and `thins_its_ref_without_reading_the_mapping`
are pure functions over a `StudyConf` (`study_conf.py:1231`, `:1269`).

### One cross-section check is a hard failure — and it fails the whole study

`check_whatsapp_refs_are_deliverable` (`study_conf.py:1110`) refuses a study
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
executing anything**. `run_study_opt` (`adopt/adopt/server/server.py:281`)
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

Five-minute timeout (`server.py:357`), `504` if exceeded, `500` with
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
with `{"detail": "<message>"}` (`server.py:469`).

Post an instruction back **exactly as the plan returned it**. `params` is
handed to the Meta SDK verbatim (`GraphUpdater.execute`,
`adopt/adopt/facebook/update.py:82`). After an `ad`/`create` the handler
re-reads the campaign and heals attributions, because ads created one-at-a-time
through this path once went unmapped and their respondents were dropped
(`server.py:326`, with the incident in the comment).

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

Steps 1–3 are one-time per researcher and **cannot be done by an agent today**.
Steps 4 onward are the agent's.

1. **A human connects a Facebook account.** The OAuth exchange is
   `POST /facebook/token` on the *Go* service
   (`api/internal/server/server.go:89`), Auth0-only, driven from the dashboard's
   Accounts page. It writes a `credentials` row with `entity = "facebook"` and
   `key = "Facebook"`. Without it the study cannot resolve a Meta token and
   `get_user_info` fails before anything else runs.

2. **A human creates the study.** `POST /{org}/studies {"name": "…"}` on the
   **Go** service (`api/internal/server/handler/studies/create.go`), Auth0
   only. Name is capped at 300 characters, must not be blank, and must be
   unique per user (`409 {"error": "The name is already in use."}`). The slug
   is derived with `gosimple/slug` (`api/internal/storage/study.go:110`) — you
   need it for every subsequent call, so read it from the `201`.

3. **A human mints you an API key** (see Authentication) and tells you the
   `org_id`. There is no endpoint an API key can call that lists organisations
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

6. **Write `destinations`,** then **`creatives`** naming them, then
   **`audiences`**. Order does not matter to the server — nothing is checked
   across sections — but it matters to you, because you have to know the
   destination names before you can write creatives.

   The creative `template` blob is a Meta ad creative read off an existing ad.
   Today the dashboard reads it in the browser with the researcher's Facebook
   token (`GET /<campaign>/ads?fields=id,name,creative{…}`,
   `dashboard/src/helpers/api.ts:610`); the backend never sees Facebook here.
   **An agent must either read it from Meta itself with a token it has been
   given, or be handed the blob.** There is no vlab endpoint that returns it.

7. **Write `strata`.** These are the real configuration (§1.5) and the hardest
   part. The dashboard derives them from `variables` with a cartesian product —
   quota as the product of level quotas, merged `facebook_targeting`, a
   per-stratum `metadata` map and a `question_targeting` predicate ANDing each
   level equality with an `answered` filter on the study's finish question
   (`createStrataFromVariables`,
   `dashboard/src/pages/StudyConfPage/forms/strata/strata.ts:53`). That code
   runs in React and is reachable from nowhere else, so **an agent must
   reproduce the derivation or hand-write the strata**. Hand-writing is
   legitimate — the server only ever stores what you send.

   The `facebook_targeting` values themselves come from a template ad set on
   Meta, read in the browser and passed through `extractFromAdset`
   (`dashboard/src/pages/StudyConfPage/forms/variables/extract.ts`), which
   throws if a declared property is missing and unconditionally forces
   `targeting_automation: {advantage_audience: 0}`. If you build targeting by
   hand, set that key yourself; adopt forces it at ad-set build time anyway
   (`marketing.py:119`), but your stored conf will otherwise disagree with what
   is deployed.

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

1. **Create a study.** Study creation is Auth0-only on the Go service (§6
   step 2). An API key cannot bring a study into existence.
2. **Discover its own `org_id`.** No API-key-reachable endpoint lists orgs.
3. **Read anything from Meta through vlab.** Ad accounts, campaigns, ad sets
   and creative blobs are all read client-side from `graph.facebook.com` with
   the researcher's stored Facebook token (`facebookRequest`,
   `dashboard/src/helpers/api.ts:412`). vlab proxies none of it. An agent that
   needs a creative template or a template ad set's targeting must talk to Meta
   directly, with a token it was given.
4. **Derive strata from variables.** The compiler is browser TypeScript (§6
   step 7). There is an older Python ancestor at
   `adopt/adopt/configuration.py`, but **it disagrees with the TypeScript** —
   different metadata keys (`stratum_<var>` vs `<var>`), different targeting
   variable refs, quotas from an Excel share lookup rather than a product of
   level quotas — and nothing imports it outside its own test. Do not treat it
   as the reference implementation; production studies are built with the
   TypeScript.
5. **Get a whole-study validation over HTTP.** The closest thing is the plan
   endpoint (§5), which is slow, reads Meta and writes rows.
6. **See why a `500` happened** on a conf POST whose model raised
   `InvalidConfigError` (§2.1).

---

## 8. Landing shortly — a revision list

Work in flight at the time of writing (2026-09-04) that will make parts of this
document wrong. Nothing here is deployed; do not code against it.

- **Study creation on the FastAPI service.** `POST /{org_id}/studies` on the
  Python service, so an API key can create a study. Will retire §6 step 2 and
  §7.1.
- **Hardened API keys.** Persisted `jti` for real revocation, a bounded `exp`,
  `<resource>:<action>` scopes with absent-means-unrestricted, plus list and
  revoke endpoints. Will rewrite most of "Authentication". Migrations for it
  were present but uncommitted in this worktree
  (`devops/migrations/20260904000000_api_token_hardening.up.sql`).
- ~~Committed JSON Schemas.~~ **Landed** as `489bc680` while this was being
  written; folded into §3.

Beyond Phase 0, the direction — a composable Python authoring SDK, server-side
Meta proxy endpoints, `POST /{org}/studies/{slug}/validate`, and an MCP shim
over the SDK — is recorded in `planning/agent-study-authoring.md`.

---

## 9. Known gaps

Marked here rather than guessed at.

- **Exact HTTP status for an `InvalidConfigError` in production is inferred,
  not observed.** The exception provably escapes FastAPI (measured with a
  `TestClient` against `list[DestinationConf]`), and the installed uvicorn's
  `BaseException` handler emits a `500`
  (`adopt/.venv/.../uvicorn/protocols/http/h11_impl.py:411`). The behaviour
  behind the deployed ingress was not observed.
- **The `500` on a POST to a nonexistent study is inferred from the schema**
  (`study_confs.study_id` is `NOT NULL`, the subselect yields `NULL`), not
  observed at run time. It is definitely not a `404`.
- **`copy-from`'s unscoped destination lookup** is read out of the SQL
  (`db.py:201`). What it does when two users hold the same slug — a wrong-study
  write or a multi-row-subquery error — was not exercised.
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
  documentation forbids (`study_conf.py:1093`). Meta reports the real
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
- **`PipelineRecruitmentExperiment` end-date consistency is unenforced.**
  `validate_dates` (`study_conf.py:714`) exists, carries a
  `TODO: this is useless`, and is called from nowhere. An inconsistent
  `arms`/`offset_days`/`recruitment_days`/`end_date` combination is accepted
  silently; what it does to the wave arithmetic at run time was not traced.
