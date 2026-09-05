# adopt

Core service for managing Virtual Lab studies: campaign orchestration, creative
management, and publishing ads to Facebook.

## Destination experiments

A study's **destinations** are the places a respondent can land after clicking an
ad — for Messenger, a `FlyMessengerDestination` naming the survey's
`initial_shortcode`. Each creative names the destination it belongs to via its
own `destination` field.

A `SimpleRecruitment` study runs one campaign. A
`DestinationRecruitmentExperiment` instead runs **one campaign per destination**,
each an arm of the experiment, with `budget_per_arm` and `max_sample_per_arm`
applied to each. The arm a campaign represents is identified by matching a
destination name against the campaign name.

### Creative → destination pairing

`pair_creatives_with_destinations` (`adopt/marketing.py`) selects the creatives
belonging to the current arm and pairs each one with the destination its own
config names. `adset_instructions` publishes from those pairs.

The invariant is that **a creative is only ever published with the destination it
names** — never another creative's. This matters because the destination's
`initial_shortcode` is baked into the ad's referral `ref` at publish time
(`make_ref` → `make_welcome_message`), and the bot reads that ref to decide which
survey the respondent enters. A mispaired creative silently recruits people into
the wrong arm's survey, and the only way to correct it is to republish the ad.

The pairing is returned as `(creative, destination)` tuples rather than two
parallel lists. This is deliberate: an earlier implementation filtered the
creatives per arm but built the destinations from the unfiltered list and joined
them with `zip`, which truncates to the shorter input rather than failing. Every
arm after the leading one silently inherited the leading arm's destinations, and
because nothing raised, it went unnoticed until a study large enough to show it
in the response data. Pairing into tuples makes the two impossible to
misalign.

`test_marketing.py` covers this with contiguous, interleaved, and unequal-sized
arm orderings — ordering must never influence the result.

### Ad-set fields are agreed across a stratum's pairs

`destination_type` and `promoted_object` are **ad-set** fields, while
destinations are named **per creative**. One ad set per stratum, many ads inside
it — so channel is necessarily uniform within a stratum and something has to
enforce agreement. Two matching pairs of functions do it:

| Per pair | Agreed across the stratum | Raises when |
|---|---|---|
| `promoted_object_for(config, destination)` | `adset_promoted_object(pairs)` | creatives want different promoted objects |
| `destination_type_for(destination)` | `adset_destination_type(pairs, default)` | creatives want different channels |

Both return `None` for destinations that do not care, and both treat "everything
wants nothing" as agreement rather than ambiguity. `destination_type_for` returns
`None` for Web and App, which fall through to the recruitment conf's value — that
is what keeps existing studies byte-identical.

`destination_type` used to be one string on the recruitment conf consumed by
every ad set of every arm, which meant a `DestinationRecruitmentExperiment` could
not have a Messenger arm and a WhatsApp arm. Deriving it per ad set is what makes
channel-as-an-experiment-arm expressible. See
`documentation/multi-destination-ads.md` §2.

Neither field is in `COMPARED_ADSET`, so both ride only on ad-set creates:
landing the derivation cannot rewrite a live ad set, and **a running study can
never change channel.**

### Destination types

| Type | `destination_type` | Routing carrier |
|---|---|---|
| `FlyMessengerDestination` | `MESSENGER` | `url_tags` + quick-reply payload |
| `FlyWhatsAppDestination` | `WHATSAPP` | `autofill_message` (compose-box prefill) |
| `FlyMultiDestination` | `MESSAGING_MESSENGER_WHATSAPP` | all three at once |
| `WebDestination` / `AppDestination` | *derived from the recruitment conf* | the URL / deeplink itself |

`FlyMultiDestination` carries an **asymmetry worth knowing**: its Messenger arm
is measured against live Meta delivery, its WhatsApp arm has never been
observed and rests on a symmetry inference from the Messenger result. If that
inference is wrong, WhatsApp arrivals land on `FALLBACK_FORM` and look like
completions. `documentation/multi-destination-ads.md` §4 is the procedure that
settles it, and §4.5 the log that records each attempt — run it against the
first multi study rather than assuming.

## The Facebook field contract

Every run, adopt compares the live ads and adsets against what the study config
says they should be, and rewrites anything that drifted. What gets compared is
declared in **`adopt/facebook/field_contract.py`** — one dict per object type,
each field with a sentence saying why we care about it.

The subtle part is that Facebook does not echo everything back the way we sent
it. Two things go wrong, and both cause an endless rewrite loop — we send a
field, Facebook returns something that does not match, we rewrite, forever:

- **`DROPPED`** — fields Facebook accepts on write and simply omits from the
  response. Excluded from comparison.
- **`NORMALIZE`** — fields Facebook returns in a different representation than
  we send: `daily_budget` comes back as a string where we set an int,
  `end_time` as a tz-offset ISO string where we set a naive datetime. Same
  value, so `==` is False forever. Each entry canonicalises both sides first.
  These are hand-written, since a normaliser encodes what "the same" means for
  a field and no probe can infer that.

One rule needs no declaration: if we ask for an **empty** value and Facebook
omits the key, that is agreement, not a difference. Facebook elides empty
values instead of echoing them. Asking for something non-empty and not seeing
it is still a difference, so adding an audience is never swallowed.

An **undeclared** nested drop is still treated as a difference, deliberately.
A real change that must be applied — converting a creative from `photo_data`
to `link_data`, say — looks identical in the data to a field Facebook silently
drops. Nothing distinguishes them, so the call belongs to a human. What the
code does instead is warn loudly, naming the path and the command that
resolves it. (A *whole* top-level field missing from Facebook's response is
skipped rather than rewritten — see `planning/field-contract.md`.)

### Checking the contract against Facebook

```bash
poetry run adopt-probe <study-id-or-name>            # read-only report
poetry run adopt-probe <study-id-or-name> --update   # rewrite DROPPED
```

The probe builds the creative and adset a study's config asks for, fetches the
live ones, and classifies every field path. Ads and adsets are reported
separately but compared the same way — desired first, the order `_eq` requires
so that Facebook's server-added fields are ignored rather than mistaken for
drift. Verdicts:

| verdict | meaning |
|---|---|
| `ok` | sent it, Facebook echoed it back unchanged |
| `dropped` | sent it, Facebook did not return it — declare it or stop sending it |
| `differs` | sent it, Facebook returned something else — a real change |
| `stale` | declared `DROPPED`, but Facebook returns it now — undeclare it |

It exits non-zero when the contract and Facebook disagree, so it can gate a
deploy. `--update` rewrites the `DROPPED` block in place, stamped with today's
date; review it as a normal git diff.

**Point it at active studies.** `end_time` is a rolling 48-hour window recomputed
every run, so an inactive study's adsets are always "behind" and the report is
never clean. That diff means nothing. And read `--update` output before trusting
it: a genuine one-time change — a setting we started sending after those adsets
were built — looks identical to a dropped field. `planning/field-contract.md`
has a worked example.

It is read-only by default because it points at ads spending real money.

Background on the incident that motivated this: `planning/field-contract.md`.

## Ad attribution: the write half

vlab creates exactly one ad per `(creative, stratum)` pair, so the ad id
Facebook hands back already determines that ad's shortcode, creative and
stratum metadata. Historically that identity was encoded into a dotted `ref`
string (`make_ref`) that rode to the survey platform inside every message.
`ad_attributions` persists it instead: a row per created ad, mapping
`(network, ad_id) -> {shortcode, creative, stratum metadata, ref_token}` frozen
at ad-creation time, joined against later rather than parsed out of the ref.
swoosh reads it — see `inference/README.md`.

This half writes the table and mints the token. What an ad's ref actually
carries is `ref_mode`, below; a conf that states no mode keeps the dotted ref it
has always had, because changing a creative triggers ad rewrites across that
study on the next reconciliation run.

### The data path

1. `ad_provenance` (`adopt/marketing.py`) builds a pure lookup keyed by
   `(adset name, ad name)` — which is `(stratum id, creative name)` — from the
   same study conf and pairing functions that build the ads themselves.
2. `adset_dif` / `ad_dif` (`adopt/facebook/reconciliation.py`) stamp the
   matching entry onto each ad-*create* `Instruction`, as its `provenance`
   field.
3. `GraphUpdater.execute` (`adopt/facebook/update.py`) returns the id Facebook
   assigned to a freshly created object alongside the usual report — that id
   used to be dropped on the floor.
4. `run_instructions` / `record_ad_attribution` (`adopt/malaria.py`) writes
   the row once both pieces are in hand, via `create_ad_attribution`
   (`adopt/campaign_queries.py`).

Instruction generation stays pure through step 2: `ad_dif` and `adset_dif`
take the provenance lookup as plain data and return plain `Instruction`s, with
no Graph API and no database. That is what makes them the testable core. The
database write happens only in step 4, in the imperative shell, after
Facebook has actually answered with an id — there is no way to learn that id
except from the create response, so nothing upstream of it could write the
row even if it wanted to.

### The three invariants

- **`metadata` is `ref_metadata`'s output — `{"creative": <creative name>,
  **md}` — never `stratum.metadata`.** `md` comes from `creative_metadata`:
  stratum metadata, plus the study's `extra_metadata`, plus, for fly
  destinations, `form` (the destination's `initial_shortcode`) and any
  `additional_metadata`. Freezing `stratum.metadata` instead would silently
  drop the `creative` and `form` keys. Downstream, an extraction conf asking
  for either would then match no one for that stratum, and the optimizer
  would quietly reallocate budget away from a stratum that is actually
  recruiting fine. It miscounts rather than errors, which is why it matters —
  nothing would ever fail loudly enough to catch it.
- **Append-only, and never rebuilt from live Facebook state.** Reconciliation
  deletes ads that fall out of a study's desired set, but respondents keep
  arriving from deleted ads — reshared page posts persist indefinitely — so a
  row must outlive its ad. That's why the table has no TTL and no foreign key
  to `studies`: a cascading delete is still a delete path, and this table
  isn't allowed one. `get_ad_attributions` reads every row for a study,
  including ones whose ad no longer exists, on purpose.
- **`metadata` is frozen at creation, permanently.** Study confs mutate, so a
  stratum's metadata today is not what it was when the ad was created — even
  a live ad can't be resolved by reading the current conf, only by reading
  the row written when it was made. `create_ad_attribution`'s
  `ON CONFLICT (network, ad_id) DO NOTHING` makes this mechanical: a re-run
  can create the row once but can never overwrite it.

### A note on `network`

`network` is the *ad* network, not the messaging channel. Messenger and
WhatsApp ads are both Meta ads sharing one id namespace, so both are recorded
as `facebook`. Easy to get backwards, and expensive to fix once rows exist —
correcting it means knowing which network to reassign every existing row to.

### Tests

- `adopt/adopt/test_ad_attributions.py` — integration tests against the
  table itself; needs `make test-db`.
- The ad-attribution sections of `adopt/adopt/test_marketing.py` and
  `adopt/adopt/facebook/test_reconciliation.py` cover the pure pieces:
  `ad_provenance`, `ref_metadata`, and the provenance plumbing through
  `ad_dif`/`adset_dif`.
- The round-trip test in `test_marketing.py`
  (`test_frozen_metadata_equals_the_parsed_ref` and its siblings) parses
  `make_ref`'s output back using a reimplementation of fly's own ref parser
  and asserts the result equals the frozen blob. That's the guard against
  `make_ref` and `ref_metadata` drifting apart from each other over time.
- `adopt/adopt/test_ref_encoding_contract.py` — **the cross-repo deploy
  contract**, and the only test here that is really about fly. It asserts vlab
  mints the frozen vectors in `adopt/adopt/ref_encoding_vectors.json`, that the
  mirror decoder round-trips them and refuses the negatives, and that the
  vendored copy of fly's WhatsApp entry pattern agrees with the deployed one.
  fly's half (`replybot/lib/typewheels/ref-encoding-contract.test.js`) decodes
  the same vectors with the replybot **tag** named by fly's
  `devops/values/production.yaml`, extracted straight out of git rather than
  from whatever happens to be checked out. Three things are vendored across
  that boundary — `decode_recruitment_ref`, `WHATSAPP_ENTRY_REF` and
  `ENCODED_REF_VERSION` — and nothing detected drift in any of them until this
  existed. Two had already accumulated. See `documentation/ad-attributions.md`,
  "The deploy contract".

### Probing production

- `adopt/scripts/write_path_probe.py` — read-only. Answers whether adopt has
  actually written an `ad_attributions` row for any ad it created since the
  write path shipped, by comparing Meta's own `created_time` against the table.
  Needed because adopt records nothing per instruction: the only trace of an ad
  create is a log line in a cronjob pod Kubernetes keeps for three runs.
- `adopt/scripts/ctwa_probe.py` — builds and reads back real Meta ads. Driven
  by `planning/ctwa-probe-runbook.md`.
- `planning/encoded-ref-probe-runbook.md` — the end-to-end encoded-ref probe,
  and the record of what has and has not been proven in production.

See `planning/ad-id-attribution.md` for the full design and the phases that
build on this one.

### The mapping CSV export

`GET /{org_id}/studies/{slug}/ad-attributions.csv` (`server.py`,
`get_ad_attributions_csv`) hands back the study's ad -> stratum mapping as a
file. Routing, org scoping and auth match every other study endpoint: it
resolves `study_id` via `get_study_id(user.user_id, org_id, slug)`, which
scopes to the requesting user and 404s rather than leaking another org's
study.

The rows come from `get_ad_attributions` (`campaign_queries.py`) — every
frozen row for the study, unfiltered — and are rendered by the pure functions
in `csv_export.py`. The shape is `ad_id, network, ref_token, <metadata keys...>,
created`: `ad_attributions_csv` flattens the frozen `metadata` blob into
columns under its own key names rather than nesting it, so the whole export
reduces to one sentence for the researcher: left-join your survey export on
`ad_id` and your old metadata columns come back under the same names. That is
only true because the frozen blob is key-for-key the dict the dotted ref used
to carry — the phase-1 invariant above is what makes the export honest.

`metadata_columns` takes those columns as the **union** across all rows, in
first-seen order, rather than trusting the first row's keys. Keys are uniform
within a study in practice, but a stratum conf edited mid-flight leaves some
rows frozen under the old shape and some under the new, and append-only means
both survive — so the header has to account for whichever rows actually
showed up. `column_name` prefixes a metadata key as `metadata_<key>` only
when it collides with one of the row's own columns (`LEADING_COLUMNS` —
`ad_id`, `network`, `ref_token` — or `TRAILING_COLUMNS` — `created` — together
`RESERVED_COLUMNS`), because two columns with the same header is the kind of
thing nobody notices until the analysis is already wrong.

Deleted ads are included, deliberately. Respondents keep arriving from ads
reconciliation has since deleted — reshared page posts persist indefinitely —
so a CSV of only live ads would silently lack rows the researcher needs, and
those respondents would look unattributed. Nothing in the read path filters
on liveness, and nothing should.

`csv_export.py` renders the mapping two ways from one definition — `headers`
gives the column list and `cells` one row's values in that order — so
`ad_attributions_csv` (which writes them positionally) and
`ad_attributions_table` (which zips them into dicts) cannot show different
shapes seconds apart. The table is served as JSON at
`GET /{org_id}/studies/{slug}/ad-attributions`, for the dashboard's Ad
Attributions step.

Tests: `adopt/adopt/server/test_ad_attributions_csv.py`, needs `make
test-db`.

## What a ref carries: `ref_mode`

Before this, the ad-table join already worked, but ads still shipped vlab's
whole stratum vocabulary to the survey platform inside every message: the frozen
row duplicated the ref rather than replacing it, so nothing was actually
decoupled.

```python
RefMode = Literal["metadata", "encoded"]
```

A ref either carries the stratum inline or carries a token that resolves to it.
A study with no stratification simply has a short ref, because
`creative_metadata` has nothing to put in it.

`RefModeDestination` (`study_conf.py`) carries exactly one field:

```python
ref_mode: Optional[RefMode] = None

@property
def resolved_ref_mode(self) -> str:
    return self.ref_mode or "metadata"
```

`Optional` is what keeps the migration free: a conf that states no mode resolves
to exactly the behaviour it has today, and no stored JSON is rewritten. One
field means there is nothing for a second field to contradict.

**Every destination type is a `RefModeDestination`** — messenger, whatsapp,
multi, web and app. What a ref carries is a property of the ref, not of the
channel carrying it, so `ad_ref_token` and
`thins_its_ref_without_reading_the_mapping` ask `resolved_ref_mode` of any
destination, with no type check.

The models tolerate unknown keys, which is pydantic's default and is relied on
here: confs are stored as raw JSON and read back through the model, so
forbidding extras would stop every conf written before any future field removal
from loading, and halt that study's reconciliation.

### Serialising the ref

`dotted_ref(creative_name, metadata, destination, token)` produces the dot-pair
grammar for every carrier that reads under it: Messenger's `url_tags` (which
Meta surfaces as `referral.ref`) and the quick-reply payload inside
`page_welcome_message`, multi's Messenger arm, and the `{ref}` a web or app
destination interpolates into its `url_template` / `deeplink_template`.
`whatsapp_ref` is its counterpart for the WhatsApp autofill, which fly parses
under a different, `form.`-anchored grammar.

Messenger ships its ref on both carriers because a respondent can arrive by
either, and emitting different refs on the two paths would mean one ad
describing two different people depending on how they tapped it.

```python
if destination.resolved_ref_mode == "encoded":
    tok = _require_token(token, destination)
    shortcode = destination_shortcode(destination)
    return encoded_ref(shortcode, tok) if shortcode else tok

return make_ref(creative_name, metadata)
```

A destination with a shortcode routes through fly, whose decoder recovers the
shortcode and the token from one string, so its encoded ref is `r.<payload>` —
and `encode_recruitment_ref` requires a shortcode of 1..255 bytes. A web or app
destination has no shortcode: its `url_template` / `deeplink_template` already
points at a specific survey, nothing decodes its ref, and swoosh compares the
extracted value against `ad_attributions.ref_token` verbatim. So its encoded ref
is the bare token.

`ad_ref_token` mints at the grain of (study, stratum, creative, destination),
which is the grain of an ad and therefore of a mapping row.
`assert_ref_tokens_unique` refuses to publish a campaign whose ads share a
token: a collision is a wrong answer rather than a missing one, and nothing
downstream can detect it.

### The trap

`creative_metadata` returns the complete metadata dict regardless of ref mode;
`dotted_ref` is the ONLY place the mode is allowed to matter. For an encoded
study, the frozen `ad_attributions` blob is the only attribution it will ever
have. If the mode leaked into `creative_metadata`, that study would freeze rows
containing nothing but `form` — every `mapping: "ad_table_lookup"` conf would
resolve to nothing, every stratum would count zero, and the optimizer would
reallocate on empty data. Silent, total, and unrecoverable, because the blob is
frozen at creation and never refreshed.

Two tests pin this: identical frozen blobs from an encoded and a metadata
destination over identical strata, and identical `ad_provenance` output one
layer up but for `ref_token`, which is the point of the mode.

### Flipping a live study

Changing the mode changes the *creative*, and `update_ad` compares creatives via
`field_contract.COMPARED_AD`, so a flip rewrites that study's ads on the next
reconciliation run. That is intended — a deliberate per-study act — and it
cannot cascade, since each study reconciles from its own conf.

Importantly, the flip is an in-place ad **update against the same ad id**, not a
delete-and-recreate: reconciliation matches ads by name, and the creative name
does not change. That matters because `(network, ad_id)` is the table's primary
key — a flip that minted new ids would strand every existing `ad_attributions`
row and leave that study's past respondents unattributable. Both are asserted in
tests.

### The half-migration guard

The one place the write side and the read side meet. Thinning the ref only works
if the study also *reads* the mapping. Do one without the other and the study
has no attribution at all — the ref no longer carries the stratum and nothing
looks the token up, so every stratum counts zero and the optimizer reallocates
on empty data.

`thins_its_ref_without_reading_the_mapping` (`study_conf.py`) detects that
shape: a destination whose resolved `ref_mode` is not `"metadata"` while no
extraction conf declares `mapping: "ad_table_lookup"`.
`warn_on_thinned_ref_without_mapping` (`malaria.py`) logs it on every
reconciliation run. It warns rather than raises, because a study recruiting
uniformly with no `question_targeting` needs no stratum attribution and is
entitled to a thin ref.

Every destination type is asked, with no type check, for the same reason
`ad_ref_token` is: a web destination that stops carrying the stratum has exactly
the problem a Messenger one does.

### Validating the mapping conf

`ExtractionConf` (`study_conf.py`) carries the `mapping` field the dashboard
writes and swoosh reads, and validates one thing at parse time: that the mapping
is a known value.

It does **not** constrain the location. Location says where to read and mapping
says what the value means, and a lookup reads its token from either: a
respondent recruited by a fly destination brings it back in event metadata, one
recruited by a web or app destination lands on the researcher's own page and
brings it back as a Typeform or Qualtrics field. Two lookup confs under one
source need not agree about where their token is, either — swoosh asks each
through its own reader.

### Tests

The "The ref mode" section of `adopt/adopt/test_marketing.py`, and the thinning
section of `adopt/adopt/test_study_conf.py`.

## Ref encoding

The ref is a dot-separated grammar (`creative.<name>.<key>.<value>...`),
and every token in it has to survive being split on `.` and then
URL-decoded. Python's `quote()` does not make that safe by itself:
urllib's `_ALWAYS_SAFE` keeps `.`, `-`, `_` and `~` untouched even when
you pass `safe=''` — measured, `quote('a.b') == 'a.b'`. Two of those
four break a ref. `.` *is* the separator, so a dotted token silently
mis-pairs everything after it. `~` is outside fly's WhatsApp token
alphabet, so it fails the entry gate outright. `-` and `_` are both
separator-safe and inside the alphabet, so `ref_value` (`study_conf.py`)
deliberately leaves them alone rather than churning refs for no gain.

### The severity asymmetry

This is the most important point. A dotted *value* shifts the pairs
after it, so the respondent is **mis-attributed**. A dotted *creative
name* sits at the front of the ref and shifts everything after it,
including `form`, so the respondent is **misrouted into a different
survey**. And the creative name was the least protected of the three
contributors — interpolated completely raw into `make_ref`, with no
`quote()` at all. Study `unicef-immunization-kyrg` ran with creative
names ending `.png` live for roughly nine hours in January 2023; timing
caught it, nothing else would have. All three segments — creative name,
keys, and values — now go through `ref_value` (`make_ref`,
`marketing.py`).

### Containment

Purely prophylactic. A production measurement across every conf
revision — every ref contributor, 3,958 metadata pairs and 618 creative
names — found zero affected studies, and downstream scans over 17.8M
response rows show no corruption signature. Nothing was remediated.
Only values containing `.` or `~` serialise differently, so only an
already-broken study could see its ads rewritten; tests assert the
recorded production values produce byte-identical refs before and
after.

Two things deliberately do **not** change:

- The Facebook **ad name**. `create_ad` still uses the raw creative
  name, and reconciliation matches ads by name — encoding it would
  orphan every live ad and mint new ids.
- The **frozen blob**. `ref_metadata` holds raw values, never encoded
  ones. Encoding is a transport concern; the blob is truth.

### The widened WhatsApp gate

fly widened its entry pattern to accept percent-encoded octets (fly@
`feature/ad-id-attribution` `37e1e06e`). Deliverability is now judged
on the *encoded* form, taking the recorded production values from
**5 of 9 to 9 of 9** — `Static English - Girls`, `Bauchi State`,
`Like Parents` and `South East` all now travel. The only residual is
`/`, which `quote()` keeps literal by default; it corrupts nothing and
is refused at config time.

### The shortcode keeps the narrow alphabet

Deliberately, even though the gate would now accept it encoded
(`WHATSAPP_SHORTCODE_TOKEN` / `whatsapp_shortcode_safe`,
`study_conf.py`). A metadata value is only ever carried by an ad, but a
shortcode is shareable by design — someone texts `form.<shortcode>`
into WhatsApp by hand, and a hand-typed space is a literal space, not
`%20`. A shortcode must be typeable, not merely encodable.

### Deploy ordering

Messenger is safe either way — its parsing is generic, and
`decodeURIComponent` already handles `%2E` on production fly today.
Only the WhatsApp gate needs fly's widened pattern deployed first.
There is deliberately no gating for this in code.

### Tests

The "Ref encoding (D2), and the widened WhatsApp gate (D1)" section of
`adopt/adopt/test_marketing.py`, and the WhatsApp deliverability tests
in `adopt/adopt/test_study_conf.py`.

## Click-to-WhatsApp destinations

Before this, vlab could not create click-to-WhatsApp ads at all: `create_creative`
branched only on `FlyMessengerDestination`, `AppDestination` and `WebDestination`,
and nothing set an autofill message. `FlyWhatsAppDestination` (`study_conf.py`)
adds the fourth branch. It is shaped after `FlyMessengerDestination`, minus
`button_text` — WhatsApp has no quick-reply button, so the respondent gets a
prefilled compose box instead — and plus the number the ad's clicks land on.

### Why the ref is a different string, not a reused one

A click-to-WhatsApp referral carries no advertiser-settable `ref` — `url_tags`
was measured not to reach WhatsApp at all — so fly recovers the shortcode from
the ad's autofill text, which the respondent's first message prefills. fly
matches that text against an anchored, full-match pattern, `WHATSAPP_ENTRY_REF`
in fly's `replybot/lib/event-normalizer.js`:

```
/^(?:start\s+)?form\.((?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+(?:\.(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+)*)$/i
```

Two consequences, both verified against that regex. First, the token must lead
with `form.`; `make_ref`'s output can never match, whatever the values are,
because it leads with `creative.` — structural, not fixable by cleaning up
values, which is why WhatsApp needs its own form-first serialisation,
`whatsapp_autofill`, rather than reusing `make_ref`. Second, every token is
`[A-Za-z0-9_-]` or a percent-encoded octet, so a raw space still fails — but a
properly encoded one no longer does: fly widened the gate to accept `%XX`
(see "Ref encoding" above), so `quote()`-ing a value now saves it rather than
just trading one rejected character for another.

### Why the failure is dangerous

Meta delivers the text intact — dots and spaces both survive
`autofill_message.content`, measured against live ads — so nothing rejects it
upstream. fly's pattern rejects it, no `conversation_started` is derived, and
the arrival falls through to `FALLBACK_FORM` — a real survey, so those
respondents look like completions rather than errors.

### What the autofill carries

`ref_mode` (see "What a ref carries" above) decides it, as on every other
destination type. In `"metadata"` the autofill text carries the full stratum
vocabulary; in `"encoded"` it carries the opaque token instead.

Of the production stratum values on record, encoding (see "Ref encoding" above)
now delivers all of them — 9 of 9, up from 5 of 9 before fly widened its gate —
but one unsafe value still poisons the whole ref, so the config-time check
remains a hard gate rather than a formality.

Worth knowing when choosing the mode: the optimizer never needs the stratum
inline, since the ad-table join carries stratum identity regardless, and the
autofill text is respondent-visible and respondent-editable — being described
back to yourself as `gender.men.age.25_34` before a survey starts is an ethical
question, not a technical one. The reason to carry it anyway is fly survey logic
that branches on ad metadata.

### Validation is at config time, in two places

The ref's content and its deliverability live in different confs, so the check
is split accordingly. `FlyWhatsAppDestination.shortcode_must_survive_the_entry_pattern`
validates the shortcode on the destination model itself, and applies in both
modes — the autofill's head is `form.<shortcode>` either way, so an unsafe
shortcode breaks the plain case too. `StudyConf.check_whatsapp_refs_are_deliverable`
validates the metadata, and fires only for a WhatsApp or multi destination
resolving to `"metadata"` — the one mode that puts stratum values in the
autofill text.
`StudyConf` is the earliest point this check is possible, because destinations
and strata are separate confs, POSTed independently — it's the first place
they meet. It fails closed: a study with an undeliverable ref creates no ads
at all, rather than ads that recruit into the fallback survey.

### Creative shape

`create_creative`'s `FlyWhatsAppDestination` branch sets
`whatsapp_call_to_action` (`WHATSAPP_MESSAGE` / `app_destination: WHATSAPP`),
`link` to `WHATSAPP_LINK` (`https://api.whatsapp.com/send`, required to match
the CTA), and a welcome screen built by `make_whatsapp_welcome_message`
(`VISUAL_EDITOR` / `autofill_message` JSON, produced by `whatsapp_autofill`).
All of it measured against live Meta ads by `adopt/scripts/ctwa_probe.py`.
Deliberately absent: `url_tags`. It never reaches WhatsApp, so setting it would
read like a working carrier when it is not one.

### Consistency with ad-ID attribution

`creative_metadata` folds `form` in for `FlyMessengerDestination` and
`FlyWhatsAppDestination` identically — `isinstance(destination,
(FlyMessengerDestination, FlyWhatsAppDestination))` — so the frozen
`ad_attributions` blob is the same shape whichever channel a respondent
arrives through.

### The ad set half

A `WHATSAPP` `destination_type` ad set on its own is not enough. Meta rejects
it outright unless the ad set also carries a `promoted_object` naming the
Page it recruits through, and optionally the number — without that,
`FlyWhatsAppDestination` was a conf class that could describe a destination
but never produce a working ad.

`whatsapp_phone_number` on the destination is **required**, even though Meta
itself treats the field as optional. Omitting it does not fail the ad; it
falls back to the Page's "primary" number, and many-numbers-to-one-Page is
documented and supported by Meta, so an org running several numbers off one
Page would silently recruit into whichever one happens to be primary. Naming
it is the only way to know which number an ad actually lands on.
`normalize_whatsapp_phone_number` strips it to digits — Meta's
promoted-object reference types the field as a numeric string, while
credentials store the display form (`+1-541-920-2635`) — and
`phone_number_must_be_dialable` validates the result at config time against
E.164's 7–15 digit bounds. That range check also catches a specific paste
error: sending a `phone_number_id` instead of the number itself, a mistake
`ctwa_probe.py` calls out by name because it is an easy way to spend a day
testing the wrong number.

The Page id is not a separate field on the destination at all.
`promoted_object_for` (`marketing.py`) reads it off the creative template via
`template_page_id`, the exact same `object_story_spec.page_id` that
`_create_creative` uses to build the creative itself — so the ad set and its
creative can never end up naming different Pages.

`destination_type` is **checked, not overridden**. A WhatsApp destination
paired with a `MESSENGER` ad set produces a perfectly valid creative and a
perfectly valid promoted object, and an ad that never reaches WhatsApp — all
three conditions look healthy in isolation.
`StudyConf.check_whatsapp_destination_type` raises when they disagree rather
than silently deriving the right value, because `destination_type` is user-set on
every existing study, and deriving it here would change what those studies
send.

**Why this cannot rewrite live ad sets.** This is the part that matters most.
`promoted_object` is deliberately absent from
`field_contract.COMPARED_ADSET`, so `update_adset` neither compares it nor
includes it in an update's params — it rides only on ad set *creates*, which
is exactly where Meta needs it and nowhere else.
`facebook/test_reconciliation.py` pins this directly: a live ad set with no
`promoted_object` is not rewritten the moment vlab starts sending one, and a
study nothing has changed in still produces zero instructions end to end.

**A latent bug fixed rather than inherited.** `promoted_object` lives on the
ad set, but destinations are named per creative, so every creative in a
stratum has to agree on what the ad set should send. The app-destination
branch used to read `destinations[0]` under a standing `# TODO: assert all
destinations are the same` — so a stratum mixing an app creative with any
other kind took whatever its first creative wanted and silently published the
rest of its ads under the wrong one. `adset_promoted_object` (`marketing.py`)
replaces
that guess with a real check: it raises only on genuine disagreement, and
still returns `None` for strata whose creatives all need no promoted
object — every Messenger and Web study there is — mixed or not.
`facebook/probe.py` used to carry a second copy of the same `destinations[0]`
branch; it now calls the shared `adset_promoted_object`, so the probe cannot
report an ad set different from the one production actually sends.

### The dashboard form

Built: `dashboard/src/pages/StudyConfPage/forms/destinations/WhatsApp.tsx`,
including the phone-number field. The two repos share no schema — the form
builds a plain object and adopt parses it — so the "dashboard contract" tests in
`test_study_conf.py` assert that the exact shape `Destination.tsx`'s
`emptyStates` produces parses into this class, and that the `type` literal still
matches what the union discriminates on.

`ref_mode` is exposed on this form as on every other destination type, through
the shared `RefModeField` — see `dashboard/README.md`. Choosing the inline mode
here can make a study's refs unparseable by fly, which
`check_whatsapp_refs_are_deliverable` catches at config time rather than in the
UI, failing closed.

### Tests

The click-to-WhatsApp sections of `adopt/adopt/test_marketing.py` — which
assert against a verbatim copy of fly's regex — and
`adopt/adopt/test_study_conf.py`.

## Configuration

Some documentation for configuring a vlab study:

## Development

### Setup local environment

This project requires the use of [Python Poetry](https://python-poetry.org/),
please see the [installation
guide](https://python-poetry.org/docs/#installation)

To install dependencies 
```bash
poetry install
```

### To Run Tests

The tests currently depend on a database running, to start the database

```bash
make test-db
```

Then to run the tests
```bash
make test
```

## JSON Schemas for study configuration

`adopt/schemas/*.json` is the machine-readable contract for a study
configuration: JSON Schema (2020-12) generated from the pydantic models in
`adopt/adopt/study_conf.py` and `adopt/adopt/study_conf_strict.py` by
`adopt/adopt/schema_export.py`.

**They describe the WRITE shape.** Since 2026-09-05 the models are asymmetric:
`POST /confs/<type>` validates through the `extra="forbid"` twins in
`study_conf_strict.py`, while the load path keeps the lenient originals so a
conf written before a field was removed still loads. The per-section files
describe the strict side, because a consumer reading them is about to POST a
body and needs to know what will be accepted — a lenient schema would tell them
their misspelled key is fine when the server is about to 422. `study-conf.json`
is the exception and says so in its `$comment`: it is the load shape, and it
permits additional properties where the others do not.

```bash
make schemas        # regenerate
make check-schemas  # fail if the committed files have drifted
```

Files are keyed by the **wire** conf type — the last path segment of `POST
/{org_id}/studies/{slug}/confs/<type>` — so `data-sources.json` and
`inference-data.json` carry hyphens even though the database stores those confs
under `data_sources` and `inference_data`. `index.json` is the manifest: conf
type, URL, whether the body is an object or an array, and which file describes
it. `study-conf.json` is the assembled whole-study shape, which no endpoint
accepts (adopt builds it on the optimize path) but which a consumer can
validate against to find out whether its sections add up.

### Why it is committed rather than served

The point is the diff. Adding a required field to `StratumConf` changes
`strata.json` in the same pull request, next to the model change, where a
reviewer can ask whether every conf already in the database still validates. An
endpoint that generated the schema on demand would give a consumer the same
JSON and give review nothing. `check-schemas` runs as its own CI job (no
database needed) and `adopt/adopt/test_schema_export.py` runs the same check
locally, so the artifact cannot quietly fall behind the models.

`schema_export.py`'s `CONF_ENDPOINTS` restates the route table from
`server.py`. That duplication is checked, not trusted:
`test_covers_every_conf_endpoint` parses `server.py` with `ast` and fails if the
two disagree. It parses rather than imports because importing the server
evaluates `PG_URL` and the auth secrets at module scope.

### What the schemas do not say

JSON Schema is a structural language and these models are not purely
structural. Four things are enforced by the server but invisible in the
generated files:

- **`StudyConf`'s cross-section validators.** `check_whatsapp_refs_are_deliverable`
  rejects stratum metadata that fly's entry regex could not parse once
  percent-encoded. It cannot be expressed in JSON Schema, and it does not run at
  write time anyway (see `planning/agent-study-authoring.md` §2.5).
- **The missing-`type` destination default.** Both destination unions run a
  `BeforeValidator` that reads an absent or empty `type` as `"messenger"`, for
  the 45 stored confs that predate the field — on write as well as on load, so
  those confs stay re-saveable. `destinations.json` marks `type` required
  anyway, which makes it stricter than the server on exactly this key, and
  deliberately: an agent authoring a new conf should write the tag. The
  leniency is a concession to the legacy corpus, not an API. It is safe because
  the strict models forbid unknown fields — a typeless body is defaulted to
  messenger and then rejected on its own type-specific fields unless it really
  is a messenger destination.
- **Retired keys are accepted on write and dropped.** A closed list of two —
  `recruitment.destination_type` and `destinations[].include_metadata_in_ref`,
  both fields this repo once declared and removed — is stripped before
  validation, so a stored conf carrying one can still be re-saved. The schemas
  say `additionalProperties: false` and so reject them, which makes the files
  stricter than the server on exactly those two names. That is the right way
  round: nothing should be *writing* them.
- **The recruitment tag reads as required and is not.** `recruitment.json`
  exports a real `discriminator` on `type`, as `destinations.json` does — but
  unlike the destination arms, the three recruitment arms carry a *default* for
  `type`, so pydantic emits it as optional and it appears in no arm's
  `required`. What the file cannot express is the `BeforeValidator` that infers
  the arm from shape (`ad_campaign_name` → simple, then `arms` → pipeline, then
  `destinations` → destination experiment, and an error naming all four if none
  is present), which is what keeps confs stored before the union was tagged
  loading and saving.

  In practice a plain validator is *more* permissive here than the
  discriminator suggests. Verified with python-jsonschema (Draft 2020-12)
  against the committed file: a complete but untagged `simple` conf is
  **accepted**, because `type` is not required anywhere and a `const` binds
  only when the key is present, so exactly one `oneOf` arm matches. Untagged
  pipeline and destination confs likewise. Only discriminator-aware tooling
  that insists on the tag, or a body carrying a retired key, is rejected.
  New configuration should write the tag regardless — it is the only thing that
  makes the arm unambiguous rather than merely inferable.



## Whole-study validation

`adopt.authoring.validate.validate_study(sections)` takes the nine stored conf
sections and returns a `ValidationReport` — `valid`, `errors`, `warnings`, each
finding carrying a machine-readable `code`, the `section`, a `path` like
`strata[0].creatives[1]`, and a message. `POST /{org}/studies/{slug}/validate`
is a thin wrapper on it. Full taxonomy and wire shape:
`documentation/agent-api.md` §2.6; the design record is
`planning/agent-study-authoring.md` §14.

Three things about it are structural rather than incidental.

**It shares its assembly with the run path.** `study_conf_from_sections` was
factored out of `malaria.get_study_conf`, which calls it. There is exactly one
definition of "these nine sections are a `StudyConf`", so a validator cannot
drift from what the cron actually builds, and every cross-section validator
added to `StudyConf` later is reported with no change to `validate.py`.

**It is pure.** No database, no Meta. That is what lets an SDK run it on
sections that have never been written, and it is why neither `credentials_key`
edge is checked and nothing Meta-side is. The gaps are enumerated as
`validate.KNOWN_GAPS` and echoed on every HTTP response rather than left to
prose.

**Errors and warnings are drawn on one line.** An *error* is a reference that
provably cannot resolve from the study's own configuration, **and that the run
path actually resolves**. A *warning* is anything else worth saying. Two
consequences that are easy to get wrong, and were, in the first draft:

- `strata[].creatives[]` → `creatives[].name` is an error, because
  `hydrate_strata` resolves every creative a stratum names. But
  `creatives[].destination` → `destinations[].name` is an error *only for a
  creative some stratum names*: `get_destination_for_creative` has exactly one
  caller, `creative_destination_pairs`, and it iterates `stratum.creatives`.
  An unreferenced creative's dead destination is
  `creative.unreferenced_destination_unknown`, a warning — harmless today,
  fatal the moment a stratum adds it. (A blanket `creative.unreferenced` was
  rejected: unreferenced creatives are ordinary editing debris and warning on
  all of them would bury the report.)
- **Every audience finding is a warning, without exception.**
  `strata[].audiences` resolves against custom audiences on the Meta *ad
  account* (`FacebookState.get_audience`), not against the `audiences` conf, so
  offline validation cannot tell a typo from an audience built by hand in Ads
  Manager. That includes `audience.partitioned_bare_name` — a stratum naming a
  `PARTITIONED` conf by a name vlab never creates — which was an error until
  review pointed out that the rule admits no exception just because the mistake
  is obvious.

Warnings never make a study invalid.

**Absent is not the same as unparseable.** For the two optional sections both
leave the value `None`, and treating them alike would report every targeted
variable as unsupplied whenever `inference_data` merely failed to parse — noise
on top of the `section.invalid` error that already says so. `_parse_sections`
returns a `failed` set for exactly this, and the checks that read a failed
section are skipped.

The two invariants that were `logging.warning` calls in a cron —
`warn_on_incomplete_targeting` and `warn_on_thinned_ref_without_mapping` — are
warnings here, deliberately keeping the status their own docstrings argue for.

### Known defect: partitioned and lookalike audiences are unwritable as JSON

Found while writing the fixtures for this and **not fixed**. `AudienceConf`'s
`model_validator(mode="before")` calls `validate(values, values["subtype"], …)`,
which does `isinstance(values.get("partitioning"), Partitioning)` — an
isinstance check against the *parsed* model class, run before pydantic has
parsed anything. From a dict it can never pass, so `PARTITIONED` and
`LOOKALIKE` audiences are constructible only from Python objects and
`POST /confs/audiences` with one is a 422. Every existing test builds them from
objects (`test_audiences.py:217`, `test_marketing.py:306`), which is why nobody
had hit it. A missing `subtype` likewise raises a bare `KeyError`, which
pydantic does not wrap.

`validate_study` reports such a section as `section.invalid`, which is the true
answer: `StudyConf` assembly in the cron fails on the same stored conf for the
same reason. Before designing a fix, check whether any production study has a
partitioned audience stored — if one does, it is already failing every
reconciliation run.

## The `vlab` SDK and CLI

Phase 3 of `planning/agent-study-authoring.md` §8. What shipped, what was
decided and what is still open: `planning/vlab-sdk.md`. The API it wraps:
`documentation/agent-api.md`.

```
export VLAB_API_KEY=eyJ...           # a human mints this; see below
export VLAB_API_URL=https://vlab-study-conf-api.toixo.vlab.digital   # the default

vlab create $ORG "HPV Nigeria" --init study.yaml
$EDITOR study.yaml
vlab validate && vlab diff && vlab push
vlab plan  $ORG/hpv-nigeria
vlab apply $ORG/hpv-nigeria 0 --yes
```

### Install

**`adopt` is not published to any index.** There is no `pip install adopt` and
there never has been — the name on PyPI belongs to an unrelated project, so
installing it would get you somebody else's package. Install from the
repository:

```
pipx install "adopt[sdk] @ git+https://github.com/vlab-research/vlab.git#subdirectory=adopt"
```

or, inside a checkout:

```
cd adopt && poetry install --extras sdk && poetry run vlab --help
```

**Python `>=3.9,<3.11`** — `adopt`'s own constraint, which the SDK inherits, so
`pipx install --python python3.10 ...` if your default is newer. `pipx` will
pull pandas, scipy and cvxpy along with it: accepted deliberately in plan §7,
on the grounds that extracting a package is real work and nobody has yet been
hurt by the download.

Verified on 2026-09-05 with pip 26.2.1 and CPython 3.10.13, from a clean venv:

```
$ python3.10 -m venv v && ./v/bin/pip install '/path/to/vlab/adopt[sdk]'
Successfully installed adopt-0.1.85 click-8.5.0 pandas-1.5.3 … (78 packages)
$ ./v/bin/vlab --help                     # works
$ ./v/bin/vlab validate study.yaml
valid (study.yaml): 1 warning(s), no errors.   # exit 0
```

and the VCS form, against a local clone so no credentials are involved:

```
$ ./v/bin/pip install "adopt[sdk] @ git+file:///path/to/vlab@feature/vlab-sdk#subdirectory=adopt"
Successfully installed adopt-0.1.85 …
```

**Use the `name[extras] @ url` spelling.** The older
`git+https://…#subdirectory=adopt&egg=adopt[sdk]` fragment is not merely
deprecated — pip 26 refuses it outright, with
`× The 'adopt[sdk]' egg fragment is invalid` and a hint pointing at the
spelling above.

`click` is `optional = true` in `pyproject.toml`, which is what keeps the server
image (`poetry install --only main --no-root`) unchanged by this. It still lands
there, as a transitive dependency of uvicorn and typer.

### The file

One `study.yaml` (JSON also parses): a three-key header and the nine
configuration sections, keyed as STORED — `data_sources` and `inference_data`
with underscores, not the hyphenated URL segments you POST to.

```yaml
org:  0f1e...            # a UUID a human has to hand you; no endpoint lists orgs
slug: hpv-nigeria        # from the 201 of `vlab create`
name: HPV Nigeria

general:      {...}
recruitment:  {...}
destinations: [...]
...
```

Section values are the wire shapes **verbatim** — exactly what
`POST /confs/<type>` takes and exactly what `GET /confs` returns. There is no
translation layer, deliberately: the moment the file has a schema of its own,
the SDK owns a second definition of what a study is, which is the failure that
made the dashboard's TypeScript compiler a problem in the first place. So
`documentation/agent-api.md` §3 is the file format's documentation, and stays
correct for free.

### Commands

| | |
|---|---|
| `vlab create <org> <name> [--init]` | `POST /{org}/studies`. Prints the slug — which you cannot compute yourself; apostrophes are *deleted*, so `Nandan's study` is `nandans-study`. `--init` writes an annotated skeleton that passes `vlab validate` as written. |
| `vlab pull <org>/<slug> [-o]` | `GET /confs` to a file. Refuses to clobber without `--force`. |
| `vlab validate [file] [--remote]` | Local and instant by default; exits 1 when invalid. `--remote` asks `POST /validate` instead — the same pure function behind an HTTP call, for when this package is older than the deployment. |
| `vlab diff [file]` | Per-section, down to the changed leaf. |
| `vlab push [file] [--section] [--force] [--dry-run]` | Validates first, then writes only what differs, in reference order. |
| `vlab plan <org>/<slug>` | `GET /{org}/optimize/{slug}`, indexed. **Not side-effect free.** |
| `vlab apply <org>/<slug> <index> [--yes]` | Re-plans, then posts that one instruction. |
| `vlab meta credentials\|adaccounts\|campaigns\|adsets\|ads` | The read-only Meta proxy. `--json` output feeds the next command. |
| `vlab strata generate [file] [--finish-question]` | The dashboard's Regenerate, in Python. |
| `vlab strata extract-targeting <adsets.json> <prop>…` | `extract_from_adset` over a `vlab meta adsets --json` response. |
| `vlab keys list\|revoke` | There is deliberately no `keys create`: minting needs a token you already have, and the first one needs an Auth0 login. |

### Four decisions worth knowing

**`diff` compares what would be STORED, not what would be sent.** The server
keeps `model_dump()` of your body, so unknown keys are gone and defaults are
filled in. Without reproducing that, every section whose file omits an optional
field would read as changed forever — and since `study_confs` is append-only,
`push` would append a row on every run with no way to remove any of them.

**A `type` tag that merely restates a body's own shape is not a difference.**
PR #262 tags the recruitment union and `model_dump()` then writes a `type` on
every recruitment conf; a server older than it drops the tag on the way in. A
file that writes the tag — which it should, since new configuration ought to be
explicit — would otherwise diff against both of them permanently. The same rule
covers a `messenger` destination, whose `type` an older stored conf may not
carry. A tag that *contradicts* the shape is reported, as an undeclared key.

**Push order is fixed, and `recruitment` is last.** general → destinations →
creatives → audiences → variables → strata → data_sources → inference_data →
recruitment. The server checks nothing across sections, so the order buys the
server nothing: it means a push that stops half way leaves a *prefix* of the
reference graph on the server rather than a middle of it. `recruitment` is last
because its `start_date`/`end_date` window is what makes the study visible to
the crons, so writing it last means the two-hourly `adopt-ads` run cannot pick
up a half-configured study.

**Unknown keys are reported by `diff` and `push`, not by `validate`.**
`vlab validate` is a wrapper over `authoring.validate.validate_study` and must
give the same answer as `POST /validate`, which uses the lenient models and does
not report them. An undeclared key is a fact about the *wire*, so it belongs in
the commands about the wire. It matters because every conf model runs on
pydantic's default `extra="ignore"`: a misspelled optional field is accepted with
a `201` and silently discarded. PR #262 makes it a 422 naming the key; reporting
it locally works against both servers, and before the write rather than after.

### Using it as a library

The CLI is one caller of the SDK, not the only way in. A notebook that builds
strata from a census spreadsheet and radius targeting — which the dashboard's
Variables form cannot express at all — uses the same pieces:

```python
from adopt.authoring.sheets import read_share_lookup, parse_kv_sheet
from adopt.authoring.geo import location_levels
from adopt.authoring.strata import create_strata_from_variables
from adopt.sdk import StudyFile, VlabClient, diff_sections

share = read_share_lookup("targeting.xlsx", ["location"], "targeting_distribution")
levels = [
    location_levels(state, rows, quota=float(share.set_index("location").loc[state]))
    for state, rows in towns.groupby("state")
]

study = StudyFile.load("study.yaml")
study.sections["variables"] = [{"name": "location", "properties": ["geo_locations"],
                               "levels": levels}]
study.sections["strata"] = create_strata_from_variables(
    study.sections["variables"], "finished",
    study.sections["creatives"], study.sections["audiences"],
    study.sections["strata"],
)
study.save()
```

`adopt.authoring.strata` is *a* helper, not the blessed pipeline. Hand-written
strata are legitimate — the server stores whatever you send — and
`validate_study` checks the result either way. That is the whole point of
rejecting a server-side "compile study" endpoint (plan §6.D): the SDK should be
able to do more than the dashboard, not the same thing over HTTP.

### Salvaged from the notebook era

`adopt/configuration.py` has been marked superseded since Phase 1. Phase 3 moved
the pieces the notebooks in `~/Documents/vlab-research/campaigns/` actually used:

| New home | |
|---|---|
| `adopt.authoring.sheets` | `parse_kv_sheet` (68 call sites, 17 notebooks), `parse_row_sheet` (17), `read_share_lookup` (17) |
| `adopt.authoring.geo` | `location_levels` (24 calls, 20 notebooks), `create_location` — now public, because 15 call sites across 14 notebooks were each a byte-identical private copy of it |

Two things changed in the move, both taken from what notebook authors kept
rewriting by hand. `location_levels` emits `facebook_targeting` rather than
`params`, so its output drops straight into a `variables` conf and through
`create_strata_from_variables`; the old key was readable only by the old
`configuration.format_group_product`. And its `rows` argument takes anything
row-shaped — a DataFrame, Series, dicts — not specifically `list(df.iterrows())`.

What was dropped, and why, is listed in `configuration.py`'s own marker. The
module is not deleted: the notebooks still import it.

`read_share_lookup`'s multi-level branch is inherited pandas that its original
author's comment called "crazy pandas magic. Probably worth redoing from
scratch", and four of its seventeen notebook callers shadowed it with their own
rewrite. It is moved unchanged, with the five tests that pin its output, and
marked rather than quietly shipped as general.

## `vlab template` — building the templates a study is configured from

The design record is `planning/template-authoring.md`; the reference, including
every Meta quirk and the full runbook, is `documentation/agent-api.md` §6a.

Before a study can be configured, something has to exist on the ad account for
it to be configured *from*: a **template campaign** whose ad sets carry the
targeting a `variables` conf extracts, and whose ads carry the creative blob a
`creatives` conf stores. Until 2026-09-05 the only way to build one was by hand
in Ads Manager — which an agent cannot do, and which is where the creative half
in particular got stuck.

```
export FACEBOOK_ACCESS_TOKEN=EAAB...          # NOT VLAB_API_KEY; see below

vlab template check-targeting --account act_… --spec spec.yaml   # read-only
vlab template plan   spec.yaml                # pure: no network, no token
vlab template create spec.yaml --create --json
vlab template creative --account act_… --campaign 120… --adset 120… \
    --name my-creative --kind whatsapp --page-id 1855… \
    --message "…" --image ./ad.png --create
vlab template delete 120…
```

`create --json` returns `ads[].template`: the creative **as Meta returns it**,
which is exactly what a `creatives` conf wants. Not what was sent — Meta fills
in `actor_id` (which `audiences.py` reads with a bare `KeyError` if it is
missing), rewrites `object_story_spec`, and drops what it did not accept.

The library underneath is `adopt.authoring.templates`, and it is usable without
the CLI: `plan_template_campaign(...)` is pure and returns the exact Graph
calls as data, `apply(plan, api)` executes them, `build_creative(...)` is the
piece worth importing on its own.

**Safety, and the shape of it.** Everything is created `PAUSED` — `status` is a
module constant, not a parameter, so nothing here can activate anything. A
template campaign's name starts with `Templates - `, which is the marker:
`delete` refuses any campaign without it and `creative` refuses to add an ad to
one. Daily budgets are capped at 10 000 cents (a typo guard — a paused campaign
cannot be charged). Dry run is the default everywhere; a write needs `--create`
or `--yes`, and refusing prints the plan rather than merely complaining.

**Auth is different here, and that is the interesting part.** Every other
`vlab` command talks to the vlab server, and `vlab meta …` reads Meta *through*
it so no Facebook token ever reaches your machine. Creating a creative cannot
work that way — it needs an image upload, which would make the conf service a
bytes relay, and it would hand that service money-spending liability it does
not have today. `planning/agent-study-authoring.md` §10 records the decision.
So this group wants `FACEBOOK_ACCESS_TOKEN`, for a user with a role on the ad
account and on the Page; nothing is written to disk and there is no login
command. `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` are optional and enable
`appsecret_proof`, which Meta requires only for apps with "Require app secret"
turned on — whether the vlab app has it on is not readable from this repo, so
a token-only run warns and names the error to expect if it does.

**Not yet run against live Meta.** Every shape is either lifted from a script
that was measured live (`adopt/scripts/make_template_campaign.py`,
`adopt/scripts/ctwa_probe.py`) or taken from Meta's documented samples, and
every test mocks `FacebookAdsApi.call`. Treat the first live run as an
experiment, on a throwaway campaign name.
