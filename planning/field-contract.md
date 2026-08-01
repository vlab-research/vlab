# The Facebook field contract

> Why this exists: on 2026-07-30 we found adopt rewriting the same 30 ads every
> two hours, indefinitely, because of one field Facebook accepts but never
> returns. ~360 no-op ad writes a day against a single ad account, and a
> contributing cause of `code 17 / Ad Account Has Too Many API Calls`.

## What happened

`reconciliation._eq` compares the live ad against the ad the study config
describes, and `update_ad` rewrites the whole ad if they differ.

The OWIS Nigeria study's creative template sets:

```
degrees_of_freedom_spec.creative_features_spec.image_text_translation = {"enroll_status": "OPT_IN"}
```

Facebook accepts that write, then returns ~82 `creative_features_spec` keys of
which `image_text_translation` is not one. Every other key matched exactly.

`_eq`'s nested subset mode said "a key in desired that is missing from source
IS a difference" and returned `False`. So: rewrite the ad, Facebook drops the
key again, next run sees the same difference. Three consecutive cron runs were
confirmed pushing the identical 30 ad updates; there was no reason it would
ever stop.

Two things made it invisible for so long:

- The per-ad log line was `WARNING ... creative mismatch`, which reads like the
  reconciler working correctly rather than looping.
- The writes all succeeded. Nothing errored, no alert fired. The only visible
  symptom was Facebook throttling reads on an unrelated study later in the run.

## It was six fields, not one

The first diagnosis came from diffing a single `_eq: mismatch` log line, which
showed exactly one key missing — `image_text_translation`. Running the probe
against all 60 live ads found five more:

| field | ads sending it that Facebook dropped |
|---|---|
| `image_text_translation` | 30/30 |
| `image_animation` | 3/30 |
| `image_brightness_and_contrast` | 3/30 |
| `image_templates` | 3/30 |
| `image_touchups` | 3/30 |
| `text_optimizations` | 3/30 |

Re-parsing every mismatch line in the captured production log confirmed the
same six. The study has two creative variants with different
`creative_features_spec` templates (15 and 16 keys), and only the larger one
carries the extra five.

Declaring just `image_text_translation` would have fixed 27 ads and left 3
rewriting forever — a quieter version of the same bug, and one that would have
looked fixed on any dashboard counting total writes.

The lesson is in the tooling, not the diagnosis: one log line is a sample, and
a sample cannot tell you the shape of the whole. That is what `adopt-probe`
is for.

## The fix

`adopt/facebook/field_contract.py` declares:

- `COMPARED_AD` / `COMPARED_ADSET` — which fields participate in the comparison
  and, in a sentence each, why. Previously these were bare lists in
  `reconciliation.py` with no rationale, so nobody could tell whether a given
  field was load-bearing.
- `DROPPED` — fields Facebook accepts but does not echo back. Excluded from
  comparison.

## Why undeclared drops are still differences

The obvious fix — never treat a missing key as a difference — is wrong, and
`test_ad_dif_updates_when_object_story_spec_format_changes` proves it. When a
creative is migrated from `photo_data` to `link_data`, the live object is
missing `link_data` in exactly the same shape as a field Facebook drops:
a dict-valued key present in desired, absent from source.

There is no signal in the data separating "Facebook won't store this" from
"this is a real change we must apply". So tolerance is opt-in per field, and an
undeclared drop warns with the path and the command that resolves it:

```
WARNING _eq: undeclared drop at .degrees_of_freedom_spec.creative_features_spec.foo
        — we set this field but Facebook did not return it. ...
        Check with `adopt-probe <study>` and declare it in field_contract.DROPPED.
```

That warning is worth alerting on: a fresh one means either a real migration in
flight or a new rewrite loop starting.

### The top-level exception

This rule applies to *nested* keys. At the top level — a whole declared field
like `url_tags` or `object_story_spec` missing from Facebook's response —
`_eq` skips instead, which is what it has always done. A field Facebook does
not return at all gives us nothing to act on, and making it a difference would
start exactly the rewrite loop this work exists to kill. It still warns when
undeclared.

Pinned by `test_eq_tolerates_a_whole_top_level_field_missing_from_source`, so
the asymmetry is deliberate rather than an accident waiting to be "tidied up".

## Maintaining it

```bash
poetry run adopt-probe <study>            # report
poetry run adopt-probe <study> --update   # rewrite DROPPED, stamped with today
```

Run it when Facebook ships API changes, when a study starts using creative
options it hasn't before, or when the `undeclared drop` warning appears. It
exits non-zero while the contract and Facebook disagree.

The probe reuses the real code path — `pair_creatives_with_destinations` then
`create_creative` — so what it compares is what the cron would actually
publish, not a reimplementation that can drift.

## The adsets were worse

Extending the probe to adsets found a second, independent loop — and a
deterministic one. Feeding the live adset's own budget back in as the desired
budget, so the optimizer's intended change could not mask anything, an adset
*still* compared unequal on every field that matters:

| field | Facebook returns | adopt sends |
|---|---|---|
| `daily_budget` | `'2585'` (str) | `2585` (int) |
| `end_time` | `'2026-08-03T02:00:00+0200'` (str) | `datetime(2026, 8, 3, 0, 0)` (naive) |

Same number. Same instant. Different types, so `==` is False forever. Unlike
the ad case, which needed a particular creative template to trigger, this hits
**every adset on every run unconditionally** — 6 for OWIS plus 2 for Girl
Effect, every two hours, whether or not anything changed.

`field_contract.NORMALIZE` fixes this: a per-path function that canonicalises
both sides before comparison. `daily_budget` through `int`, `end_time` to a UTC
instant. Genuine changes still register — `int('2585') != int(3000)` — which is
what `test_eq_still_detects_a_real_budget_change` guards.

Normalisers are hand-written, not probe-generated. A normaliser encodes what
"the same" *means* for a field, and no amount of sampling live data can infer
that.

## The argument order, now unified

`_eq(a, b)` treats `a` as the authority: every key in `a` must be present and
equal in `b`, and extras in `b` are ignored. Facebook decorates everything it
returns with server-side defaults we never set, so the **desired** object has
to be `a`.

`update_ad` always did that. `update_adset` had it backwards — `_eq(live,
desired)` asks "is everything Facebook returned present in what we want?",
which is a different question and the wrong one. Both now pass desired first.

That also fixes the logging: `_eq` labels its arguments `desired=` and
`source=`, which were simply lying on the adset path.

Flipping it exposed one field: `targeting.custom_audiences`. `add_audience_targeting`
always sets it — to `[]` when the study has no audiences — and Facebook omits
the key rather than echoing an empty list. In the old order this was invisible.

Rather than declare it dropped, `_eq` now takes **empty and absent as
agreement**: if we ask for nothing and Facebook shows nothing, that is not a
difference. Declaring it dropped would have been worse — a path in DROPPED is
skipped whenever it is missing from the live object, so *adding* an audience to
an adset that has none would have been silently never applied.
`test_update_adset_still_applies_a_newly_added_audience` guards that.

The rule is general and does not weaken the protections above: `link_data` and
`image_text_translation` both carry non-empty values, so both still require a
real answer.

## One more thing to be careful of near this code

**`hydrate_strata` mutates the strata it is given.** It appends to
`excluded_custom_audiences` in place, so calling it twice in one process
duplicates entries. The probe hit this immediately — hydrating separately for
ads and adsets invented a difference that did not exist — and now hydrates once
and shares. Anything calling it more than once per process will see phantom
targeting drift.

## Verified against live Facebook

`adopt-probe "OWIS Nigeria Study"` was run against production on 2026-08-01
(read-only, via a port-forward to the prod database):

```
ADS      compared 46 field paths across 60 live ads   -> 6 declared drops, 40 clean
ADSETS   compared 14 field paths across 6 live adsets -> 14 clean
contract matches live Facebook behaviour.             (exit 0)
```

And directly against the production function, with each live adset's own
budget and status fed back in so nothing had genuinely changed:

```
6/6 adsets no-op when nothing changed
```

Before this work that number was 0/6, on every run.

Running it against production caught three things no fixture-based test could:

- `db.query` is a generator, so `resolve_study_id`'s `if rows:` was always
  truthy and passed the study *name* through as if it were an id.
- Hydrating strata separately for ads and adsets duplicated audience
  exclusions and invented a targeting difference.
- The probe's own list comparison was stricter than `_eq`'s, flagging reordered
  audience refs that the reconciler ignores. `_walk` now delegates lists and
  scalars to `_eq` itself rather than reimplementing them.

The last one is the general lesson: anywhere the probe reimplements comparison
logic, it can disagree with the thing it is meant to be checking. Delegate.

## What probing 45 studies found

Run read-only on 2026-08-01 across every study with an end date in the previous
twelve months: 2 active, 43 historical. 42 of the 43 historical studies were
reachable — no expired tokens anywhere, including a study that ended a year
earlier. Probing old studies works. No rate limiting was hit in 45 sequential
runs.

**Only the two active studies came back clean.** Everything else showed at
least one difference, and neither category is a contract problem:

### `.targeting.targeting_automation` is not a drop — do not declare it

It appeared as an undeclared drop in 26 studies, every one ending 2026-02-26 or
earlier, and in none from 2026-04-10 onward. That boundary is the point:
`create_adset` now forces `targeting_automation = {"advantage_audience": 0}` on
every adset unconditionally. Adsets built before that policy simply do not have
the field set on Facebook's side.

So this is a **real difference that should be applied once**, not a field
Facebook refuses to echo. The live adsets of both active studies *do* carry
`targeting_automation`, which is exactly what proves it round-trips: once
written, Facebook returns it, and the comparison converges.

Declaring it in DROPPED would have been a bad mistake — a DROPPED path is
skipped whenever it is missing from the live object, so we would permanently
stop applying "Advantage+ Audience off" to any adset that lacks it. That is a
real targeting setting on real spend. This is the same shape as the
photo_data → link_data case: a genuine change wearing the costume of a drop.

It also costs nothing today. All 26 studies are inactive, and `get_active_studies`
means the cron never touches them.

### `end_time` always differs on inactive studies, by construction

`create_adset` sets `end_time` to *today's* midnight plus `ADSET_HOURS` (48), a
rolling window pushed forward on every run. An inactive study's live adsets are
frozen wherever the cron last left them, so the desired value is always "two
days from now" and the live one is always older. 34 studies showed this, all
with an identical `want` regardless of study age.

Nothing is wrong. It does mean **a probe report on an inactive study will never
be clean**, and that `end_time` diff carries no information. Worth knowing
before anyone wires the probe's exit code into a scheduled check across all
studies rather than active ones.

## What this does not cover

- The contract is a flat path namespace shared by ads and adsets. `daily_budget`
  and `end_time` happen to be adset-only, but a path that means different things
  on the two object types would need the namespace split.
- The probe feeds the live budget and status back in as the desired ones, so it
  says nothing about whether the optimizer's current budget is correct. It
  answers "does this round-trip", not "is this up to date".
- Removing the last audience from an adset that has some is still applied
  (both sides present, values differ), but the empty-and-absent rule means we
  cannot tell "we want none" from "we never asked" when Facebook has none
  either. That is the correct outcome here and worth remembering if the rule
  is ever reused for a field where absent and empty differ in meaning.
