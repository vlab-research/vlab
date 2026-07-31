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

The subtle part is that Facebook does not echo everything back. Some fields it
accepts on write and simply omits from the response. Comparing such a field is
a trap: we send it, Facebook drops it, we see a difference, we rewrite — every
run, forever. `field_contract.DROPPED` is the list of fields known to behave
this way, and those are excluded from comparison.

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

The probe builds the creative a study's config asks for, fetches the live ad,
and classifies every field path:

| verdict | meaning |
|---|---|
| `ok` | sent it, Facebook echoed it back unchanged |
| `dropped` | sent it, Facebook did not return it — declare it or stop sending it |
| `differs` | sent it, Facebook returned something else — a real change |
| `stale` | declared `DROPPED`, but Facebook returns it now — undeclare it |

It exits non-zero when the contract and Facebook disagree, so it can gate a
deploy. `--update` rewrites the `DROPPED` block in place, stamped with today's
date; review it as a normal git diff.

It is read-only by default because it points at ads spending real money.

Background on the incident that motivated this: `planning/field-contract.md`.

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


