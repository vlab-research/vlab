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

`FlyMultiDestination` is **gated off** behind `ADOPT_ENABLE_MULTI_DESTINATION`:
its Messenger arm is measured against live Meta delivery, its WhatsApp arm has
never been observed. `documentation/multi-destination-ads.md` §4 is the
procedure that clears the gate and the log that records it.

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

## Ad-ID attribution

vlab creates exactly one ad per `(creative, stratum)` pair, so the ad id
Facebook hands back already determines that ad's shortcode, creative and
stratum metadata. Today that identity is encoded into a dotted `ref` string
(`make_ref`) that rides to the survey platform inside every message. This
phase adds the alternative: an `ad_attributions` table that persists
`(network, ad_id) -> {shortcode, creative, stratum metadata}` at ad-creation
time, so it can be joined against later instead of parsed out of the ref.

This phase builds the capture and the table only. Nothing consumes the table
yet, and no existing study's behaviour changes — `make_ref` and the ref
emission in `create_creative` are deliberately untouched, because changing a
creative triggers ad rewrites across every live study on the next
reconciliation run.

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
in `csv_export.py`. The shape is `ad_id, network, <metadata keys...>,
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
`ad_id`, `network` — or `TRAILING_COLUMNS` — `created` — together
`RESERVED_COLUMNS`), because two columns with the same header is the kind of
thing nobody notices until the analysis is already wrong.

Deleted ads are included, deliberately. Respondents keep arriving from ads
reconciliation has since deleted — reshared page posts persist indefinitely —
so a CSV of only live ads would silently lack rows the researcher needs, and
those respondents would look unattributed. Nothing in the read path filters
on liveness, and nothing should.

Tests: `adopt/adopt/server/test_ad_attributions_csv.py`, needs `make
test-db`.

## Shortcode-only refs

Before this, `location: "ad"` already worked, but ads still shipped vlab's
whole stratum vocabulary into fly inside every message: the ad id duplicated
the ref rather than replacing it, so nothing was actually decoupled.
`FlyMessengerDestination.include_metadata_in_ref` (`study_conf.py`) controls
what the ref carries. It is named to match `FlyWhatsAppDestination`'s field
of the same name — one concept, and the two channels differ only in their
default. Messenger defaults **True**, the historical behaviour every existing
study depends on.

### What it emits

Turned off, the ref becomes `form.<initial_shortcode>` on **both** Messenger
carriers: `url_tags` (which Meta surfaces as `referral.ref`) and the
quick-reply payload inside `page_welcome_message`. Both, because a respondent
can arrive by either, and emitting different refs on the two paths would mean
one ad describing two different people depending on how they tapped it.

`form.<shortcode>` is the minimum that still routes: fly's `getMetadata`
parses `referral.ref` as dot-pairs and reads `md.form`, falling back to
`FALLBACK_FORM` — a real survey — when it is absent. Routing is the one job
the ref cannot delegate, since it happens at the first inbound message, while
attribution is a batch join done afterwards.

### The trap

`creative_metadata` returns the complete metadata dict regardless of ref
mode; `messenger_ref` is the ONLY place the mode is allowed to matter. For a
shortcode-only study, the frozen `ad_attributions` blob is the only
attribution it will ever have. If the mode leaked into `creative_metadata`,
that study would freeze rows containing nothing but `form` — every
`location: "ad"` conf would resolve to nothing, every stratum would count
zero, and the optimizer would reallocate on empty data. Silent, total, and
unrecoverable, because the blob is frozen at creation and never refreshed.

Two tests pin this: identical frozen blobs from a shortcode-only and a
full-ref destination over identical strata, and identical `ad_provenance`
output one layer up.

### Flipping a live study

Toggling the flag changes the *creative*, and `update_ad` compares creatives
via `field_contract.COMPARED_AD`, so a flip rewrites that study's ads on the
next reconciliation run. That is intended — a deliberate per-study act — and
it cannot cascade, since each study reconciles from its own conf.

Importantly, the flip is an in-place ad **update against the same ad id**,
not a delete-and-recreate: reconciliation matches ads by name, and the
creative name does not change. That matters because the ad id is the
attribution key — a flip that minted new ids would strand every existing
`ad_attributions` row and leave that study's past respondents
unattributable. Both are asserted in tests.

### The half-migration guard

Thinning the ref only works if the study also *reads* the mapping. Do one
without the other and the study has no attribution at all — the ref no longer
carries the stratum and nothing looks the ad up, so every stratum counts zero
and the optimizer reallocates on empty data.
`thins_its_ref_without_reading_the_mapping` (`study_conf.py`) detects that
shape: a fly destination with `include_metadata_in_ref` off while no extraction
conf declares `location: "ad"`. `warn_on_thinned_ref_without_mapping`
(`malaria.py`) logs it on every reconciliation run. It warns rather than
raises, because a study recruiting uniformly with no `question_targeting` needs
no stratum attribution and is entitled to a thin ref. It covers WhatsApp
destinations too, whose default is already thin.

### Web and App stay on full refs

Deliberately: neither has an `initial_shortcode`, because their
`url_template` / `deeplink_template` already points at a specific survey, so
routing is not a job the ref does for them. Making them shortcode-only would
mean inventing a conf field for a token neither needs; the equivalent
decoupling for a web platform is capturing the ad id from the ad URL, which
is separate work.

### Tests

The "Shortcode-only Messenger refs (A4)" section of
`adopt/adopt/test_marketing.py`.

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
prefilled compose box instead — and plus `include_metadata_in_ref`.

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

### Full-ref mode is opt-in and rare

`include_metadata_in_ref` puts the full stratum metadata in the autofill text,
not just the shortcode. It defaults off. Of the production stratum values on
record, encoding (see "Ref encoding" above) now delivers all of them — 9 of
9, up from 5 of 9 before fly widened its gate — but one unsafe value still
poisons the whole ref, so the config-time check remains a hard gate rather
than a formality. The only reason to turn this on is fly survey logic that
branches on ad metadata; the optimizer never needs it, since the ad-ID join
(see above) carries stratum identity regardless. The autofill text is also
respondent-visible and respondent-editable, which is the other reason the
default is the shortcode alone.

### Validation is at config time, in two places

The ref's content and its deliverability live in different confs, so the check
is split accordingly. `FlyWhatsAppDestination.shortcode_must_survive_the_entry_pattern`
validates the shortcode on the destination model itself, and applies in both
modes — even the default token is `form.<shortcode>`, so an unsafe shortcode
breaks the plain case too. `StudyConf.check_whatsapp_refs_are_deliverable`
validates the metadata, and fires only when `include_metadata_in_ref` is on.
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

### Not yet built

The dashboard form for this destination type, including its phone-number
field.

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


