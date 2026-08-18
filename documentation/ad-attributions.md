# Ad attributions: vlab owns the ad → stratum join

**Status:** complete. A1/A2 write the mapping, A5–A7 read it, C1 lets a
researcher declare an ad-derived variable in the dashboard, A3 exports the
mapping as CSV, A8/A9 add click-to-WhatsApp, and A4 lets a study stop shipping
its stratum vocabulary in the ref at all. Every part is per-study and opt-in:
nothing existing changes until someone changes it. The one piece outstanding is
the dashboard form for the WhatsApp destination type.

**The join key changed.** The mechanism first shipped joining on `ad_id`; it now
joins on an opaque `ref_token` that rides the ref itself. The earlier work is
**superseded, not wrong** — the capture and monitoring halves survive untouched,
only the join half was replaced, and by something of exactly the same shape. See
*The join key* below, and `planning/encoded-ref-attribution-plan.md` for the
design discussion.

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
adopt mints ref_token -> deterministic from (study, stratum, creative,
                         destination); rides inside the ad's encoded ref
adopt creates ad      -> Meta returns ad_id
                      -> ad_attributions row frozen, with BOTH keys (A1/A2)

respondent arrives    -> fly decodes the encoded ref locally and stamps
                         metadata.vt = <token>          (no lookup, no shared state)
                      -> and separately resolves ad_id where Meta sends it
                         Messenger: referral.ad_id
                         WhatsApp:  referral.source_id, when source_type == 'ad'

fly connector         -> the token rides item.Metadata into User.Metadata;
                         ad_id is copied onto InferenceDataEvent.AdID   (A5, Go)

swoosh                -> joins metadata[key] -> ref_token -> frozen metadata,
                         emits the study's declared variables           (A6, Go)
                      -> counts organic vs unmapped                     (A7, Go)
```

## What changed, and what deliberately did not

Additive, and opt-in per study. **No existing study's ad-creation behaviour
changes unless someone changes that study's conf.** Reconciliation compares
creatives via `field_contract.COMPARED_AD`, so any change to what a creative
emits rewrites that study's ads on its next run — which is why every lever here
is per-destination and defaults to the historical behaviour. Existing studies
keep the dotted ref indefinitely and are never migrated.

Two later changes did touch the ref itself, both deliberately containable:

- **A4** added `include_metadata_in_ref`, defaulting to the historical full ref.
  A study only thins its ref when someone turns it off.
- **D2** made `make_ref` encode `.` and `~`. Only values actually containing
  those serialise differently, so only an already-broken study is affected — and
  a production measurement found none. See *Ref encoding* below.

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
| 1 | fly's `getMetadata` | Decodes the encoded ref into `md.form` + `md.vt`. Both `vt` and `ad_id` are **fly-owned**: each is unconditionally deleted before fly stamps its own, so a dotted ref like `creative.X.vt.injected.form.Y` cannot pre-populate a join key. Trustworthy input, by construction. |
| 2 | fly's responses view | Exposes `ad_id` as a first-class column, resolved at `conversation_started`. Captured for monitoring; not joined. |
| 3 | `sources/fly/main.go` | The token rides `item.Metadata` into `User.Metadata` with no connector change — that is the whole point of "the token is in metadata". `AdID` / `AdNetwork` are still copied across. |
| 4 | `swoosh/swoosh.go` | `GetAdAttributions` loads the study's mapping — once per run, before `Reduce`. |
| 5 | `swoosh/inference_data.go` | `retrieveFromMetadata` closes over that mapping and resolves `mapping: "ad_table_lookup"` confs; `adAttributionOutcome` classifies each event three ways. |

`AdID` and `AdNetwork` are **typed fields on `InferenceDataEvent`**, and remain
so. The `ref_token` deliberately is **not**: it rides `User.Metadata` under a
key the conf declares. The two choices look contradictory and are not. A typed
field is the right shape for a fact every connector could supply the same way;
the token is a fact only a platform that participates in vlab's own ref format
can supply, and the conf declaring where it lands is what lets a second such
platform join with no structural change. What the typed field bought — the
contract being explicit rather than a convention smuggled inside an untyped blob
— the conf's `key` field buys here instead.

**This needed no migration.** `inference_data_events` stores the whole event as
one JSON blob in its `data` column, and the new fields are `omitempty`, so every
existing row stays byte-identical.

### The join key: `ref_token`, and why `ad_id` is no longer it

Both are opaque ad identifiers resolving to the same frozen row. They are the
same shape and differ only in the carrier:

| | Carrier | Reach |
|---|---|---|
| `ad_id` | Meta's referral webhook | **~31%** of Messenger ad entrants — Meta simply does not send the referral for the rest |
| `ref_token` | the ref itself, which vlab authors | ~100% |

That is the whole argument. `ref_token` is the superior version of the same
idea, so `ad_id` is **deprecated as a join** — not deleted. The column stays on
the row, the field stays on the event, and fly's recruitment-health alerting
gates on ad_id presence. If a platform ever genuinely needs an id-carrier join,
it comes back in exactly this shape.

The token is minted deterministically from `(study_id, stratum_id,
creative_name, destination_name)` via `mint_ref_token` (blake2b, 5 bytes,
domain-separated). Determinism is non-negotiable: the ref is part of the
creative and reconciliation compares creatives, so a random token would rewrite
every ad on every run. `marketing.assert_ref_tokens_unique` checks for
collisions at instruction-generation time — the last cheap moment, before any
ad exists on Facebook and is spending.

`ad_attributions` keeps `(network, ad_id)` as its primary key and gains
`ref_token` as the join column. A NULL `ref_token` is the normal case and means
something: that ad's ref carries no token, because its destination is not in
`ref_mode: "encoded"`. Such a row loads but is not indexed — and critically it
must not land under `""`, where every tokenless respondent would match it.

### The `mapping` concept

Today's `ExtractionConf` reads a value from a `location` and uses it as-is. One
new field, `mapping`, says what to do with the value read:

- **`"raw"`** (and `""`, the default) — the value read is the answer. Today's
  behaviour, so every conf ever written keeps meaning what it meant.
- **`"ad_table_lookup"`** — the value read is a token; look it up in
  `ad_attributions` by `ref_token` and return the stratum variable off the
  frozen row.

`location` is **unchanged** (`metadata` | `variable`). The token lives in
metadata, so reading it is an ordinary metadata read — which is why `"ad"` was
never really a location, and why it is now **removed**. Both remaining fields
are contextual to the mapping:

```
// legacy — the value rides the ref inline
{location: "metadata", key: "gender", mapping: "raw", name: "gender"}
  ->  metadata["gender"]  ->  "women"

// encoded — a token rides the ref; the value is looked up
{location: "metadata", key: "vt", mapping: "ad_table_lookup", name: "gender"}
  ->  metadata["vt"]              (key = WHERE TO READ: the token)
  ->  ad_attributions[token]      (the mapping — the ONLY automatic part)
  ->  row.metadata["gender"]      (name = WHICH stratum variable)
  ->  "women"
```

- **`key`** — where to read. For `raw` this addresses the value itself; for a
  lookup it addresses the token. Same field, contextual to `mapping`, exactly as
  `key` was already contextual to `location`.
- **`name`** — the output variable name and, for a lookup, **also the key into
  the frozen row**. This double duty is the one constraint the design carries.
  It is acceptable because you name the output after the stratum variable
  anyway.

A lookup is valid only on `location: "metadata"`. The combination with
`"variable"` is rejected at config time *and* refused by `getRetrieveFunc`,
because swoosh reads a lookup conf's `key` as the declaration of where the token
lives — one stray conf would have every respondent in the study classified
against the wrong metadata key, and a token that is not there reads as an
organic arrival, which does not alarm.

### The token's metadata key is conf-declared, never hardcoded

swoosh never assumes the token is at `metadata["vt"]`. The conf's `key` field
declares where it is; fly stamps `vt` as a convention and the conf says
`key: "vt"` to match. A platform surfacing the token under a different key just
declares that key. The only automatic part of the whole mechanism is
`token -> ad_attributions row -> stratum metadata`.

**fly owns `vt`.** `getMetadata` deletes `md.vt` unconditionally, before the
decode branch, exactly as it owns `ad_id`. Without that, a dotted ref like
`creative.Smiling.vt.injected.form.mnchweek` would set `md.vt` via the ordinary
dot-pair parse — and since the decode branch only fires when `md.r` is present,
nothing would overwrite it. That author-injected value would then be the join
key vlab attributes the respondent by: a silent mis-join onto any row whose
token matched.

### The mechanism is conf-declared, never selected at runtime

**No key-sniffing.** The attribution mechanism is a property of the study conf,
fixed at config time, never chosen at read time by whichever key happens to be
present on an event. A token that misses the mapping is an **unmapped error**,
never a silent retry against `ad_id`.

A runtime choice would make a genuine miss indistinguishable from a study
part-way through switching mechanisms, and every debugging session an
archaeology exercise. There is likewise no cross-check between the two when both
are present: `ad_id` is not joined, so there is no second result to disagree
with.

### Why there is still no fallback to `location: "metadata"`

**`ad_table_lookup` is for new studies only, and a fallback to the raw value
would be a bug.** swoosh recomputes a study's entire history on every run:
`GetEvents` loads every event and `InsertInferenceData` upserts. So swapping an
existing study's confs over would not migrate it forward — it would
retroactively re-attribute its whole back-catalogue through a path those events
cannot satisfy. Rows written before that study's ads carried an encoded ref have
no token and are never backfilled, so every historical respondent would extract
nothing, match no stratum, and vanish from the counts. Strata would read as
massively under-recruited and the optimizer would flood budget toward them.
Worse, an event with no token is indistinguishable from an organic arrival, so
it lands in the do-not-alarm bucket.

A one-off backfill is the answer if someone ever genuinely must retrofit a
study — not a standing code path whose justification will be forgotten.

Note that ref content and inference source stay orthogonal: the destination's
`ref_mode` (the write side) and the conf's `mapping` (the read side) are
independent settings, and the half-migration guard catches the incoherent
combinations.

### The token is unquoted before joining

Metadata values are JSON, so the token arrives as a quoted JSON string
(`"a1b2c3d4e5"`) while `ref_token` comes out of a text column bare. Joining the
raw bytes would miss **every single time**, on a value that looks correct in
every log line it appears in. `metadataToken` does the unquoting; a value that
is not a JSON string is treated as no token at all, so it lands in a counter
someone can see rather than being stringified into a guess.

### Where the database touch lives

`RetrieveFunc` is `func(*InferenceDataEvent, *ExtractionConf) (json.RawMessage,
bool)` — no context, no error, called once per event per conf. A query inside it
would be one query per response. So the mapping is loaded once per study in
`swooshStudy` and passed into `Reduce` as plain data; `Reduce` has no pool in
its signature, which makes a per-event query unrepresentable rather than merely
avoided, and keeps `Reduce` unit-testable against a fake mapping.

The load is **per study**, not global. A cross-study token then misses the
lookup instead of silently importing another study's strata — and that miss is
correct behaviour that lands in the counters below.

`AdAttributions` is a struct with a single index, `ByRefToken`, rather than a
bare map — so every call site says out loud which key it joined on. There is
deliberately no `ByAdID`: adding a second index is how runtime mechanism
selection creeps back in.

## The three-way split

A retrieve returning `ok=false` means `continue`: no variable, no stratum match,
optimizer undercount. Three different things produce it and only one is a bug.

| Outcome | Meaning | Treatment |
|---|---|---|
| attributed | token present, mapping row found | normal; no event |
| organic | no token on the event | expected; counted as `extraction_warning`, does not alarm |
| **unmapped** | token present, **no mapping row** | always a bug; counted as `extraction_error` at severity `error` |

Classification happens once per **event**, not per conf. An event either carries
a token or it does not, and that token either resolves or it does not — none of
which depends on the conf. Counting per conf would multiply one organic arrival
by however many lookup confs the study declares.

Every outcome's details name the mechanism (`ref_token`) and the metadata key it
read, so a miss is diagnosable from the recorded row rather than from the era it
was written in. `ad_id` rides along in the details of an unmapped event too —
not as a second attribution path, but so a miss can be lined up against fly's
recruitment-health signals.

Organic is worth counting even though it is expected: shortcodes are shareable
by design, so a jump in the organic share means a leaked shortcode. Unmapped is
always a defect — vlab created an ad and failed to record what it meant.

**Unmapped is self-healing.** Because swoosh recomputes the whole study every
run, inserting a missing mapping row retroactively fixes every prior run's
attribution. The counter is a current-state measure, not a cumulative one, and
the dashboard's 90-minute recency window ages the stale error out without anyone
closing it.

A key that is missing from a row that *was* found is deliberately not counted as
unmapped: the respondent is mapped, the conf just asked for a stratum variable
the ad was not frozen with. That is a conf problem, and inflating the unmapped counter with it
would blunt the signal that exists to catch real bugs.

## Declaring an ad-derived variable

vlab does not infer these confs, so the dashboard form is the only way a
researcher states one. In the study's **Inference Data** step, a fly source's
location dropdown offers Metadata and Variable — and choosing **Metadata**
reveals a second dropdown, the mapping:

> **Use the value as it is** · **Ad (which ad recruited them)**

Choosing the ad option produces `location: "metadata"`, `mapping:
"ad_table_lookup"`. The two text fields then mean something different from
usual, and the form's prompts say so, because getting them backwards is the easy
mistake:

| Field | For a raw read | For an ad lookup |
|---|---|---|
| `key` | the metadata key holding the value | the metadata key holding the **token** — usually `vt` |
| `name` | what to call the variable | the **stratum variable** to pull (`creative`, `gender`, `Age`) — which is also what it is called |

There is no response to select in either case, because the value is looked up by
key rather than found by walking a path into the respondent's answer.

Switching a conf away from Metadata resets its mapping to raw. Without that, a
conf could end up `variable` + `ad_table_lookup`, whose `key` swoosh would read
as a declaration of where the token lives.

**The lookup is offered on fly sources only.** The Qualtrics and Typeform
connectors carry no ad token, so offering it there would let someone configure a
variable that silently yields nothing forever. The two forms are separate
modules for that reason: since `location: "ad"` was removed, their *location*
lists are identical, and what stays per-source is the *mapping*. Qualtrics
exports an empty `mappingOptions` — exported precisely so a test can assert the
absence rather than the module merely not mentioning it. The guard is there to
survive a future refactor that merges the forms.

The seam opens without a structural change: a platform that starts surfacing the
token adds the option to its own form and declares whichever metadata key it
arrives under.

Nothing between the form and swoosh constrains `location` or `mapping`: both are
bare strings in the dashboard's TypeScript and in the Go API's opaque conf
storage. Python's `ExtractionConf` is the one place that validates them —
rejecting an unknown mapping, and a lookup on a non-metadata location.

### Config-time checks

Two, both in `adopt/adopt/study_conf.py`. Note that `location: "ad"` is **not**
one of them: it was never live in any study, so there is nothing to validate
away and no migration to guard. It is simply an unknown location now, and gets
the same error any typo does.

- **`disagreeing_token_keys`** — all `ad_table_lookup` confs under one source
  must read the token from the same metadata key. One respondent has one token,
  in one place; confs on another key attribute nobody, and silently, because a
  token that is not there looks exactly like an organic arrival. It **warns**
  rather than raising: swoosh takes the first key it finds and carries on, so a
  raise here would make that tolerance unreachable and would stop ad
  reconciliation over a miscount.
- **`thins_its_ref_without_reading_the_mapping`** — see the half-migration guard
  below.

## The mapping CSV export

`GET /{org_id}/studies/{slug}/ad-attributions.csv`, on the same org/study
routing and auth as every other study endpoint.

```
ad_id, network, ref_token, creative, gender, Age, Region, form, created
```

The frozen blob is flattened into columns under its own key names, which makes
the whole export one sentence: **left-join your survey export on the join key
and your old metadata columns come back, named as they always were.** Both keys
are exported: `ref_token` is what swoosh joins on, and `ad_id` is there for the
studies whose analysis already keys on it, and for lining a row up against
Meta's own reporting. True only
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
pulls it, a lookup conf works but its ads still ship vlab's entire stratum
vocabulary into fly on every message — the frozen row *duplicates* the ref
rather than replacing it, and nothing is actually decoupled.

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
a study would freeze rows containing nothing but `form`; every lookup conf would
resolve to nothing, every stratum would count zero, and the optimizer would
reallocate on empty data. Silent, total, and unrecoverable after the fact,
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
does not change. That matters more than it looks: `(network, ad_id)` is the
table's primary key, so a flip that minted new ids would strand every
`ad_attributions` row the study already had and leave its past respondents
unattributable. Both properties are asserted.

### The half-migration guard

Thinning the ref only works if the study *also* reads the mapping. Do one
without the other and the study has no attribution at all: the ref no longer
carries the stratum, and nothing looks the ad up. Every stratum counts zero and
the optimizer reallocates on empty data — the same silent shape as an unmapped
ad, arrived at from the opposite direction.

`study_conf.thins_its_ref_without_reading_the_mapping` detects it and
`malaria.warn_on_thinned_ref_without_mapping` logs it: a fly destination whose
resolved `ref_mode` is not `"metadata"` while no extraction conf declares
`mapping: "ad_table_lookup"`. Both thin modes count, `"shortcode"` and
`"encoded"` alike — they differ in what carries the join key, not in the thing
this guard is about. It **warns rather than raises**, because it is not
certainly wrong — a study recruiting uniformly, with no `question_targeting`, needs no
stratum attribution and is entitled to a thin ref. Same reasoning as the
completeness check below.

It covers WhatsApp destinations too, since their default is already thin: a
CTWA study that never declares a lookup conf has no attribution at all, and
should hear about it.

### Web and App stay on full refs

Deliberately. Neither type has an `initial_shortcode`, because their
`url_template` / `deeplink_template` already points at a specific survey —
routing is not a job the ref does for them. Making them shortcode-only would
mean inventing a conf field for a token neither needs. The equivalent decoupling
for a web platform is carrying the token in the ad URL, which is separate work. Messenger is where every existing study lives and where the ref actually
costs something.

## Ref encoding, and why the creative name mattered most

The ref is a dot-separated grammar, so every token has to survive being split on
`.` and URL-decoded. Three things go into one: the creative name, each metadata
key, and each metadata value.

**Python's `quote()` is not enough on its own.** It never escapes `.`, `-`, `_`
or `~` — they live in urllib's `_ALWAYS_SAFE`, and passing `safe=''` does *not*
override that. Measured: `quote('a.b') == 'a.b'`, `quote('x~y') == 'x~y'`. Two
of those four break a ref:

| Character | What it does |
|---|---|
| `.` | it *is* the separator, so a dotted token silently mis-pairs everything after it |
| `~` | outside fly's WhatsApp token alphabet, so the whole ref fails the entry gate |

`-` and `_` are separator-safe and inside the gate alphabet, so
`marketing.ref_value` leaves them alone; encoding them would churn refs for no
benefit.

### The severity asymmetry

Not obvious from the code, and the reason the creative name mattered more than
anything else:

- A dotted **value** shifts the pairs that follow it. The respondent is
  **mis-attributed** — wrong stratum, wrong counts.
- A dotted **creative name** sits at the front, so it shifts *everything* after
  it, `form` included. The respondent is **misrouted** — dropped into a
  different survey altogether.

And the name was the *least* protected of the three: interpolated completely
raw, with no `quote()` call at all, while values at least got partial escaping.
Study `unicef-immunization-kyrg` had creative names ending `.png` live for
roughly nine hours in January 2023. Nothing caught it; the timing did.

All three segments now go through `ref_value`.

### Containment

Purely prophylactic. A production measurement across every conf revision — all
ref contributors, 3,958 metadata pairs, 618 creative names — found **zero**
affected studies, and downstream scans over 17.8M response rows show no
corruption signature. Nothing was remediated, and nothing needed to be.

Only values actually containing `.` or `~` serialise differently, so only an
already-broken study could see its ads rewritten. Asserted directly: the
recorded production values all produce byte-identical refs.

Two things deliberately do **not** change:

- **The Facebook ad name.** `create_ad` uses the raw creative name, and
  reconciliation matches ads by name — encoding it there would orphan every live
  ad and mint new ids, the `ad_attributions`-stranding failure.
- **The frozen blob.** `ref_metadata` holds raw names and raw values. Encoding
  is transport; the blob is truth.

### Deploy ordering

Messenger is safe either way — its parsing is generic and `decodeURIComponent`
handles `%2E` on production fly today. Only the **WhatsApp** gate needs fly's
widened pattern deployed first; before that, an encoded value fails the match.
There is deliberately no gating for this in code.

## Click-to-WhatsApp destinations

`FlyWhatsAppDestination` is shaped after `FlyMessengerDestination`, minus
`button_text` (WhatsApp has no quick-reply button — the respondent gets a
prefilled compose box) and plus `include_metadata_in_ref`.

Both fly destinations fold `form` into `creative_metadata` identically, so the
frozen `ad_attributions` blob has the same shape on either channel and a study
on a lookup conf reads the same keys regardless of how respondents arrived.

### Why the WhatsApp ref is a different string

A CTWA referral carries **no advertiser-settable `ref`** — `url_tags` was
measured not to reach WhatsApp at all. fly instead recovers the shortcode from
the ad's autofill text, which prefills the respondent's first message, and
matches it against an anchored full-match pattern (`WHATSAPP_ENTRY_REF` in
`replybot/lib/event-normalizer.js`):

```
/^(?:start\s+)?form\.((?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+
                      (?:\.(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+)*)$/i
```

Two things follow, both verified directly against that regex:

1. **`make_ref`'s output can never match.** The pattern anchors on `form.`;
   `make_ref` leads with `creative.`. No value is safe enough to fix that, so
   WhatsApp needs its own **form-first** serialisation —
   `marketing.whatsapp_autofill`, emitting `form.<shortcode>[.key.value…]`.
   This one is structural and has not changed.
2. **Every token is `[A-Za-z0-9_-]` or a percent-encoded octet.** The `%XX`
   half was added on fly@`feature/ad-id-attribution` `37e1e06e`. Before it, a
   space was undeliverable raw *and* encoded, because `%` was not in the
   alphabet either — encoding traded one rejected token for another.

**A failure here is silent, which is what makes it dangerous.** Meta delivers
the text intact — dots *and* spaces both survive `autofill_message.content`,
measured against live ads — so nothing rejects it upstream. fly's pattern
rejects it, no `conversation_started` is derived, and the arrival falls through
to `FALLBACK_FORM`: a real survey, so those respondents look like completions
rather than errors. That is the VIR-19 shape, which took four days to spot.

### Full-ref mode: once rare, now workable

The widened gate changed this substantially. Measured against the production
stratum values recorded in `planning/ad-id-attribution.md`:

| | Deliverable |
|---|---|
| old gate, raw values | **5 of 9** |
| new gate, encoded values | **9 of 9** |

`Static English - Girls`, `Bauchi State`, `Like Parents` and `South East` were
all undeliverable and now travel fine. The only residual is `/`, which
`quote()` keeps literal by default and the gate does not accept — it corrupts
nothing, it is simply refused at config time.

`include_metadata_in_ref` stays **off by default** all the same, for reasons
that never depended on deliverability: the optimizer does not need it, since
the ad-table join carries stratum identity regardless, and the autofill text is
**visible to and editable by the respondent**. The only reason to turn it on is
fly survey logic that branches on ad metadata — but a study that wants it is no
longer blocked by its stratum vocabulary.

**The shortcode keeps the narrow alphabet**, deliberately, even though the gate
would now accept it encoded. A metadata value is only ever carried by an ad,
but a shortcode is shareable by design: someone texts `form.<shortcode>`
straight into WhatsApp by hand, and a hand-typed space is a literal space, not
`%20`. A shortcode has to be typeable, not merely encodable.

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
fly survey logic *and* declare a lookup conf for the optimizer.

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
| Migrations | `devops/migrations/20260816000000_add_ad_attributions.{up,down}.sql`, `devops/migrations/20260818000000_add_ad_attributions_ref_token.up.sql` |
| Schema bootstrap (second copy — keep in sync) | `devops/helm/migrations/init.sql` |
| Provenance construction | `adopt/adopt/marketing.py` |
| Instruction plumbing | `adopt/adopt/facebook/{update,reconciliation}.py` |
| Write path | `adopt/adopt/{malaria,campaign_queries}.py` |
| Completeness check, mapping validation, token-key agreement | `adopt/adopt/study_conf.py`, `adopt/adopt/malaria.py` |
| Token minting + the encoded ref | `adopt/adopt/ref_encoding.py`, `adopt/adopt/marketing.py` |
| Ref decode (fly) | `replybot/lib/typewheels/utils.js`, `replybot/lib/event-normalizer.js` |
| CSV export | `adopt/adopt/server/csv_export.py`, `adopt/adopt/server/server.py` |
| WhatsApp destination + ref validation | `adopt/adopt/study_conf.py`, `adopt/adopt/marketing.py` |
| Ref mode (`ref_mode`, `include_metadata_in_ref`) | `adopt/adopt/study_conf.py`, `marketing.messenger_ref` |
| Dashboard form | `dashboard/src/pages/StudyConfPage/forms/inferenceData/{flyExtraction,qualtricsExtraction}.ts`, `FlyExtraction.tsx` |
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

Full design: `planning/ad-id-attribution.md` for the original ad-id work, and
`planning/encoded-ref-attribution-plan.md` for the encoded-ref rework that
replaced its join half.
