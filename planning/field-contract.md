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

## Two things to be careful of near this code

**The argument order is reversed between the two callers.** `update_ad` calls
`_eq(desired, live)`; `update_adset` calls `_eq(live, desired)`. Since `_eq`
walks the *first* argument's keys and tolerates extras in the second, the two
paths do genuinely different things. It also makes the log messages misleading
on the adset path — `desired=` there is actually the live value. `probe_adsets`
deliberately mirrors the production order so a clean report means the
reconciler really will no-op. Worth unifying, but it is a behaviour change to
reconciliation and deserves its own verification.

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
ADSETS   compared 13 field paths across 6 live adsets -> 13 clean
contract matches live Facebook behaviour.             (exit 0)
```

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

## What this does not cover

- The contract is a flat path namespace shared by ads and adsets. `daily_budget`
  and `end_time` happen to be adset-only, but a path that means different things
  on the two object types would need the namespace split.
- The probe feeds the live budget and status back in as the desired ones, so it
  says nothing about whether the optimizer's current budget is correct. It
  answers "does this round-trip", not "is this up to date".
- `targeting.custom_audiences` is sent by adopt (as `[]`) and never returned by
  Facebook. Invisible today because the adset path walks the live object's keys,
  so it is never examined — but it would surface immediately if the argument
  order above were unified.
