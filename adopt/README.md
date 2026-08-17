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
/^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$/i
```

Two consequences, both verified against that regex. First, the token must lead
with `form.`; `make_ref`'s output can never match, whatever the values are,
because it leads with `creative.` — structural, not fixable by cleaning up
values, which is why WhatsApp needs its own form-first serialisation,
`whatsapp_autofill`, rather than reusing `make_ref`. Second, every token is
`[A-Za-z0-9_-]`, so a space fails, and percent-encoding does not save it either
— `%` is not in the class, so `quote()`-ing a value just trades one rejected
character for another.

### Why the failure is dangerous

Meta delivers the text intact — dots and spaces both survive
`autofill_message.content`, measured against live ads — so nothing rejects it
upstream. fly's pattern rejects it, no `conversation_started` is derived, and
the arrival falls through to `FALLBACK_FORM` — a real survey, so those
respondents look like completions rather than errors.

### Full-ref mode is opt-in and rare

`include_metadata_in_ref` puts the full stratum metadata in the autofill text,
not just the shortcode. It defaults off. Of the production stratum values on
record, roughly half are undeliverable — `Static English - Girls`,
`Bauchi State`, `Like Parents` and `South East` all fail; `3B`,
`gelangchoice`, `women` and `Smiling` pass — and one unsafe value poisons the
whole ref. The only reason to turn it on is fly survey logic that branches on
ad metadata; the optimizer never needs it, since the ad-ID join (see above)
carries stratum identity regardless. The autofill text is also
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


