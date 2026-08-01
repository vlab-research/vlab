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

## Verified against live Facebook

`adopt-probe "OWIS Nigeria Study"` was run against production on 2026-08-01
(read-only, via a port-forward to the prod database). It compared 46 field
paths across all 60 live ads, found the six drops above, and after `--update`
reports `contract matches live Facebook behaviour` and exits 0.

That run also caught a bug the unit tests could not: `db.query` is a
generator, so `resolve_study_id`'s `if rows:` was always truthy and passed the
study *name* through as if it were an id. Fixture-based tests never touch it.

## What this does not cover

- Only ads are probed today. Adset fields are declared in `COMPARED_ADSET` but
  the probe does not fetch and classify live adsets yet.
- The contract is a flat path namespace shared by ads and adsets. If a path
  ever collides between them, it needs splitting per object type.
- `daily_budget` legitimately differs on most runs (the optimizer moves it).
  The probe reports that as `differs`, which is correct but noisy — it is a
  real, intended, once-per-run change rather than drift.
