# Ad-ID Attribution: vlab owns the ad → stratum join

**Date:** 2026-08-16
**Status:** Design revised 2026-08-16 — approved, implementation starting
**Scope:** Offer an opaque ad identifier as an alternative to ref-smuggling, for **new
studies**. Applies to fly and, by the same contract, to any web survey platform
(Typeform, Qualtrics, SurveyMonkey).

**Companion docs:**
- `planning/click-to-whatsapp-ads.md` — Meta API reference and the CTWA-specific findings
- `planning/whatsapp-metadata-opt-in.md` — the escape hatch for studies that need ad
  metadata inside survey logic
- `adopt/scripts/ctwa_probe.py` — the probe that produced the evidence below

---

## The problem

Today vlab encodes ad identity into a dotted string and smuggles it through the
messaging platform:

```
make_ref()  ->  "creative.Static English - Girls.Age.Age.State.Bauchi State.form.mnchweeklanguage"
```

It reaches fly two ways — `AdCreative.url_tags` (`marketing.py:463`), which Meta
surfaces as `referral.ref`, and a quick-reply payload inside `page_welcome_message`
(`marketing.py:136-148`). fly parses the dot-grammar generically and the result lands
in its own schema. Production response metadata looks like this:

```json
{"creative": "3B", "form": "gelangchoice", "gender": "women", "location": "location", ...}
{"Age": "Like Parents", "Region": "South East", "creative": "Smiling", ...}
```

`creative`, `gender`, `Age`, `Region` are vlab's stratum keys, living as first-class
fields across 17.5M rows in fly's `responses` table. Any change to vlab's metadata
scheme is a change fly's data must tolerate. That is the coupling this document
removes — **for new studies**. Existing studies keep the coupling, and keep working.

The coupling is in the **data**, not in fly's code: `getMetadata`
(`replybot/lib/typewheels/utils.js:75-105`) does generic dot-pair parsing —
`_group(pairs.map(decodeURIComponent))` — with no vlab-specific key handling anywhere.
vlab's vocabulary is in fly's tables purely because vlab sends it.

It also does not port cleanly. WhatsApp has no advertiser-settable `ref` on the referral
object, and the carrier that does exist there is visible to the respondent and editable
by them (finding 8).

## What we verified, empirically

All of the following was measured, not inferred — against production data, against live
Meta ads created by `adopt/scripts/ctwa_probe.py` on 2026-08-16, and against the code as
it stands.

**1. `url_tags` does not reach WhatsApp.** A real CTWA ad carrying
`url_tags=ref=ctwaprobe.alpha...` produced a referral whose complete key set was:

```
body, ctwa_clid, headline, image_url, media_type,
source_id, source_type, source_url, welcome_message
```

No `ref`. The mechanism that works on Messenger has no WhatsApp equivalent.

**2. `source_id` is exactly the ad ID.** The same referral carried
`source_id = 120254866237980150`, the precise ad the probe had created.

**3. On Messenger, `ad_id` is a strict superset of `ref`.** Across the full `messages`
history (2020–2026), there is **not one row** where `referral.ref` is present without
`referral.ad_id`. The converse occurs — 288 rows in 2025, 151 in 2024 arrived with
`ad_id` and no `ref`. Switching to the ad ID loses nothing and recovers several hundred
conversations that are currently unbindable.

**4. Meta only began sending `ad_id` in 2024.** Zero in 2020–2023; 65,599 in 2024;
118,135 in 2025. The constraint that produced ref-smuggling was real when the code was
written and has since expired.

**5. The ad ID is stable across updates.** Reconciliation matches ads by **name**
(`facebook/reconciliation.py:278`) and issues in-place updates against the existing id
(`:236`), including for full creative changes. A new id appears only when the name is
new — a new creative or a new stratum — which is exactly when the ref would change too.

**6. Ad metadata is almost never used in survey logic.** Of 5,141 production surveys,
logic branches on `seed*` in 1,599 and on `e_*` payment/event outcomes in 1,491, but on
ad-derived stratum keys in roughly 30–60 (`gender` 21, geo 29, `creative` 9, `age` 0).
Under 1%.

**7. swoosh recomputes every study from scratch, on every run.** `GetEvents` loads
*every* event for the study (`inference/swoosh/swoosh.go:61-72`), `Reduce` folds the
whole history, and `InsertInferenceData` upserts `ON CONFLICT ... DO UPDATE`
(`inference/swoosh/persist.go:15-16`). There is no incremental era and no watermark. A
conf change therefore applies **retroactively to all of a study's history** on the very
next run. This finding is load-bearing — it is why the design is new-studies-only, and
the reasoning is in *New studies only, and no fallback* below.

**8. fly already carries the legacy dotted string on click-to-WhatsApp.** Since
`replybot-v0.0.217`, `categorizeWhatsAppEvent`
(`fly/replybot/lib/event-normalizer.js:295-309`) derives a `ref` from the ad's
autofill-message text when `referral.ref` is absent, carrying trailing `.key.value`
pairs through `_group` exactly as on Messenger. So "WhatsApp has no advertiser-settable
`ref`" is true of the referral *object* and false of the entry path as a whole. Studies
that want ad metadata inside fly survey logic can have it on WhatsApp today — the cost
is that the prefill is respondent-visible and respondent-editable.

**9. vlab has no WhatsApp destination type at all.** `create_creative` branches only on
`FlyMessengerDestination` / `AppDestination` / `WebDestination`
(`adopt/adopt/marketing.py:440-487`), and nothing anywhere sets `autofill_message`. The
CTWA arm is greenfield in vlab: fly built the receiving end, vlab never built the
sending end. A new `FlyWhatsAppDestination` is new scope this plan names (A8).

---

## The design

**The ref was never per-user data.** vlab creates exactly one ad per (creative,
stratum) pair, so the ad ID already determines the shortcode, the creative, and the
stratum metadata. We have been shipping a redundant copy of the ad's identity inside
every message.

So: **the survey platform returns an opaque ad identifier; vlab owns the mapping and
does the join.**

```
vlab creates ad        -> Meta returns ad_id
                       -> vlab writes (network, ad_id) -> {shortcode, creative, stratum metadata}

respondent arrives     -> platform captures the identifier
                          Messenger: referral.ad_id
                          WhatsApp:  referral.source_id  (when source_type == 'ad')
                          Web:       hidden field from the ad URL
                       -> stored alongside responses, opaque

analysis / inference   -> vlab joins on (network, ad_id) -> strata, counts
```

### New studies only, and no fallback

**`location: "ad"` is a per-study choice made at study creation. Existing studies keep
`location: "metadata"` and full refs, permanently, and are never touched.**

This is the rule the rest of the design hangs off, and finding 7 is why. Because swoosh
recomputes a study's entire history on every run, swapping an existing study's conf
entry from `metadata` to `ad` would not migrate it forward — it would retroactively
re-attribute its whole back-catalogue through a path those events cannot satisfy. Fly
`responses` rows written before B1 carry no `ad_id` and are never backfilled, so their
`inference_data_events` carry none either. Every one of those historical respondents
would extract nothing, match no stratum, and vanish from the counts. Strata would read
as massively under-recruited and the optimizer would flood budget toward them.

It is also worse than an unmapped ad, because an event with no `ad_id` is
indistinguishable from an organic arrival — it lands in the expected, do-not-alarm
bucket rather than the alertable one.

A new study has no such history. Every ad it creates has a mapping row, every event it
produces has an `ad_id`, and full recompute is a non-issue precisely because the entire
history was written under the new scheme.

**Rejected: a code-level fallback.** We considered having the `ad` retrieve function try
`e.User.Metadata[conf.Key]` first and fall back to the ad mapping, so one conf entry
could span both eras. It works, and it is monotone — but it exists only to serve a
migration that does not need to happen. Two locations with the user picking one per
study is dumber, has no hidden precedence rule, and carries no permanent code path whose
justification will be forgotten. If someone later genuinely must retrofit an existing
study, that is a one-off backfill job, not a standing feature.

**Ref content and inference source are orthogonal knobs.** A new study can emit full
refs *and* declare `location: "ad"`. Nothing couples them: the ref is what fly survey
logic can branch on, the mapping is what the optimizer reads. Choosing the ad-ID join
for inference does not cost you metadata in the survey, and vice versa.

### Routing stays separate, and stays with the shortcode

The ref does two jobs and only one of them can be deferred.

- **Attribution** — which creative/stratum. Deferred, batch, joined in vlab.
- **Routing** — which survey to start. Cannot be deferred: fly must decide at the first
  inbound message.

Web platforms get routing for free, because the ad URL already points at a specific
survey. Messaging does not — one number or page hosts many studies. So a **minimal
routing token stays in the message: the shortcode alone**, for studies that choose the
thin ref.

This is not a compromise; it is what shortcodes were always for. They are designed to
be human-readable and shareable — someone hears about a study and texts the shortcode.
That is also what makes a shortcode acceptable as a visible WhatsApp prefill
(`form.mnchweeklanguage` reads fine in a compose box; the full dotted ref does not).

Note the decoupling this buys: a shortcode is **fly's own concept**. Under this split
fly parses only an identifier for a thing fly owns, and vlab's stratum vocabulary never
enters fly at all.

### The contract

One opaque string, returned unchanged. No grammar, no shared vocabulary, no parsing.

| Platform | Captured from | Returned as |
|---|---|---|
| fly / Messenger | `referral.ad_id` | first-class field on the response record |
| fly / WhatsApp | `referral.source_id`, when `source_type == 'ad'` | same field |
| Typeform / Qualtrics / etc. | hidden field populated from the ad URL | hidden field in the export |

**Key on `(network, ad_id)`, not on a bare id.** Meta's ad IDs live in Meta's
namespace, and `planning/ad-conversion-feedback/` already contemplates TikTok and
Google Ads. Add the discriminator before the second network exists, not after.

`network` is the **ad network**, not the messaging channel. Messenger and WhatsApp ads
are both Meta ads in one id namespace, so both are `facebook`. Easy to get backwards,
expensive to fix once rows exist.

### fly: storage vs. view

Four sinks off one Kafka stream (`scribble/README.md:42-56`):

| Table | Tier | Semantics |
|---|---|---|
| `messages` | **storage** | Raw event content, `ON CONFLICT(hsh, userid) DO NOTHING`. Append-only, authoritative, never reinterpreted. |
| `states` | **projection** | One row per `(userid, pageid)`, `state_json` overwritten in place. A fold over the log; also the mechanism that carries a conversation-start fact forward to a response written later. |
| `responses`, `chat_log` | **derived output** | Append-only extracted records, each with a frozen snapshot of `md`. |
| `/api/v1/responses`, exports | **view** | Computed at read. Already a curated projection — hand-picked columns, `seed` omitted, computed pagination `token` (`dashboard-server/queries/responses/response.queries.js:106-130`). |

The complete raw referral is **already** in `messages`. Nothing needs building for
durability, and `md` therefore carries only what must travel forward.

**Normalize early, in `getMetadata`.** Rows stay cheap — one added key, not the seven
a raw CTWA referral would cost on every response. The rule stays recoverable if it
changes, because `getMetadata` is pure over the `conversation_started` event and that
event is in the log.

### Layering: who knows what

| Layer | Owns | Responsibility here |
|---|---|---|
| fly | messenger vs. whatsapp | Stores the referral raw; resolves **one** normalized ad identifier; exposes it in the view. |
| vlab source connectors | survey-platform specificity | fly connector copies fly's normalized field; Typeform's reads a hidden field; each maps its own source to the common contract. |
| swoosh | nothing platform-specific | Joins the mapping, emits variables, counts outcomes. Never learns WhatsApp exists. |

The ad identifier is a **first-class field on `InferenceDataEvent`**, not a reserved key
inside `User.Metadata`. A map key would be a fly-shaped convention every other connector
has to imitate, enforced by nothing — the same shape of mistake as the dotted ref, which
was a convention smuggled inside an untyped blob. The field is the contract; each source
figures out how to meet it.

---

## Failure modes to design for

**Silent miscounting.** Today a broken ref means the survey does not start — loud,
immediate, noticed. Under ad-ID join, a missing mapping entry means a respondent is
attributed to *no stratum*: it does not fail, it miscounts, and the optimizer is fed bad
numbers and misallocates budget. Quieter and worse. This is the strongest argument for
the new-studies-only rule, for the append-only invariant in A2, and for the counters in
A7.

**Organic entrants.** Shortcodes are shareable by design, and a Page linked to a
WhatsApp number gets a public WhatsApp button — so respondents can arrive with no ad and
no identifier. They must be **kept out of stratum counts** or recruitment looks complete
when it is not. This works by accident today (a bare-shortcode entrant has no `creative`
key, so matches no stratum predicate); make it explicit.

Three outcomes are wanted, not two — reject, accept-unattributed, or
accept-attributed-to-a-default. Rejecting throws away real data; for many research
questions an organic respondent is still a respondent, just not a sampled one. The
setting belongs in fly's `survey_settings` (fly enforces it at conversation start, so no
runtime call to vlab).

**Spend leak.** Recruitment confs carry `incentive_per_respondent` and dinersclub pays
real money, so uncontrolled entry has a direct cost and rewards sharing. Default to
requiring an identifier whenever a study has a non-zero incentive.

**Observability.** A per-study count of unattributed entrants must be visible and
alertable. A rise means either a leaked shortcode or a broken mapping — and those look
identical in the data unless someone is watching.

---

## Stream A — vlab

### A1. Capture the ad id at creation

The created id is discarded twice: `GraphUpdater.execute` drops the SDK return
(`adopt/adopt/facebook/update.py:93-96`), and `run_instructions` only *logs* the report
(`adopt/adopt/malaria.py:59-67`). Nothing is persisted, so this is new plumbing.

The create instruction also carries no stratum identity. `ad_dif`'s creator passes
`{**ad.export_all_data(), "adset_id": adset["id"]}`; ad name = creative name
(`marketing.py:153`); the stratum is only reachable via adset name = `stratum.id`
(`marketing.py:101-102`).

1. Add an optional `provenance` field to `Instruction` (NamedTuple in `update.py:9-13`,
   defaulted to `None` so no existing construction site breaks).
2. Populate it in `ad_dif`'s creator (`facebook/reconciliation.py`) with
   `{study_id, stratum_id, creative_name, shortcode, metadata, resolved_from}`.
3. `execute` returns the created object's id alongside the report; `run_instructions`
   writes a mapping row on successful ad creates.

Instruction *generation* stays pure and testable; the write lands in the imperative
shell.

### A2. The mapping table

New migration, following `devops/migrations/YYYYMMDDHHMMSS_<name>.{up,down}.sql`:

```sql
CREATE TABLE ad_attributions (
  network        TEXT NOT NULL DEFAULT 'facebook',
  ad_id          TEXT NOT NULL,
  study_id       UUID NOT NULL,
  stratum_id     TEXT NOT NULL,
  creative_name  TEXT NOT NULL,
  shortcode      TEXT,
  metadata       JSONB NOT NULL,
  resolved_from  TEXT,           -- write path; 'ad_id' = captured at ad creation
  created        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (network, ad_id)
);
```

Write pattern follows `create_adopt_report` (`adopt/adopt/campaign_queries.py:131-140`).

**Three invariants, all load-bearing:**

- **Append-only. Never delete, never derive from live Facebook state.** Reconciliation
  *deletes* ads that fall out of the desired set (`reconciliation.py:290-296`), and
  respondents still arrive from deleted ads — the referrals we examined carry
  `ads_context_data.post_id`, and page posts persist and can be reshared. Today's
  mechanism has no such problem because the ref travels in the message.

- **`metadata` is frozen at creation.** Study confs mutate, so a stratum's metadata
  today is not what it was when the ad was created. Even a *live* ad cannot be resolved
  correctly after a conf edit. The row is a snapshot, not a pointer.

- **`metadata` is the dict `make_ref` serialises, not `stratum.metadata`.** Write
  `{"creative": config.name, **md}` where `md` is exactly what `create_creative` builds
  (`marketing.py:446-453`) — `{**stratum.metadata, **study.general.extra_metadata,
  "form": destination.initial_shortcode, **additional_metadata}`. Freeze the stratum's
  metadata instead and `creative` and `form` silently go missing from the `ad` path,
  which is precisely the silent miscount this design exists to prevent. The invariant is
  directly testable:

  ```python
  _group(make_ref(creative_name, md).split(".")) == frozen_metadata
  ```

  That equality is what makes `location: "ad"` a drop-in for `location: "metadata"` at
  the level of key names — the user writes the same `key` either way.

`resolved_from` records **which write path produced this row** — `'ad_id'` for the
normal case, a Meta ad id captured from the create response — so that a row written later
by some other path (a retrofit, a second network's importer) is distinguishable from one
written at creation.

Note this is a correction to an earlier draft, which defined the column as "which
referral field produced the id" — `referral.ad_id` versus `referral.source_id`. That is a
property of an *arrival*, not of an ad, and this table is written at ad creation, before
any arrival exists. The column could not have carried that meaning. The inbound question
it was meant to answer needs no column anywhere: `md.platform` already distinguishes
messenger from whatsapp, and the field fly reads is one-to-one with the platform. Should
that rule ever stop being one-to-one, the fact belongs on the response, not here.

### A3. Publish the mapping CSV (convenience)

**Backfill of live ads is no longer required for correctness.** A study using
`location: "ad"` creates every one of its ads after A1/A2, so every ad it recruits from
has a mapping row by construction. A backfill over `GraphUpdater`'s `state.ads` is
useful only if someone later retrofits an existing study — at which point note that it
cannot cover ads reconciliation has already deleted, and that fly's `messages` history
(which carries `referral.ad_id` and `referral.ref` on the same referral since 2024) is
the better reconstruction source.

**CSV endpoint.** `GET /{org_id}/studies/{slug}/ad-attributions.csv` on the adopt server
— it already has org/study routing and API-key auth
(`adopt/adopt/server/server.py:448`) — plus a dashboard download button.

Users join it against their fly export downstream. No fly→vlab runtime dependency and
no exporter change.

**Flatten metadata into columns.** Keys are uniform within a study, so:

```
ad_id, network, creative, gender, Age, Region, form, created
120254866237980150, facebook, Smiling, women, Like Parents, South East, mnchweek…, 2026-08-16T…
```

Non-key columns are exactly the keys that used to be exploded into `responses.metadata`,
so the user story is one line: **left-join your fly export on `ad_id` and you get your
old columns back, same names.** `ad_id` alone is a sufficient join key (Meta ad ids are
globally unique); `network` rides along for the future.

Deleted ads must remain in the CSV — see the append-only invariant.

### A4. Ref content is a per-destination preference

`create_creative` (`marketing.py:446-485`) currently builds the full ref via `make_ref`
(`:256-260`) and ships it two ways for Messenger: `url_tags=f"ref={ref}"` (`:463`) and a
quick-reply payload in `page_welcome_message` (`make_welcome_message`, `:136-148`). Web
destinations use `url_template.format(ref=ref)` (`:479`).

Add a per-destination option for what goes in the ref slot: the full ref (default,
what every existing study gets) or `destination.initial_shortcode` alone.

**This is not a migration lever and nothing gates on it.** It changes the *creative*,
and `update_ad` compares creatives via `field_contract.COMPARED_AD`, so it must never be
flipped globally — but under the new-studies-only rule there is no reason to flip an
existing study at all. A new study picks its ref content at creation, independently of
whether it declares `location: "ad"` (see *orthogonal knobs* above), and never changes
it.

### A5. First-class ad id on `InferenceDataEvent`

Two fields:

- `ad_id` — the opaque identifier
- `ad_network` — `facebook` today; connector-supplied, matching the mapping's key

**No migration is needed, contrary to an earlier draft of this plan.**
`connector.WriteEvents` marshals the entire `InferenceDataEvent` into a single `data`
JSON column and `GetEvents` scans it straight back — `inference_data_events` has no typed
columns for event fields at all. The two fields ride inside the existing blob, and
declaring them `omitempty` leaves every existing row byte-identical.

The requirement this step actually carries is unaffected: they must be **first-class
typed fields on the struct**, not reserved keys inside `User.Metadata`. A map key would
be a fly-shaped convention every other connector has to imitate, enforced by nothing —
the same shape of mistake as the dotted ref, which was a convention smuggled inside an
untyped blob. The migration was incidental to that requirement, not the substance of it.

**fly connector** (`inference/sources/fly/main.go:180-190`): populate from the
normalized field in fly's responses view. No platform logic — fly already resolved it.

**Other connectors** (Typeform, Qualtrics, Alchemer): populate from their own hidden
field when studies use them. Not required for the first release.

### A6. swoosh: the `"ad"` extraction location, user-declared

The optimizer reads the `inference_data` table (`malaria.py:78`), and metadata becomes
variables in swoosh (`inference/swoosh/inference_data.go:254`, `retrieveFromMetadata`),
driven by each study's `inference_data` conf. Add a third location alongside
`"variable"` and `"metadata"` in `getRetrieveFunc` (`:268-275`).

```go
func retrieveFromAd(mapping map[string]AdAttribution) RetrieveFunc {
    return func(e *InferenceDataEvent, conf *ExtractionConf) (json.RawMessage, bool) {
        a, ok := mapping[e.AdID]
        if !ok {
            return nil, false
        }
        v, ok := a.Metadata[conf.Key]
        return v, ok
    }
}
```

**The user declares these confs.** Same `ExtractionConf` shape as every other location —
`location`, `key`, `name`, `value_type`, `aggregate`
(`inference/swoosh/inference_data.go:21-29`) — so this is one new value in an existing
dropdown, not a new concept in the dashboard.

An earlier draft had vlab *derive* the conf set from the mapping rows, on the argument
that the user had already stated the key set three times and a fourth statement only adds
a way to disagree. We reversed that. The derivation was solving a **naming** problem that
only exists if you invent new names: it had to reproduce whatever the strata predicates
already reference (`md:stratum_gender` in `configuration.py:118-129`, plain `md:gender`
in older studies), and validating that against 5,141 studies was an unbounded research
task. If the user declares the names they already use, there is nothing to reproduce.
Because the frozen metadata is key-for-key the ref's dict (A2), `location: "metadata"` →
`location: "ad"` is a one-word difference at the same `key`.

`aggregate: "first"` is the sensible default for ad-derived variables — attribute the
respondent to the ad that recruited them — and should be the UI default, but it is the
user's field like any other.

**Completeness check.** Independent of derivation, and worth keeping: vlab holds both the
strata (`question_targeting` predicates, `adopt/adopt/configuration.py:118-129`) and the
`inference_data` confs, so it can compare what strata *demand* against what confs
*supply*. A predicate referencing a variable no conf produces is a detectable, loud error
at config time. Today that is invisible — the predicate never matches, the stratum counts
zero, and the optimizer quietly reallocates budget away from it. Same failure family as
A7, caught one layer earlier.

**Load the mapping once, pass it in as data.** The `RetrieveFunc` signature is
`func(*InferenceDataEvent, *ExtractionConf) (json.RawMessage, bool)` — no context, no
error, called per-event-per-conf. A DB call inside it is one query per response. Load
the study's mapping in `swoosh.go` before `Reduce`, and have
`getRetrieveFunc(conf, mapping)` return a closure over it. `Reduce` stays pure and
unit-testable against a fake map; the DB touch stays in the shell.

**Per-study load,** not global: cheaper, and an ad id from another study misses the
lookup rather than silently importing foreign strata. That miss is correct behaviour and
lands in the counters below.

### A7. The three-way split, and making the quiet failure loud

A `retrieve` returning `ok=false` means `continue`: no variable, no stratum match,
optimizer undercount. **Two very different things produce it**:

| Outcome | Meaning | Treatment |
|---|---|---|
| attributed | ad id present, mapping row found | normal |
| organic | no ad id on the event | expected; count, don't alarm. Includes post-sourced CTWA arrivals (B1). |
| **unmapped** | ad id present, **no mapping row** | always a bug; alert |

The machinery already exists: `extractValue` returns `*ExtractionError` keyed by entity
with occurrence counts, aggregated and written to `study_run_events` and surfaced in the
dashboard (`inference/swoosh/events.go:69`, `inference_data.go:282-315`). "N events with
unmapped ad ids" becomes a visible, counted study error.

Under the new-studies-only rule this split is unambiguous — there is no overlap era in
which a variable could arrive by two routes, so no mismatch counter and no arbitration
question. An earlier draft carried one; it is dropped.

**Unmapped is self-healing.** Because swoosh recomputes the whole study every run
(finding 7), inserting a missing mapping row retroactively fixes every prior run's
attribution. The counter is therefore a *current-state* measure, not a cumulative one,
and it should drop to zero on the run after a fix.

**Build this alongside A6, not after.** It is what keeps the silent-miscounting failure
mode from shipping.

### A8. `FlyWhatsAppDestination` — new scope

Finding 9: vlab cannot create click-to-WhatsApp ads at all today. `create_creative`
handles Messenger, App and Web only, and nothing sets `autofill_message`. This is
required for CTWA regardless of attribution, and it is where finding 8 lands: the
autofill message is the carrier fly already reads, so the destination's config decides
whether respondents see `form.mnchweeklanguage` or the full dotted ref in their compose
box.

Needs: the destination type in `study_conf.py`, a `create_creative` branch with the
WhatsApp call-to-action, the `autofill_message` field, and the dashboard form.

---

## Stream B — fly

Purely additive. Nothing is removed, nothing is gated, nothing observable changes for
any existing study. Ships in any order relative to Stream A.

### B1. Resolve and stamp the ad identifier

`getMetadata` (`replybot/lib/typewheels/utils.js:75-105`) builds `md` from the ref's
dot-pairs plus fly-owned synthetic keys — `form`, `startTime`, `pageid`, `platform`,
`randomSeed`. It never reads `referral.ad_id` or `referral.source_id`; today they are
dropped after `messages`.

Add `md.ad_id`, resolved from the referral:

- Messenger: `referral.ad_id`
- WhatsApp: `referral.source_id` **only when `referral.source_type === 'ad'`**

The gate matters. CTWA referrals carry `source_type`, and for an organic reshare of a
page post it is a post — `source_id` is then a *post* id. Capturing it unconditionally
writes post ids into the ad_id field, where they never match the mapping and pile up
forever in the "unmapped" bucket that exists to catch real bugs. The post case is an
organic arrival and should fall through as one.

Notes:
- `md.pageid` / `md.platform` / `md.startTime` are the existing precedent for fly-owned
  synthetic keys in the same dict — this is idiomatic, not a hack.
- Synthetic keys are assigned *after* `_group`, so fly's key wins any collision with a
  ref token.
- `getMetadata` runs once at `conversation_started` and persists in state, so one
  capture stamps every subsequent response.
- No `ad_network` key needed: `md.platform` already holds `messenger`/`whatsapp`
  (`utils.js:99`), and vlab derives the network from the channel. When TikTok arrives,
  that mapping changes in vlab, not fly.
- `getMetadata` is pure, so the resolution rule is testable in isolation.

**Optionally** also stamp `ctwa_clid` — the Conversions API attribution key
(`replybot/lib/event-normalizer.js:292-294`), needed by the separate
`planning/ad-conversion-feedback/` stream. Capturing it here means that work needs no
second fly change. Decide whether it must be snapshotted per response or can be read
from `messages` when needed.

### B2. Expose it in the view

Add `ad_id` as a first-class column on `/api/v1/responses`
(`dashboard-server/queries/responses/response.queries.js:106-130`) rather than leaving
it inside the metadata blob. That endpoint is already a curated projection, so this is
what it is for.

### B3. Expose it in the export

Add `ad_id` as a column on the responses export (`exporter/`), so the manual join path
exists for researchers working from a raw CSV in R or Stata. No `vlab_prepro` change, no
join logic in fly.

---

## Ordering

**The one hard prerequisite: A1+A2 must ship before the first ad of any study that will
use `location: "ad"`.** There is no backfill that rescues a miss — an ad created before
the mapping table exists leaves no row, and every respondent it recruits lands in the
unmapped bucket permanently. Everything else in this plan is flexible; this is not.

| # | Stream | Step | Depends on |
|---|---|---|---|
| 1 | vlab | A1 + A2 — capture the created id, mapping table, freeze the ref's dict | — |
| 2 | fly | B1–B3 — stamp `md.ad_id`, expose in view, expose in export | — |
| 3 | vlab | A5 — `ad_id`/`ad_network` on `InferenceDataEvent` + fly connector | B2 |
| 4 | vlab | A6 + A7 — `location: "ad"`, unmapped counter | A2, A5 |
| — | vlab | A8 — `FlyWhatsAppDestination` | independent; needed for CTWA at all |
| — | vlab | A3 — CSV endpoint | any time after A2 |
| — | vlab | A4 — per-destination ref content | a config option, not a sequenced step |

Steps 1 and 2 are independent and run in parallel. A8 is independent of the attribution
work and can run in parallel with either.

**The dependencies above are deploy-order, not merge-order.** fly and vlab release
independently, and A5's connector reads `ad_id` off fly's responses view — so B2 must be
*in production*, not merely merged, before A5 does anything but write nulls.

That extends the hard prerequisite. `getMetadata` runs once, at `conversation_started`,
and its result persists in state (`replybot/lib/typewheels/utils.js`) — so a conversation
that began before B1 deployed never acquires an `ad_id`, and no later message backfills
one. A conversation is stamped or it is not, forever.

So the full precondition for a study using `location: "ad"` is **A1+A2 and B1 both in
production before that study recruits its first respondent** — not merely before its
first ad is created. A study that starts recruiting between the two deploys produces a
permanently mixed cohort: early respondents carrying no `ad_id`, unrecoverable by any
later fix, and indistinguishable in the data from organic arrivals. That is exactly the
silent miscount this design exists to prevent, arriving through the release process
rather than through the code.

## Validation

**Free, and available before any production change.** Meta has been sending `ad_id`
since 2024, and those referrals are in fly's `messages` now. Read them offline against a
backup, extract `(userid, ref, ad_id)`, and compare ref-derived strata against
mapping-derived strata. Pure read, zero writes.

Production history says the two should agree exactly — `ad_id` has been a strict
superset of `ref` since 2024 — so any disagreement is a bug in the new path, and a
cheap, low-risk way to find it.

**Live comparison on a new study.** Declare *both* confs on one new study under
**different names** — `md:gender` at `location: "metadata"`, `ad:gender` at
`location: "ad"` — and diff them offline. Distinct names mean the two never collide in
`addValue` and no aggregate function silently arbitrates between them, which is what
made a same-name side-by-side a hazard rather than an instrument.

**No historical backfill of anything.** Rows written before the switch already carry
the exploded metadata — that *is* their attribution. Existing studies keep resolving
through `location: "metadata"` forever, so there is no era boundary any single config
has to straddle.

**`messages` retention becomes load-bearing** for the offline validation above — it is
the only durable copy of the raw referral. Confirm nothing expires 2024 data before it
runs.

## Open

- **Does the WhatsApp arm of a multi-destination ad carry `source_id`?** The last
  unknown that could change this design. Probe ad `probe.multi.two` (campaign
  `120254876244710150`) is built and preview-clickable; preview clicks produce genuine
  referrals, so this costs nothing.
- **Instagram's referral shape** — determines whether this extends to Instagram or only
  appears to.
- **Should `FlyWhatsAppDestination` default its autofill message to shortcode-only or to
  the full ref?** The prefill is respondent-visible and respondent-editable, which argues
  for the shortcode; studies wanting ad metadata in fly survey logic need the full ref
  (finding 8). A default has to be picked either way.
- **`chat_log` / `full-messages` exports** — do those need attribution too, or is
  `responses` the only export where strata matter for analysis?
- **`.claude/worktrees/variables-strata-pipeline/`** has its own copies of `responses.py`
  and `marketing.py`. Check for collision before starting A1/A4.
