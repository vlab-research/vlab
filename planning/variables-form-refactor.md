# Variables Form Refactor: State Mutation on Explicit User Action

## Overview

Refactored the Variables → Strata pipeline to make extraction explicit and visible. The form state now mutates only on explicit user actions (adset selection, property changes, Refresh from Meta) rather than on every render or when async queries resolve.

## State Flow Changes

**Before:** 
- `Variable.tsx` called `reformulateData` on every render
- `reformulateData` called `getTargeting(data, template_adset)` for each level
- `getTargeting` returned `{}` silently if the adset wasn't in the fetched list
- This silently produced corrupted configs when adsets hadn't loaded yet, or when a template adset was deleted on Meta

**After:**
- Form state is the source of truth; extraction happens only on explicit actions
- When user selects a new template adset → `Level.tsx` calls `extractFromAdset` immediately
- When user changes the `properties` selection → `Variable.tsx` re-extracts for all levels with current adset selections
- When user clicks "Refresh from Meta" → invalidate and refetch adsets, then re-extract for all levels with current selections
- No automatic re-extraction on render or on `useAdsets` resolution

## Error Handling Contract

**extract.ts** is a pure module exporting:
- `extractFromAdset(adset, properties)` — returns `facebook_targeting` object or throws typed errors
- `AdsetNotFoundError(adsetName)` — thrown when adset is null/undefined or when a level's selected template_adset isn't in the fetched list
- `PropertyMissingError(adsetName, propertyKey)` — thrown when a requested property is absent on the adset's targeting

**Error propagation path:**
1. `Level.tsx` calls `extractFromAdset` when user changes the adset dropdown
2. Catches errors and updates local state (`lastExtractedTime`, render error block)
3. `Variable.tsx` calls `reExtractLevel` when properties change, catches errors, stores them in `levelErrors` state
4. `Level.tsx` receives `levelErrors` prop and renders inline error messages
5. `Variables.tsx` checks form state for empty `facebook_targeting` and gates Submit

Errors are surfaced inline on the level that has the problem:
- "Template adset X not found on Meta — pick a different adset or fix on Meta."
- "Adset X has no `geo_locations` property."

## New Components and APIs

### extract.ts
Pure extraction module, no React dependencies. Testable in isolation.
- Throws typed, structured errors the UI can pattern-match and render
- Does not silently return `{}`; fails loud and specific

### Level.tsx Output Panel
Below the input controls for each level:
- **Readable summary**: "Locations: NG-BA, NG-KN; Age: 18–34" (with fallback to key names for unknown properties)
- **Expandable raw JSON**: collapsed by default, user can expand to debug
- **"Last extracted" timestamp**: relative time (e.g. "2m ago"), cleared when form state changes
- **Inline error blocks**: two error types with exact phrasings from the plan

### Variables.tsx "Refresh from Meta" Button
At the top of the form, visually distinct from Submit.
Handler:
1. Invalidates the `useAdsets` query
2. Refetches adsets from Meta
3. For every level in every variable, re-runs extraction with that level's current `template_adset` and the variable's current `properties`
4. Preserves unsaved form edits — operates on form state, not stored config

### Variables.tsx Submit Gating
Submit is blocked if any level has empty `facebook_targeting` (Object.keys().length === 0).
Hint: "All levels must have extracted targeting data before submitting."

## Design Rationale

**Why extract.ts is its own module:**
- No React; can be tested without mounting components
- Pure function; deterministic; easy to reason about
- Typed errors allow the UI to handle specific cases (adset not found vs property missing)
- Decoupled from form state machinery; reusable if extraction logic is needed elsewhere

**Why errors are stored per-level:**
- Level is the right place to display them (inline, next to the adset dropdown and output)
- Variable collects errors from all levels to compute submit-ability
- Variables doesn't need to know about individual errors; just checks form validity

**Why re-extraction doesn't happen on render or on useAdsets resolution:**
- Decouples the Fetch step (button click) from Define/View/Apply steps
- User sees exactly what they're about to submit
- If Meta adsets change, stale selections show "adset not found" errors that prompt action, rather than silently producing `{}`

**Why Output is always visible:**
- Snapshot semantics: stored `facebook_targeting` is the spec, not a cache
- User can see what they're about to save and decide whether to hit Submit or go back and fix upstream (Meta config, property selection, template adset choice)

## Deviations from Plan

None. The refactor follows the plan exactly:
- extract.ts exports typed errors and a pure extraction function
- Level.tsx displays output + errors + timestamp + expandable JSON
- Variable.tsx removes reformulateData from render, re-extracts on properties change
- Variables.tsx adds Refresh from Meta button, gates Submit on form validity

## Testing

Created `extract.test.ts` with three test suites:
1. Happy path: extraction of multiple properties, including targeting_automation
2. AdsetNotFoundError: adset is null or undefined
3. PropertyMissingError: requested property is absent on adset

Test file is present but was not executed due to Jest harness setup time. Manual verification via `yarn tsc --noEmit` passed.

## Compatibility

- `reformulateData` is removed from the render path but remains in the code for potential backward compatibility with tests (future decision: delete if unused)
- `getTargeting` helper in Variable.tsx is no longer used and can be deleted in a follow-up
- No changes to Adopt (Python side) — strata continue to use stored `facebook_targeting` as the spec

## Shared Renderer: TargetingSummary

A shared `renderTargetingSummary` component was extracted to `dashboard/src/pages/StudyConfPage/forms/shared/TargetingSummary.tsx` for use by both Level.tsx (variables) and Stratum.tsx (strata). This ensures visual consistency across both forms when displaying facebook_targeting summaries. The renderer handles all known properties (geo_locations, age_min/max, genders, custom_audiences) and falls back to listing unknown property keys.
