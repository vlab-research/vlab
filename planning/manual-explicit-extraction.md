# Plan: Manual + Explicit Extraction (v2)

## Problem we keep solving

Extraction (pulling `facebook_targeting` from template adsets on Meta) runs
in a `useEffect` whenever the component mounts or react-query refetches
adsets. The user has no control over when it happens, and "Last extracted:
just now" appears without any user action.

The remaining pain after v1 (timestamp/snapshot tracking) is that
**the staleness indicator turns on as soon as the user edits
`properties` or `template_adset`, even though nothing on Meta has
changed.** That's misleading. The user said edits shouldn't be enough
to claim "stale."

## Design (v2)

Three lifecycle-separated concerns:

| Concept | Where it lives | Triggered by | Mutates form data? |
|---------|----------------|--------------|---------------------|
| **Meta cache** | `react-query` via `useAdsets` | Auto on mount + manual top button | No — in memory only |
| **Apply** | Per **variable** button | User click | Yes — writes `facebook_targeting` per level |
| **Submit** | Form | User click | Posts form to backend |

The level output panel always renders **the last applied** targeting
(`level.facebook_targeting`). It is **never** auto-replaced by a Meta
cache arrival or a `properties`/`template_adset` edit. The output changes
only when the user clicks Apply.

There is **no per-level extraction metadata** stored in `conf.ts`. We
don't track `lastExtractedTime`, `lastExtractedAdset`, or
`lastExtractedProperties` — they're derived from existing state at
diff time. Saving the form keeps `facebook_targeting` only; no inert
fields.

## Diff detection (per level)

Two helpers in `extract.ts`:

```typescript
isLevelInSync(stored, wouldApply)         // true iff equal (excluding targeting_automation)
diffPropertyKeys(stored, currentProps)   // { added: string[], removed: string[], keysDiffer }
```

The **`isLevelInSync`** comparison strips the always-emitted
`targeting_automation` block so that pre-fix saved data (without that
key) compares equal to freshly-extracted targeting.

**`diffPropertyKeys`** uses `Object.keys(stored)` minus
`targeting_automation` as a proxy for "what was last applied." This
spares a separate `lastExtractedProperties` field — the proxy is good
enough because `facebook_targeting` is structurally `{[key]: value}`
for every applied property.

A level is **out of sync** when `extractFromAdset` succeeds and
`isLevelInSync(stored, wouldApply)` is `false`. If `extractFromAdset`
throws (`AdsetNotFoundError`, `PropertyMissingError`), we render the
error block as before — the per-level error takes priority over the
banner.

## Out-of-sync banner (per level)

Two-line when keys differ; one-line when only values drift:

> **Properties changed: added X, removed Y.**
> Apply on the variable above to use your current selections.

or

> Out of sync with current Meta data — Apply on the variable above to use your current selections.

The banner does not appear when the level is in sync — the output panel
just shows the targeting + the Advantage+ source/applied callout + the
JSON toggle.

## Per-variable Apply

One button per Variable row, in the same row cluster as `properties`.

**Disabled with reason** while one of these is true:

| Reason | Caption |
|--------|---------|
| `useAdsets` `isLoading` | "Waiting for Meta cache…" |
| `useAdsets` `isError`  | "Meta cache unavailable — refresh to retry." |
| `variable.properties.length === 0` | "Select properties above to enable Apply." |
| `variable.levels.length === 0` | "Add a level below to enable Apply." |

**Click** → run `extractFromAdset` for every level in this variable
using **current** `useAdsets` cache + the variable's current
`properties` + each level's `template_adset`. On success, write
`facebook_targeting`. On throw, write `facebook_targeting: {}` and let
the per-level live preview surface the error inline.

## Refresh button (top)

Lives next to a status row.

| Lifecycle | UI |
|-----------|----|
| `isFetching` true | Spinner + "Refreshing from Meta…" + "Loading…" caption |
| Idle + success | "Refresh from Meta" + "Meta last pulled: 2m ago" from `useAdsets`'s `dataUpdatedAt` |
| `isError` (after a successful load) | "Refresh from Meta" + "Pull failed — click to retry." |

The first-load `isLoading` -> `LoadingPage`. The first-load
`isError` (no prior data) -> existing `ErrorPlaceholder`. After a
successful pull, even if a later refetch errors, the form keeps
showing cached adsets and the top button surfaces the error.

## Submit gating

- **Block** if any level has empty `facebook_targeting` (existing
  rule).
- **Non-blocking warning** if any level is out of sync (count
  computed at the form level using `extractFromAdset` + `isLevelInSync`
  per level). Message:
  > N levels out of sync with current Meta data — Apply on the variable
  > above each to sync before submitting.

The warning is suppressed when `hasEmptyTargeting` is already blocking,
so the user sees only one message at a time.

## Files to modify

| File | Change |
|------|--------|
| `dashboard/src/types/conf.ts` | Revert v1 additions (`lastExtractedTime`, `lastExtractedAdset`, `lastExtractedProperties` all removed from `Level`). |
| `dashboard/src/pages/StudyConfPage/forms/variables/extract.ts` | Add two helpers: `isLevelInSync`, `diffPropertyKeys`. Domain types stay. |
| `dashboard/src/pages/StudyConfPage/forms/variables/extract.test.ts` | Add tests for the two helpers. |
| `dashboard/src/pages/StudyConfPage/forms/variables/Level.tsx` | Live `wouldApply` + `isLevelInSync` per render; out-of-sync banner; Advantage+ callout unchanged; no "Last extracted" timestamp. |
| `dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx` | Per-variable Apply button + disabled reason; no per-level extraction logic; pass `properties` to each Level. |
| `dashboard/src/pages/StudyConfPage/forms/variables/Variables.tsx` | Refresh lifecycle (status row, last-pulled caption); submit warning on out-of-sync; "View" of `outOfSyncCount` derived from same helpers; no per-form extraction logic anymore. |
| `dashboard/src/pages/StudyConfPage/forms/strata/strata.ts` | Unchanged — strata still reads `level.facebook_targeting`. |
| `marketing.py` | Unchanged — backend safety net stays as-is. |

## What NOT to change

- `extract.ts` (`extractFromAdset`, `AdsetNotFoundError`, `PropertyMissingError`) — same logic, just two new helpers added alongside.
- `TargetingSummary.tsx` — the pure renderer stays.
- `strata.ts` — strata generation unchanged.
- `marketing.py` — backend safety net unchanged.

## Migration note (v1 → v2)

Old study confs in the DB may have `lastExtractedTime`,
`lastExtractedAdset`, `lastExtractedProperties` keys in their
`level.facebook_targeting` adjacent fields. After v2 revert these
fields aren't read or written, so they sit inert in JSON until the
next Apply + Submit overwrites the level. No data migration needed.
