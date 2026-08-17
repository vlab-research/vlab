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


