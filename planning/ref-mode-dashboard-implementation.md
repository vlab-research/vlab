# Ref mode in the dashboard — implementation plan

**Handoff:** `planning/ref-mode-dashboard-HANDOFF.md` — read that first if
you are picking this up.

**Status:** built, then simplified in review. Dashboard 184 tests, adopt 718,
swoosh and the rest of inference green.

**Review pass (PR #246) cut three things as over-built**, and the theme is worth
keeping in mind for anything similar:

- **Thin is gone from the dashboard entirely**, not merely unselectable. The
  census says no conf resolves to it, so `REF_MODE_THIN`, the disabled
  current-value option, the per-channel branch in `displayedRefMode`, and the
  `disabled` support added to `Select` were all code defending an empty set.
  Every legacy conf is a Messenger one, so absent means thick, full stop.
- **`refModeOptions` collapsed** to "pure-Messenger study → both modes,
  otherwise encoded". The per-destination type check was redundant: the
  destination is in the list it judges.
- **Generation became a plain default.** The button, `mergeLookupConfs`,
  `wouldGenerateAnything` and the blank-row filtering are gone. The rule is
  simply: a source with saved confs shows those; a source without shows the
  generated ones. Nothing merges, and no second copy is held anywhere.

**Design:** `planning/ref-mode-dashboard-ux.md`. That document is the decision
record; this one is the build order. Read it first — every section below cites
the § it implements, and where this plan departs from it, the departure is
called out and justified.

**Branch:** `feature/ref-mode-dashboard-ux`, worktree `../vlab-ref-mode-ux`,
from `origin/main` (`b94aafe3`).

**Reads with:** `documentation/ad-attributions.md` (the join, both sides),
`adopt/README.md`, `dashboard/README.md`, `inference/README.md`.

---

## 0. What is already built, and what this adds

The **write side is done**. `RefModeDestination`, `resolved_ref_mode`,
`ref_mode: Optional[RefMode] = None`, `messenger_ref`, `whatsapp_autofill`,
`encoded_ref`, `mint_ref_token` and the `ad_attributions` table all ship today.
The **read side is done** too: `mapping: "ad_table_lookup"`, `AdAttributions`,
`retrieveFromMetadata`, the CSV export endpoint.

What is missing is everything a researcher touches. `ref_mode` is reachable only
by hand-authoring JSON through the API; the two halves of one decision live in
two unrelated forms; and the mapping the whole mechanism produces has no surface
at all. This plan builds the researcher-facing half, plus two corrections to
what exists.

Six pieces, in dependency order:

| | Piece | Where |
|---|---|---|
| A | Ref mode on the destination forms | dashboard |
| B | Auto-wire the read side from declared variables | dashboard |
| C | The ad-attributions verification surface | dashboard + adopt |
| D | Save-time coherence validation | adopt |
| E | Delete the organic branch | swoosh |
| F | Documentation pass | all |

A and B are independent. C depends on a new adopt endpoint. D depends on
nothing but is easiest to test after A. E is standalone. F is last, as a
dedicated pass, per the repo's documentation-first protocol.

---

## 1. Decisions taken before building

Four came from the design doc and were confirmed; two are mine, stated here so
they are reviewable rather than discovered in a diff.

### 1.1 Confirmed

- **§7 generation lives in the dashboard, explicitly.** A "generate from
  variables" action writes real `ad_table_lookup` confs into the form, editable
  before save — mirroring Strata's existing `createStrataFromVariables` /
  Regenerate pattern. Rejected: synthesizing them in adopt at `StudyConf`
  assembly, which would cover API-authored studies but make a study's stored
  conf stop describing what swoosh actually runs.
- **§6 validation refuses only when the counterpart conf exists.** Destinations
  and Data Extraction are separate POSTs and the wizard saves Destinations
  first, so an unconditional check would 422 every new encoded study before it
  could reach the extraction step. A study that is merely unfinished is not
  wrong; a study whose two halves contradict each other is.

  **Refined while building: the check is also one-directional.** Only a thin
  write with no read is refused. Refusing the other direction as well would make
  §5's flip unperformable in either order, each conf waiting on the other — see
  §5 below.
- **§4.4 gets a real surface**, not just a download: a dedicated
  **Ad Attributions** step showing each ad, its stratum and its `ref_token`,
  with the CSV download alongside it.
- **§5.3 is resolved by deletion, not suppression** — see §7 below. The rate
  that replaces it is **VIR-32**, in the backlog, out of scope here.

### 1.2 Mine, and why

**Thin is removed from the UI only. `"shortcode"` stays in the `RefMode`
literal.** §3 says "delete it from the surface entirely", and the surface is the
form. The literal cannot go: `resolved_ref_mode` returns `"shortcode"` for any
destination with `ref_mode is None` and `include_metadata_in_ref False`, which
is the resolution path §4.2 insists stays untouched for migration safety.
Removing the literal would either break that resolution or force a rewrite of
stored JSON — the exact thing §4.2 exists to prevent. Unreachable from the UI
is what "deleted" means here.

**The flip warning fires on any change to a saved destination's mode, not on
"has arrivals".** §5 says a mode change should be "guarded" and describes the
cost as the ad rewrite — spend, possible Meta re-review, learning-phase reset,
live reshared page-posts changing under old respondents. Every one of those
costs lands whether or not the study has arrivals yet, because they are
properties of the *ads*, not of the respondents. Gating on arrival counts would
need data the form does not have, and would suppress the warning in exactly the
case where acting on it is cheapest. So: warn whenever a destination that was
loaded with one mode is about to be saved with another.

---

## 2. Piece A — ref mode on the destination forms (§4.1, §4.3, §4.4)

### The pure module

New: `dashboard/src/pages/StudyConfPage/forms/destinations/refMode.ts`, no React
imports, tested in isolation — the same shape as the existing
`flyExtraction.ts` and `additionalMetadata.ts`.

```
REF_MODE_ENCODED = 'encoded'
REF_MODE_THICK   = 'metadata'      // the mode's stored name; never shown

refModeOptions(destinationType, storedMode)
    → encoded always
    → thick only when destinationType === 'messenger'   (§4.1)
    → plus storedMode as a disabled current-value entry when it is
      neither of the above (a legacy 'shortcode' conf; population is zero
      per the census, but showing it beats lying about it)

displayedRefMode(data, destinationType)
    → data.ref_mode when set
    → 'metadata' for messenger when absent      (§4.2: None ⟺ legacy thick)
    → the resolved legacy mode otherwise; NEVER the UI default

initialRefMode() → REF_MODE_ENCODED             (new confs only, §4.3)

refModeConsequence(mode) → the researcher-facing sentence (§4.4)
```

**Labels are framed by consequence, not by mechanism.** The word `ref_mode`
never appears, and neither does "encoded" as jargon. Per §4.4 the one thing that
must be communicated is where the researcher's stratum data ends up:

- encoded → *"Clean link. Stratum data comes from the ad-attributions export,
  joined on `ref_token`."*
- thick → *"Stratum values ride inline in every response. Messenger only."*

### The form wiring

- `dashboard/src/types/conf.ts` — add `ref_mode?: RefMode` to `Messenger`,
  `WhatsApp`, `Multi`; export `type RefMode = 'encoded' | 'metadata'`. Optional
  in TypeScript because absent is a real, meaningful state (§4.2).
- `Messenger.tsx`, `WhatsApp.tsx`, `Multi.tsx` — render the select from
  `refModeOptions`, valued by `displayedRefMode`, plus the consequence line.
- `Destination.tsx` — `ref_mode: 'encoded'` into the messenger, whatsapp and
  multi `emptyStates`; pass the destination type and the study's full
  destination list down (needed for "pure-Messenger study", §4.1).
- `Destinations.tsx` — `ref_mode: 'encoded'` in `initialState`.

### The sharp edge, and why this wiring is safe (§4.3)

The failure §4.3 names is: open a legacy thick study, edit the welcome message,
save, and `ref_mode` silently flips `None → "encoded"`. Three properties
together prevent it, and each is worth stating because each is load-bearing:

1. **`GenericList` renders `data` as-is.** `initialState` is spread only in
   `addItem` (`GenericList.tsx:26`), never merged into an existing element. So a
   stored destination arrives at its form untouched.
2. **The forms write `{...data, [name]: value}`.** A field absent from `data`
   stays absent through an edit to any other field.
3. **`displayedRefMode` is a display function only.** It is never written back.
   The select emits `ref_mode` into `data` only when the user actually changes
   it.

The UI default therefore lives in exactly two places — `emptyStates` and
`initialState` — both of which are new-conf constructors. That is what makes
"model defaults to legacy, UI defaults to encoded" coexist safely.

A test pins it directly: hydrate a destination with no `ref_mode`, change an
unrelated field, assert `ref_mode` is still absent from the emitted payload.

### The flip warning (§5.2)

`Messenger.tsx` holds the first-seen `ref_mode` in a `useRef` and renders a
warning block when the current value differs. Text names the real cost — the ref
is part of the creative, `COMPARED_AD` sees every existing ad as drifted, so the
next reconciliation run rewrites all of them: real spend, possible Meta
re-review, ad learning-phase reset, and live reshared page-posts changing under
respondents already recruited. It does **not** warn about data loss, because per
§5 there is none.

### Tests

`refMode.test.ts` — options per destination type; thick absent on
whatsapp/multi; thick present only for a pure-Messenger study; legacy
`shortcode` surfaced as a disabled entry; `displayedRefMode` maps absent→thick
on messenger; `initialRefMode` is encoded; the no-coercion property above.

---

## 3. Piece B — auto-wire the read side (§7)

A stratified ad study attributes its respondents; you do not opt into that. The
researcher already declared the stratum variables in **Variables**, and
re-declaring each one as an `ad_table_lookup` extraction by hand is precisely
the split that produces silent half-configs.

New pure module
`dashboard/src/pages/StudyConfPage/forms/inferenceData/generateLookupConfs.ts`:

```
lookupConfsFromVariables(variableNames, tokenKey = 'vt') → Extraction[]
    one conf per declared variable:
      { location: 'metadata', mapping: 'ad_table_lookup',
        key: tokenKey, name: <variable name>,
        functions: identityFunctions(), value_type: 'categorical',
        aggregate: 'first' }

mergeLookupConfs(existing, generated) → Extraction[]
    adds only names not already present; never overwrites a hand-edited conf
```

`aggregate: 'first'` and `identityFunctions()` are reused from `flyExtraction.ts`
rather than re-derived — `aggregateForLocation('metadata')` already returns
`'first'`, and metadata is a keyed read with no response path.

Surface: a button in `SourceExtraction.tsx`, rendered for **fly sources only**
(same reasoning as `mappingOptions` — Qualtrics and Typeform carry no token).
`InferenceData.tsx` already computes `globalData.variables.map(v => v.name)` for
its `nameOptions`, so the input is in hand.

The generated confs land in the form as ordinary editable rows and save through
the normal Submit. Nothing is synthesized behind the researcher's back; the
stored conf stays the whole truth.

**Token key.** `'vt'` by convention, matching what fly stamps and what
`disagreeing_token_keys` expects every lookup conf under one source to agree on.
Generation emits one key for all confs, so it cannot produce a disagreement.

### Tests

`generateLookupConfs.test.ts` — one conf per variable; correct shape;
idempotent (running twice adds nothing); a hand-edited conf with a matching
name survives; empty variables yields nothing.

---

## 4. Piece C — the ad-attributions surface (§4.4)

> `ref_token` is a verification surface, not an input. You do not configure
> them, you confirm them.

**adopt** — new `GET /{org_id}/studies/{slug}/ad-attributions` returning JSON,
beside the existing `.csv` route in `server.py`. Same auth, same
`get_study_id` ownership check, same `get_ad_attributions(study_id, db_cnf)`
load. Columns are the union across rows in first-seen order — and no extraction
was needed after all: `metadata_columns`, `column_name` and `_cell` were already
pure functions in `csv_export.py`, so `ad_attributions_table` just calls them.
The table and the CSV therefore cannot disagree about shape, which is asserted
directly rather than assumed.

Deleted ads are included, for the reason the CSV already includes them:
respondents keep arriving from ads reconciliation has removed, and a row missing
here would look exactly like an unattributed respondent.

**dashboard**

- `helpers/api.ts` — `fetchAdAttributions`, plus a CSV download helper. The
  endpoint needs an `Authorization` header, so a plain `<a href>` cannot fetch
  it: the helper fetches the blob, creates an object URL, clicks it, revokes it.
- `hooks/useAdAttributions.tsx` — react-query, matching the existing hook shape.
- `forms/adAttributions/AdAttributions.tsx` — table of ad, creative, form,
  stratum keys, `ref_token`, created; download button; an empty state saying
  rows appear once ads have been built, since before the first reconciliation
  run there is legitimately nothing.
- `shared.ts` — register the step after **Current Data**, before **Errors**.

**Note on `getNextConf`:** `shared.ts`'s `confs` array doubles as the wizard's
next-step chain. Inserting a step changes where Current Data advances to. That
is intended — verification belongs after the data appears — but it is a
behaviour change to state in review rather than let someone find.

---

## 5. Piece D — save-time coherence validation (§6)

Today the incoherent states surface hours later in a swoosh log or a cron
warning. They should be refused at save, naming *both* sides.

**Pure predicate**, in `adopt/adopt/study_conf.py` beside the existing guards:

```
ref_mode_incoherence(destinations, inference_data) → Optional[str]
```

Returns a message, or None. It takes the two confs rather than a `StudyConf`,
because at save time no assembled study exists — only the conf being written and
whatever its counterpart already is.

**As built it checks one direction, not two.** The plan called for both; the
second turns out to make §5's flip impossible.

- **Refused** — a fly destination resolving to a thin mode (`encoded` or
  `shortcode`) while no extraction conf declares `mapping: "ad_table_lookup"`.
  The ad stops carrying the stratum and nothing looks it up, so every stratum
  counts zero and the optimizer reallocates on empty data.
- **Allowed** — a lookup conf declared while no destination emits a token. Those
  confs extract nothing and swoosh skips them; the respondent is still
  attributed inline, so nothing is lost.

The asymmetry prescribes the safe order for a flip: add the lookup confs first,
where they lie dormant against a thick destination, then flip the destination.
Refusing both directions would deadlock that — the destination save waiting for
confs, the conf save waiting for the destination. Refusing one turns the 422
into the instruction.

The message names the destination *and* the conf, because being told only one
half is how someone fixes the wrong side.

**Wiring**, in `server.py`: `create_destinations_conf` and
`create_inference_data_conf` load the counterpart and raise
`HTTPException(422, detail=...)` only when it **exists** and the pair is
incoherent.

`get_study_conf` turned out to *raise* on a missing conf rather than return
`None`, so `find_study_conf` was split out of it for callers to whom absence is
an ordinary answer. A stored conf that no longer parses is treated as absent
too: refusing to let someone save Destinations because an unrelated conf is
malformed would be a dead end with no way out through the UI.

### A latent bug this piece uncovered

Confs are stored as `model_dump()`, which writes defaults. So the moment the UI
began sending `ref_mode: "encoded"`, a Messenger destination was stored as
`{"ref_mode": "encoded", "include_metadata_in_ref": true}` — Messenger defaults
that flag `True`. Re-reading it put the flag in `model_fields_set`, which is
exactly what `ref_mode_must_not_contradict_the_legacy_flag` rejects: the save
returned 201 and the study was then permanently unparseable, stopping its
reconciliation. `RefModeDestination` now omits the legacy flag on serialisation
once `ref_mode` is stated, which is what that validator's own message asks a
human to do. Caught by the endpoint tests, not by the unit tests — nothing else
round-tripped a conf through storage.

This is a deliberate weakening of §6's "make the wrong thing unsaveable", and
the reason is the wizard order: Destinations is saved before Data Extraction
exists, so an unconditional refusal would make an encoded study unsaveable at
step 4 of 10. The uncovered case — a study that saves encoded destinations and
then never configures extraction — is exactly what
`thins_its_ref_without_reading_the_mapping` already warns about, and that guard
stays as the backstop it was written to be.

Kept unchanged, per §6: `a_lookup_reads_the_token_from_metadata`,
`ref_mode_must_not_contradict_the_legacy_flag`, and
`thins_its_ref_without_reading_the_mapping` as a warning. The UI never sends
`include_metadata_in_ref`, so the contradiction validator becomes reachable only
by API-authored confs — which is what it is for.

### Tests

`test_study_conf.py` for the predicate, both directions plus the coherent cases;
a server test for the 422 and, importantly, for the **non**-422 when the
counterpart is absent.

---

## 6. Piece E — delete the organic branch (§5.3, superseded)

§5.3 filed monitoring noise as a residual to be scoped away. On inspection the
category itself is the defect, so this is a deletion rather than a suppression,
and §5.3 stops existing.

`adAttributionOutcome` classifies by **mechanism state** — is there a token,
does it resolve — when the only thing worth reporting is **outcome**: could this
respondent be attributed. `organic` is an expected, correct, non-error result
sitting on an error page; the "does not alarm" carve-out in
`classifyExtractionError` is the acknowledgement that it never belonged there.

Once an error is defined as *an unmappable respondent*, three outcomes collapse
to two:

```
token present?
  no  → nothing.        No ad provenance. Not an error.
  yes → resolves?
          yes → nothing.     attributed
          no  → UNMAPPED.    error: vlab minted an ad and lost its meaning
```

The thick-era respondent §5.3 worried about stops being reported because it was
never an error — not because the code learned to recognise it. And the
documented rule that *a row found but missing the requested key is a conf
problem, not unmapped* survives untouched, since resolution is judged on the row
rather than on the value.

Changes:

- `inference/swoosh/inference_data.go` — remove the no-token branch and
  `entityAdOrganic`; rewrite the doc comment on `adAttributionOutcome`, which
  currently describes a three-way split.
- `inference/swoosh/events.go` — remove the organic case from
  `classifyExtractionError`; rewrite its doc comment likewise.
- Tests updated; a test asserting *no* event for a tokenless respondent.

**What this gives up, deliberately.** The leaked-shortcode signal the organic
count nominally existed for, and the "encoded study receiving no tokens at all"
case. Neither worked on this surface: a count with `first_seen`/`last_seen`
cannot show a jump, and the branch explicitly did not alarm. Both are the same
measurement — *what share of respondents arrived with no ad provenance* — which
needs a denominator an error list does not have. Filed as **VIR-32**.

**Precedent.** `planning/swoosh-config-reconciliation.md:14` records the same
shape: a warning re-emitted every hourly run over 52,090 historical rows, never
ageing out through the recency predicate, described there as *"a permanent false
alarm."* An organic branch on a flipped study is that, by construction, forever.

---

## 7. Piece F — documentation pass

A dedicated step after the code, per the repo's documentation-first protocol —
not mixed into the pieces above.

- `documentation/ad-attributions.md` — "The three-way split" section is now
  wrong; rewrite as two. Update "Declaring an ad-derived variable" for
  generation, and "The mapping CSV export" for the download button and JSON
  endpoint ("There is no dashboard download button yet" stops being true).
  Document the ref-mode form.
- `dashboard/README.md` — the new step, the new pure modules.
- `adopt/README.md` — save-time coherence validation and its deliberate limit.
- `inference/README.md` — the outcome change.
- `planning/ref-mode-dashboard-ux.md` — mark built; record that §5.3 was
  resolved by deleting the category, with a pointer to VIR-32.

---

## 8. Verification

| Piece | Command | Needs |
|---|---|---|
| A, B, C (dashboard) | `cd dashboard && npm test` | `npm install` in the worktree |
| A, B, C (types) | `cd dashboard && npx tsc --noEmit` | — |
| C, D (adopt) | `cd adopt && pytest` | `make test-db` |
| E (swoosh) | `go vet ./swoosh/... && go test ./swoosh/...` | `make test-db` |

Dependencies are not shared between worktrees; `../vlab-ref-mode-ux/dashboard`
needs its own `npm install`.

## 9. Risks

- **`getNextConf` chain changes** when the Ad Attributions step is registered
  (§4). Intended, but user-visible.
- **`refModeOptions` needs the whole destination list** to decide "pure-Messenger
  study" (§4.1), which means threading it from `Destinations.tsx` through
  `Destination.tsx`. Mild prop drilling; the alternative is deciding per
  destination, which would offer thick on the Messenger arm of a mixed study and
  reintroduce exactly the per-channel heterogeneity §4.1 removes.
- ~~**The CSV shape extraction** (§4) touches shipped export code.~~ Did not
  arise: the column logic was already pure and is reused as-is, so the shipped
  CSV path is untouched and its tests pass unchanged.
- **`getByLabelText` does not work on these forms.** The shared `TextInput` and
  `Select` render a `<label>` with no `htmlFor`, so nothing associates it with
  its control; component tests query by role and placeholder instead. Worth
  fixing, but it touches every form in the app and was left out of scope.
- **No production study currently sets `ref_mode`.** Every path added here is
  new-conf-first, and the legacy resolution is untouched, so the blast radius is
  studies someone deliberately edits.
