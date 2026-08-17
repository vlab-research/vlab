# Ad attributions: vlab owns the ad → stratum join

**Status:** complete. A1/A2 write the mapping, A5–A7 read it, C1 lets a
researcher declare an ad-derived variable in the dashboard, A3 exports the
mapping as CSV, A8/A9 add click-to-WhatsApp, and A4 lets a study stop shipping
its stratum vocabulary in the ref at all. Every part is per-study and opt-in:
nothing existing changes until someone changes it. The one piece outstanding is
the dashboard form for the WhatsApp destination type.

vlab creates exactly one ad per (creative, stratum) pair. The ad's id therefore
already determines its shortcode, its creative and its stratum metadata — which
means the dotted `ref` string vlab has historically encoded that identity into
and shipped to the survey platform inside *every message* was a redundant copy
of a fact vlab already knew.

`ad_attributions` is where vlab keeps that fact instead: a row per created ad,
mapping `(network, ad_id)` to the shortcode, creative name and stratum metadata
that ad was published with.

End to end:

```
adopt creates ad      -> Meta returns ad_id
                      -> ad_attributions row frozen  (A1/A2, Python)

respondent arrives    -> fly resolves one ad identifier and exposes it
                         Messenger: referral.ad_id
                         WhatsApp:  referral.source_id, when source_type == 'ad'

fly connector         -> copies it onto InferenceDataEvent.AdID,
                         derives AdNetwork                      (A5, Go)

swoosh                -> joins ad_id -> frozen metadata,
                         emits the study's declared variables   (A6, Go)
                      -> counts organic vs unmapped             (A7, Go)
```

## What changed, and what deliberately did not

Purely additive. **No existing study's ad-creation behaviour changes.** In
particular `make_ref` and the ref emission inside `create_creative` are
untouched, and that is a constraint rather than an oversight: reconciliation
compares creatives via `field_contract.COMPARED_AD`, so altering a creative
rewrites every ad across every live study on the next run. Existing studies keep
the dotted ref indefinitely and are never migrated.

## The write path (adopt, Python)

Everything up to the Graph API call is pure; only the last step touches a
database.

| # | Where | What happens |
|---|---|---|
| 1 | `marketing.ad_provenance` | Builds a lookup keyed by `(adset name, ad name)` — which is `(stratum id, creative name)`, because `create_adset` names an adset after the stratum and `create_ad` names an ad after its creative. Values are the `{study_id, stratum_id, creative_name, shortcode, metadata, resolved_from}` dicts destined for the table. |
| 2 | `reconciliation.adset_dif` → `ad_dif` | Stamps the matching entry onto each `"ad"`/`"create"` `Instruction` via its new optional `provenance` field. Updates and deletes get nothing — only a create learns a new id. |
| 3 | `facebook.update.GraphUpdater.execute` | Returns `(report, created_id)`. The SDK's return value used to be discarded; this is the only moment vlab ever learns the ad id without going back to the Graph API. |
| 4 | `malaria.run_instructions` → `record_ad_attribution` | Writes the row via `campaign_queries.create_ad_attribution`. |

The split at step 2/4 is the point. The `_dif` functions are the testable
functional core and stay pure — they can be exercised without a database, which
is what keeps `test_reconciliation.py` a fast unit-test file. The write lives in
the imperative shell, where the run already has a `db_conf`.

A create that carries no provenance, or whose provenance key is missing, still
succeeds — but logs a warning, because an unmapped ad is a real defect (see
below) and refusing to create the ad would be worse than creating one that is
merely unattributable.

## The read path (inference, Go)

| # | Where | What happens |
|---|---|---|
| 1 | fly's responses view | Exposes `ad_id` as a first-class column, resolved at `conversation_started`. fly deletes any `ad_id` arriving via ref metadata before stamping its own, so a study author cannot inject one — the field is trustworthy input. |
| 2 | `sources/fly/main.go` | Copies it to `InferenceDataEvent.AdID` and derives `AdNetwork` from fly's `platform` metadata key via `adNetworkForPlatform`. |
| 3 | `swoosh/swoosh.go` | `GetAdAttributions` loads the study's mapping — once per run, before `Reduce`. |
| 4 | `swoosh/inference_data.go` | `retrieveFromAd` closes over that mapping and resolves `location: "ad"` confs; `adAttributionOutcome` classifies each event three ways. |

`AdID` and `AdNetwork` are **typed fields on `InferenceDataEvent`, not reserved
keys inside `User.Metadata`**. A map key would be a fly-shaped convention every
future connector has to imitate with nothing enforcing it — the same shape of
mistake as the dotted ref, which was a convention smuggled inside an untyped
blob. The field is the contract; each source works out how to meet it.

**This needed no migration.** `inference_data_events` stores the whole event as
one JSON blob in its `data` column, and the new fields are `omitempty`, so every
existing row stays byte-identical.

### `location: "ad"`, and why there is no fallback

A third value alongside `"variable"` and `"metadata"`, with the same
`ExtractionConf` shape — the user declares `key`, `name`, `value_type` and
`aggregate` exactly as for any other location. vlab derives nothing.

**It is for new studies only, and a fallback to `location: "metadata"` would be
a bug.** swoosh recomputes a study's entire history on every run: `GetEvents`
loads every event and `InsertInferenceData` upserts. So swapping an existing
study's conf from `"metadata"` to `"ad"` would not migrate it forward — it would
retroactively re-attribute its whole back-catalogue through a path those events
cannot satisfy. Rows written before fly began stamping `ad_id` carry none and
are never backfilled, so every historical respondent would extract nothing,
match no stratum, and vanish from the counts. Strata would read as massively
under-recruited and the optimizer would flood budget toward them. Worse, an
event with no `ad_id` is indistinguishable from an organic arrival, so it lands
in the do-not-alarm bucket.

A one-off backfill is the answer if someone ever genuinely must retrofit a
study — not a standing code path whose justification will be forgotten.

Note that ref content and inference source are orthogonal: a new study can emit
full refs *and* declare `location: "ad"`. The ref is what fly survey logic can
branch on; the mapping is what the optimizer reads.

### Where the database touch lives

`RetrieveFunc` is `func(*InferenceDataEvent, *ExtractionConf) (json.RawMessage,
bool)` — no context, no error, called once per event per conf. A query inside it
would be one query per response. So the mapping is loaded once per study in
`swooshStudy` and passed into `Reduce` as plain data; `Reduce` has no pool in
its signature, which makes a per-event query unrepresentable rather than merely
avoided, and keeps `Reduce` unit-testable against a fake map.

The load is **per study**, not global. A cross-study ad id then misses the
lookup instead of silently importing another study's strata — and that miss is
correct behaviour that lands in the counters below.

## The three-way split

A retrieve returning `ok=false` means `continue`: no variable, no stratum match,
optimizer undercount. Three different things produce it and only one is a bug.

| Outcome | Meaning | Treatment |
|---|---|---|
| attributed | ad id present, mapping row found | normal; no event |
| organic | no ad id on the event | expected; counted as `extraction_warning`, does not alarm |
| **unmapped** | ad id present, **no mapping row** | always a bug; counted as `extraction_error` at severity `error` |

Classification happens once per **event**, not per conf. An event either carries
an ad id or it does not, and that id either resolves or it does not — none of
which depends on the conf. Counting per conf would multiply one organic arrival
by however many ad-location confs the study declares.

Organic is worth counting even though it is expected: shortcodes are shareable
by design, so a jump in the organic share means a leaked shortcode. Unmapped is
always a defect — vlab created an ad and failed to record what it meant.

**Unmapped is self-healing.** Because swoosh recomputes the whole study every
run, inserting a missing mapping row retroactively fixes every prior run's
attribution. The counter is a current-state measure, not a cumulative one, and
the dashboard's 90-minute recency window ages the stale error out without anyone
closing it.

A key that is missing from a row that *was* found is deliberately not counted as
unmapped: the ad is mapped, the conf just asked for something the ad was not
frozen with. That is a conf problem, and inflating the unmapped counter with it
would blunt the signal that exists to catch real bugs.

## Declaring an ad-derived variable

vlab does not infer these confs, so the dashboard form is the only way a
researcher states one. In the study's **Inference Data** step, a fly source's
location dropdown offers a third option alongside Metadata and Variable:

> **Ad (which ad recruited them)**

The `key` is then a stratum metadata key — `creative`, `gender`, `Age`, `form` —
one of the keys that study's ads were actually built with. There is no response
to select, because the value is looked up by key rather than found by walking a
path into the respondent's answer.

Moving an existing variable from Metadata to Ad is a one-word change at the same
`key`, precisely because the frozen blob is key-for-key the ref's dict. But it
is only safe on a **new** study — see the no-fallback reasoning above.

**The option is offered on fly sources only.** The Qualtrics and Typeform
connectors do not populate an event's ad id, so offering it there would let
someone configure a variable that silently yields nothing forever. The two
location lists are separate modules for that reason, and a test asserts the
Qualtrics list contains no `ad` — the guard is there to survive a future
refactor that merges the forms.

Nothing between the form and swoosh constrains the value: `location` is a bare
string in the dashboard's TypeScript, in the Go API's opaque conf storage and in
Python's `ExtractionConf`. The only two places that enumerate the allowed
locations are the form's dropdown and swoosh's `getRetrieveFunc`.

## The mapping CSV export

`GET /{org_id}/studies/{slug}/ad-attributions.csv`, on the same org/study
routing and auth as every other study endpoint.

```
ad_id, network, creative, gender, Age, Region, form, created
```

The frozen blob is flattened into columns under its own key names, which makes
the whole export one sentence: **left-join your survey export on `ad_id` and
your old metadata columns come back, named as they always were.** True only
because of invariant 1 below — a blob built from `stratum.metadata` would be
missing `creative` and `form`, and the join would quietly return fewer columns
than the researcher had before.

Two details worth knowing:

- Columns are the **union** across rows, in first-seen order, not the first
  row's keys. A conf edited mid-flight leaves rows frozen under two shapes and
  append-only means both survive.
- **Deleted ads are included.** Respondents keep arriving from ads
  reconciliation has removed, so a CSV of only live ads would silently lack rows
  the researcher needs — and those respondents would look unattributed rather
  than unexported. Nothing in the read path filters on liveness; there is no
  liveness column to filter on, by design.

There is no dashboard download button yet. The endpoint takes an API key, which
suits the primary use — fetching it from an analysis script that is doing the
join anyway.

## Retiring the ref: shortcode-only Messenger ads

This is the lever the rest of the design exists to make safe. Until a study
pulls it, `location: "ad"` works but its ads still ship vlab's entire stratum
vocabulary into fly on every message — the ad id *duplicates* the ref rather
than replacing it, and nothing is actually decoupled.

`FlyMessengerDestination.include_metadata_in_ref` controls it, named to match
the WhatsApp destination's field because it is one concept; the two channels
differ only in default. Messenger defaults **True** — the historical behaviour,
which every existing study depends on. Turned off, the ad emits
`form.<initial_shortcode>` on **both** Messenger carriers: `url_tags`, which
Meta surfaces as `referral.ref`, and the quick-reply payload inside
`page_welcome_message`. Both, because a respondent can arrive by either, and two
different refs would mean one ad describing two different people depending on
how they tapped it.

`form.<shortcode>` is the minimum that still routes. fly's `getMetadata` parses
`referral.ref` as dot-pairs and reads `md.form`, falling back to
`FALLBACK_FORM` — a real survey — when it is absent. Routing is the one job the
ref cannot delegate, because it happens at the first inbound message while
attribution is a batch join done afterwards.

### The trap: what the ref carries is not what gets frozen

`creative_metadata` returns the **complete** dict regardless of ref mode, and
`messenger_ref` is the only place the mode is allowed to matter. This separation
is load-bearing.

For a shortcode-only study the frozen `ad_attributions` blob is the *only*
attribution it will ever have. If the mode leaked into `creative_metadata`, such
a study would freeze rows containing nothing but `form`; every `location: "ad"`
conf would resolve to nothing, every stratum would count zero, and the optimizer
would reallocate on empty data. Silent, total, and unrecoverable after the fact,
because the blob is frozen at creation and never refreshed.

Two tests pin it: a shortcode-only and a full-ref destination over identical
strata produce identical frozen blobs (still containing `creative`, `form` and
every stratum key), and `ad_provenance` — the thing that actually reaches the
database — is identical under both modes.

### Flipping a live study

Changing the mode changes the *creative*, and `update_ad` compares creatives via
`field_contract.COMPARED_AD`, so a flip rewrites that study's ads on its next
reconciliation run. That is intended: it is a deliberate per-study act, and each
study reconciles from its own conf, so it cannot cascade to any other.

The flip is an in-place ad **update against the same ad id**, not a delete and
recreate — reconciliation matches ads by name, and the name (the creative name)
does not change. That matters more than it looks: the ad id is the attribution
key, so a flip that minted new ids would strand every `ad_attributions` row the
study already had and leave its past respondents unattributable. Both properties
are asserted.

### The half-migration guard

Thinning the ref only works if the study *also* reads the mapping. Do one
without the other and the study has no attribution at all: the ref no longer
carries the stratum, and nothing looks the ad up. Every stratum counts zero and
the optimizer reallocates on empty data — the same silent shape as an unmapped
ad, arrived at from the opposite direction.

`study_conf.thins_its_ref_without_reading_the_mapping` detects it and
`malaria.warn_on_thinned_ref_without_mapping` logs it: a fly destination with
`include_metadata_in_ref` off while no extraction conf declares
`location: "ad"`. It **warns rather than raises**, because it is not certainly
wrong — a study recruiting uniformly, with no `question_targeting`, needs no
stratum attribution and is entitled to a thin ref. Same reasoning as the
completeness check below.

It covers WhatsApp destinations too, since their default is already thin: a
CTWA study that never declares `location: "ad"` confs has no attribution at all,
and should hear about it.

### Web and App stay on full refs

Deliberately. Neither type has an `initial_shortcode`, because their
`url_template` / `deeplink_template` already points at a specific survey —
routing is not a job the ref does for them. Making them shortcode-only would
mean inventing a conf field for a token neither needs. The equivalent decoupling
for a web platform is capturing the ad id from the ad URL, which is separate
work. Messenger is where every existing study lives and where the ref actually
costs something.

## Click-to-WhatsApp destinations

`FlyWhatsAppDestination` is shaped after `FlyMessengerDestination`, minus
`button_text` (WhatsApp has no quick-reply button — the respondent gets a
prefilled compose box) and plus `include_metadata_in_ref`.

Both fly destinations fold `form` into `creative_metadata` identically, so the
frozen `ad_attributions` blob has the same shape on either channel and a study
on `location: "ad"` reads the same keys regardless of how respondents arrived.

### Why the WhatsApp ref is a different string

A CTWA referral carries **no advertiser-settable `ref`** — `url_tags` was
measured not to reach WhatsApp at all. fly instead recovers the shortcode from
the ad's autofill text, which prefills the respondent's first message, and
matches it against an anchored full-match pattern (`WHATSAPP_ENTRY_REF` in
`replybot/lib/event-normalizer.js`):

```
/^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$/i
```

Two things follow, both verified directly against that regex:

1. **`make_ref`'s output can never match.** The pattern anchors on `form.`;
   `make_ref` leads with `creative.`. No value is safe enough to fix that, so
   WhatsApp needs its own **form-first** serialisation —
   `marketing.whatsapp_autofill`, emitting `form.<shortcode>[.key.value…]`.
2. **Every token is `[A-Za-z0-9_-]`.** No spaces, no `%`. Percent-encoding
   rescues nothing, because `%` is not in the class either.

**A failure here is silent, which is what makes it dangerous.** Meta delivers
the text intact — dots *and* spaces both survive `autofill_message.content`,
measured against live ads — so nothing rejects it upstream. fly's pattern
rejects it, no `conversation_started` is derived, and the arrival falls through
to `FALLBACK_FORM`: a real survey, so those respondents look like completions
rather than errors. That is the VIR-19 shape, which took four days to spot.

### Full-ref mode is real but rare

Measured against the production stratum values recorded in
`planning/ad-id-attribution.md`, roughly half are undeliverable:

| Value | Deliverable |
|---|---|
| `3B`, `gelangchoice`, `women`, `Smiling`, `location` | yes |
| `Static English - Girls`, `Bauchi State`, `Like Parents`, `South East` | **no** |

A single unsafe value poisons the whole ref. So `include_metadata_in_ref` is
**off by default**, and it will stay unusable for most existing-style strata
unless their values are renamed. The only reason to turn it on is fly survey
logic that branches on ad metadata — the optimizer never needs it, because the
ad-ID join carries stratum identity regardless.

The autofill text is also **visible to and editable by the respondent**, which
is a second, independent reason to prefer the short form.

### Validation is at config time, always

Two checks, because the ref's content and its deliverability live in different
confs:

- **The shortcode**, on `FlyWhatsAppDestination` itself. Applies in both modes,
  since even the default token is `form.<shortcode>`.
- **The metadata**, in `StudyConf.check_whatsapp_refs_are_deliverable`, which
  fires only for a destination with `include_metadata_in_ref` on. Destinations
  and strata are separate confs POSTed independently, so no per-conf validator
  can see both; `StudyConf` is where they first meet, and it is assembled at the
  start of every reconciliation run — still before any ad exists.

It fails closed. A study with an undeliverable ref creates **no ads at all**,
rather than ads that recruit people into the fallback survey.

Ref content and inference source stay orthogonal: a study can emit full refs for
fly survey logic *and* declare `location: "ad"` for the optimizer.

### The ad set half

Meta will not accept a `WHATSAPP` `destination_type` ad set without a
`promoted_object` naming the Page and, optionally, the number.

`whatsapp_phone_number` is **required** on the destination, even though Meta
treats it as optional. Omitting it falls back to the Page's "primary" number,
and many-numbers-to-one-Page is documented and supported — so an org running
several would silently recruit into whichever one that happens to be. Naming it
is the only way to know. It is normalised to digits (Meta types it as a numeric
string; credentials store the display form `+1-541-920-2635`) and validated at
config time against E.164's 7–15 digit bounds, which also catches the classic
mistake of pasting a `phone_number_id` instead of a number.

The Page id comes off the creative template's `object_story_spec.page_id` — the
same field `_create_creative` reads, so an ad set and its creative can never
name different Pages.

`destination_type` is **checked, not overridden**. A WhatsApp destination on a
`MESSENGER` ad set produces a valid creative, a valid promoted object, and an ad
that never reaches WhatsApp. Deriving it here would change what every existing
study sends, so `StudyConf` raises when the two disagree instead.

### Why this could not rewrite your live ad sets

`promoted_object` becoming non-`None` for a whole destination type is exactly
the kind of change that can make every existing ad set look drifted. It cannot
here: `promoted_object` is **not in `field_contract.COMPARED_ADSET`**, so
`update_adset` neither compares it nor includes it in update params. It rides
only on ad set *creates*, which is where Meta needs it. Asserted directly — a
live ad set without one is not rewritten once we start sending one, and an
unchanged study still produces zero instructions.

### A latent bug fixed rather than inherited

`promoted_object` is an ad set field while destinations are named per creative,
so every creative in a stratum has to want the same one. That used to be
assumed: the app branch read `destinations[0]` under a standing `# TODO: assert
all destinations are the same`, so a stratum mixing an app creative with any
other kind published half its ads under the wrong promoted object, silently.
`planning/click-to-whatsapp-ads.md` flags it and says to fix it rather than
copy it.

`marketing.adset_promoted_object` now checks agreement and raises only on
genuine ambiguity. Strata whose creatives all need none — every Messenger and
Web study there is — still produce `None`, mixed or not, because there is
nothing to disagree about. `facebook/probe.py` held a second copy of the same
branch and now calls the shared function, so the probe cannot report an ad set
different from the one production actually sends.

**Not yet built:** the dashboard form for this destination type, including its
phone-number field.

## Completeness check

A stratum's `question_targeting` predicate matches on variables swoosh writes,
and swoosh writes exactly what the study's `inference_data` confs name. A
predicate naming anything else can never match: the stratum counts zero and the
optimizer moves its budget elsewhere. Same silent-miscount family, catchable one
layer earlier and from configuration alone.

`study_conf.missing_targeting_variables` detects it, and
`malaria.warn_on_incomplete_targeting` logs it. It **warns rather than raises**,
for two reasons: a study with no `inference_data` conf at all supplies nothing,
so every targeted variable looks missing when the study is merely unfinished;
and the predicate has never been run against the thousands of existing
production studies, so its false-positive rate is unmeasured. Turning an
unmeasured predicate into a hard failure would stop ad reconciliation for any
study it misjudges. Measure first, enforce later — the same reasoning as
`facebook/reconciliation.py:_declared_drop`.

## Three invariants

### 1. `metadata` is what `make_ref` serialises, not `stratum.metadata`

The frozen blob is `{"creative": <creative name>, **md}`, where `md` is what
`marketing.creative_metadata` builds:

```
stratum.metadata
  + study.general.extra_metadata
  + form: destination.initial_shortcode   (fly destinations only)
  + destination.additional_metadata       (if any)
```

`make_ref` prepends `creative.<creative name>`, and `form` is added at
publish time rather than declared in the stratum conf. So the ref carries
strictly more keys than `stratum.metadata` has.

Freezing `stratum.metadata` instead is the easy mistake, and it fails quietly:
the keys `creative` and `form` simply go missing. A downstream extraction conf
asking for either finds nothing, the stratum matches nobody, its count reads
zero, and the optimizer reallocates budget away from a stratum that is in fact
recruiting perfectly well. Nothing raises. Silent miscounting is the failure
mode this whole design exists to prevent, so this is the invariant to be most
careful with.

`creative_metadata` was extracted out of `create_creative` precisely so the ref
and the frozen blob are computed from one expression and cannot drift.
`test_marketing.py` also asserts the equality directly, by parsing `make_ref`'s
output back with a reimplementation of fly's own dot-pair parser
(`getMetadata`, `replybot/lib/typewheels/utils.js`) and comparing.

One known limit, asserted rather than fixed: `make_ref` does not escape `.`, so
a metadata *value* containing a dot produces a ref that parses back to garbage.
The frozen blob has no such grammar and keeps the value intact — for those
studies the ad-id path is strictly more accurate than what it replaces.

### 2. Append-only, and never rebuilt from live Facebook state

Reconciliation deletes ads that fall out of the desired set, but respondents
keep arriving from deleted ads: CTWA referrals carry
`ads_context_data.post_id`, and page posts persist and can be reshared
indefinitely. **A row must outlive its ad**, which is also why the table cannot
be reconstructed from the Graph API on demand.

Consequences visible in the schema: no TTL (unlike `study_run_events`), and **no
foreign key to `studies`** — a cascading delete is still a delete path, and this
table has none.

### 3. `metadata` is frozen at creation, permanently

Study confs mutate. A stratum's metadata today is not what it was when the ad
was created, so even a *live* ad cannot be resolved correctly by reading the
current conf. The row is a snapshot, not a pointer.

`create_ad_attribution` writes with `ON CONFLICT (network, ad_id) DO NOTHING`,
which makes this mechanical: a re-run can neither duplicate a row nor overwrite
a snapshot with today's metadata. It returns `None` when the row already
existed. **Do not add a code path that refreshes `metadata`.**

## `network` is the ad network, not the messaging channel

Messenger and WhatsApp ads are both Meta ads living in one id namespace, so both
are `facebook`. The discriminator exists because Meta ad ids are only unique
within Meta and TikTok/Google Ads are already contemplated — it is much cheaper
to add before a second network exists than after. Easy to get backwards.

`resolved_from` records which id source produced the row: `'ad_id'` for rows
written at ad creation (all of them today), leaving room for a row resolved from
a WhatsApp referral's `source_id` to be distinguishable later without
archaeology.

## Failure mode to watch

An ad created with no mapping row can never be attributed, and **there is no
backfill path** — the design rejected retrofitting existing studies. For that
reason `record_ad_attribution` raises on a failed write rather than continuing:
stopping the run leaves the remaining ads uncreated, which the next run fixes,
whereas carrying on would mint permanent silent gaps. `run_updates` already
catches per-study, so one study's failure does not stop the others.

This is also why **A1 and A2 must be in production before the first ad of any
study that opts into ad-id attribution.**

## Where things live

| Thing | Path |
|---|---|
| Migration | `devops/migrations/20260816000000_add_ad_attributions.{up,down}.sql` |
| Schema bootstrap (second copy — keep in sync) | `devops/helm/migrations/init.sql` |
| Provenance construction | `adopt/adopt/marketing.py` |
| Instruction plumbing | `adopt/adopt/facebook/{update,reconciliation}.py` |
| Write path | `adopt/adopt/{malaria,campaign_queries}.py` |
| Completeness check | `adopt/adopt/study_conf.py`, `adopt/adopt/malaria.py` |
| CSV export | `adopt/adopt/server/csv_export.py`, `adopt/adopt/server/server.py` |
| WhatsApp destination + ref validation | `adopt/adopt/study_conf.py`, `adopt/adopt/marketing.py` |
| Ref mode (`include_metadata_in_ref`) | `adopt/adopt/study_conf.py`, `marketing.messenger_ref` |
| Dashboard form | `dashboard/src/pages/StudyConfPage/forms/inferenceData/{flyExtraction,qualtricsExtraction}.ts` |
| Event fields + network constant | `inference/inference-data/inference_data.go` |
| Connector | `inference/sources/fly/main.go` |
| Mapping load | `inference/swoosh/ad_attributions.go` |
| Extraction + three-way split | `inference/swoosh/inference_data.go` |
| Event routing / severity | `inference/swoosh/events.go` |
| Python tests (need `make test-db`) | `adopt/adopt/test_ad_attributions.py`, `adopt/adopt/test_marketing.py`, `adopt/adopt/facebook/test_reconciliation.py`, `adopt/adopt/test_study_conf.py`, `adopt/adopt/server/test_ad_attributions_csv.py` |
| Go tests (need `make test-db`) | `inference/swoosh/ad_attributions_test.go`, `inference/sources/fly/main_test.go` |
| Frontend tests | `dashboard/src/pages/StudyConfPage/forms/inferenceData/flyExtraction.test.ts` |

Per-app detail: `adopt/README.md`, `inference/README.md` and
`dashboard/README.md`.

Full design, including the phases still outstanding (A4's per-study lever that
finally retires the ref, and A8's `FlyWhatsAppDestination`):
`planning/ad-id-attribution.md`.
