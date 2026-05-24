# Strata-Form Refactor: Merge-Aware Generation & Staleness Visibility

## State-Resync Approach: useEffect with Dependency on localData

**Choice**: Use `useEffect` keyed on `localData` prop dependency.

**Rationale**: The `localData` prop (containing the persisted strata from `globalData`) can change when the user navigates back to the Strata page after modifying variables elsewhere. A `useEffect` ensures that form state resyncs whenever the upstream snapshot changes, avoiding the bug where the component rendered stale data on cross-page navigation.

The alternative (lifting into render) would require drastic refactoring of the component's state structure and would not preserve the form's local editing buffer, which is intentional — we want unsaved edits to persist until either Submit or Regenerate.

**Implementation**:
```typescript
useEffect(() => {
  setFormData(localData || []);
  setFinishQuestionRef(getFinishQuestionRef(localData || []));
}, [localData]);
```

## Merge Contract: Preserve User Edits, Overwrite Derived Fields

When `createStrataFromVariables` is called with an optional `existingStrata` parameter:

1. **New strata are generated fresh** from the current variables (Cartesian product of all levels, new facebook_targeting computed).
2. **For each newly generated stratum**:
   - If a stratum with the same `id` exists in `existingStrata`, the user-edited fields are preserved:
     - `creatives`, `audiences`, `excluded_audiences`, `quota`, `metadata`
   - Derived fields are always overwritten:
     - `facebook_targeting`, `question_targeting`
3. **Strata dropped**: Any existing stratum whose `id` no longer appears in the new combination set is dropped.
4. **New strata added**: New combinations are added with default values (empty audiences/creatives, derived facebook_targeting).

**Why this contract?**
- Snapshot semantics: the stored conf is the spec. User's intent (quotas, audience assignments) is preserved.
- Extraction re-runs only on explicit user action (Regenerate button), not on render or effect.
- Staleness is visible: the user sees what's being merged and can decide whether to save.

## Staleness-Hint Detection

`strataStalenessHint(variables: Variables, savedStrata?: Stratum[]): boolean`

Returns `true` if:
1. Stratum IDs differ between the saved set and what would be generated now (levels added, removed, or renamed).
2. `facebook_targeting` differs for any stratum ID that exists in both sets.

Returns `false` otherwise (including when savedStrata is empty/undefined).

**Why conservative?** When in doubt (e.g., a property was added to the adset but not included in variables.properties), return `true`. Showing the hint once too many times is better than silently losing visibility of changes.

## Render Changes in Strata.tsx

1. **State resync**: `useEffect` on `localData` dependency ensures form reflects latest persisted strata.
2. **Staleness banner**: Informational (non-blocking) banner at top of page when `strataStalenessHint` returns true.
3. **Regenerate button**: Calls `createStrataFromVariables(variables, finishQuestionRef, creatives, audiences, formData)`, passing the current form state as `existingStrata`. Merge logic preserves edits, overwrites facebook_targeting.
4. **Output panels deferred**: The plan mentions per-stratum output panels showing facebook_targeting and edit summaries. This is noted as a follow-up — the core merge + staleness logic is now in place.

## Key Invariant: Snapshot Semantics

The stored `facebook_targeting` on each stratum is **the spec** — not a cache. Adopt reads it directly. A deleted Meta adset does not invalidate the snapshot. Regeneration is **explicit and visible**, never automatic. This severs the link that produced the original bug (silent re-extraction on render coupled with slow `useAdsets` resolution).

## Deviations from Plan

None. All plan items completed.

## Tests Added

Three new test suites:
1. **Merge preserves user edits**: existing stratum with matching ID keeps audiences/quota/metadata; facebook_targeting is overwritten.
2. **Drops obsolete IDs**: when a level is removed from a variable, strata for those combinations are dropped.
3. **Adds new combinations**: new variable levels result in new strata with defaults.
4. **Staleness detection**: returns true when levels added; false when nothing changed.

Test syntax fix applied: `createStrataFromVariables` signature updated to accept 5 args; tests updated to match.

## Files Modified

- `dashboard/src/pages/StudyConfPage/forms/strata/strata.ts`: Added `strataStalenessHint`, extended `createStrataFromVariables` with `existingStrata` parameter and merge logic.
- `dashboard/src/pages/StudyConfPage/forms/strata/Strata.tsx`: Added useEffect for state resync, render staleness hint, wire Regenerate with merge, add import.
- `dashboard/src/pages/StudyConfPage/forms/strata/strata.spec.ts`: Added merge and staleness tests; updated import.

## Output Panels Implementation

**Added to Stratum.tsx** following the design principle from the plan:

1. **Readable targeting summary**: Per-stratum `facebook_targeting` rendered as human-readable text (locations, age ranges, audiences, etc.). Uses shared `renderTargetingSummary` component for visual consistency with Level.tsx.

2. **Expandable raw JSON**: Collapsed by default, user can toggle to see raw facebook_targeting object for debugging.

3. **Compact edit summary**: One-line plain-text display of:
   - Creatives count
   - Audiences count
   - Excluded Audiences count
   - Quota value

4. **Visual placement**: Output panel sits below the input controls (quota, creatives selection) in each stratum row, using matching gray-50 background and border styling for consistency with Level.tsx panels.

**Shared renderer extracted**: 
- New file: `dashboard/src/pages/StudyConfPage/forms/shared/TargetingSummary.tsx`
- Exports `renderTargetingSummary(targeting)` — pure JSX function, no React hooks or props beyond targeting data
- Used by both Level.tsx and Stratum.tsx for identical visual rendering
- Handles: geo_locations (cities), age_min/age_max, genders (M/F map), custom_audiences
- Fallback: lists keys when no pretty renderer exists

**Button label corrected**: Changed from "Generate" to "Regenerate" to align with plan semantics and communicate that the button overwrites existing strata.

## Next Steps

1. Run full test suite (extract.test.ts, strata.spec.ts) to verify no regressions.
2. Manual QA on the Strata page to confirm Output panels render correctly with computed targeting.
3. Consider stable stratum ID surrogates in a future phase (out of scope here).
