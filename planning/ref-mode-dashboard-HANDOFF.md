# Handoff: ref mode in the dashboard (PR #246)

**Written 2026-08-24.** Read this first, then the PR's review comments — there is
a merge review on #246 that has **not** been read or acted on by anyone yet.
That review is your work queue; this document is the context you need to act on
it without relitigating what is already settled.

---

## 0. Where everything is

| | |
|---|---|
| Repo | `vlab` (`git@github.com:vlab-research/vlab.git`) |
| Worktree | `/home/nandan/Documents/vlab-research/vlab-ref-mode-ux` |
| Branch | `feature/ref-mode-dashboard-ux` |
| PR | **#246**, open, mergeable, 9 commits off `origin/main` (`b94aafe3`) |
| HEAD | `e0e38e98` — working tree clean, everything pushed |

**Documents, in the order worth reading:**

1. `planning/ref-mode-dashboard-ux.md` — the design. The decision record, with a
   header listing what changed while building.
2. `planning/ref-mode-dashboard-implementation.md` — the build plan, annotated
   with what actually happened per piece.
3. `documentation/ad-attributions.md` — **the shipped behaviour**, and the one to
   keep true. Cross-component: the join, both sides, the ref modes, the save-time
   refusal, what swoosh reports.
4. `adopt/README.md`, `dashboard/README.md`, `inference/README.md` — per-app.

All four are current as of `e0e38e98`. If you change behaviour, they are part of
the change (repo protocol: docs are a dedicated step, not folded into the code
commit).

---

## 1. What this PR does, in one paragraph

The ad→stratum attribution mechanism already shipped on both sides: adopt writes
`ad_attributions` rows and mints encoded refs, swoosh joins them via
`mapping: "ad_table_lookup"`. What was missing was everything a *researcher*
touches — `ref_mode` was reachable only by hand-authoring JSON through the API,
the two halves of one decision lived in two unrelated forms, and the mapping the
whole mechanism produces had no surface at all. This PR builds that half.

| Piece | Where |
|---|---|
| A · Ref mode on the Messenger/WhatsApp/multi destination forms | dashboard |
| B · Read-side extraction confs defaulted from declared variables | dashboard |
| C · Ad Attributions step: table + CSV download | dashboard + adopt |
| D · Save-time 422 on an incoherent write/read pair | adopt |
| E · Delete the `ad=organic` outcome | swoosh |
| F · Documentation pass | all |

---

## 2. The load-bearing decisions

These are settled and were argued through. **Do not re-derive them; if a review
comment challenges one, the reasoning is here and in the linked docs.**

### 2.1 The model defaults to legacy, the UI defaults to encoded

`ref_mode: Optional[RefMode] = None`, and `None` resolves to `"metadata"` — the
stratum inline. The dashboard writes `ref_mode` explicitly into every **new**
destination. That makes `ref_mode is None` mean exactly one thing: *created
before this feature existed*, which is a thick Messenger study.

**The failure this guards against**: open a legacy thick study, edit its welcome
message, save, and re-serialise `ref_mode` from absent to `"encoded"` — silently
flipping a running study's ads. Three properties prevent it, all three
load-bearing:

1. `displayedRefMode` reports what a conf *actually does* and is never written
   back.
2. The encoded default lives **only** in the two empty-state constructors
   (`Destination.tsx` `emptyStates`, `Destinations.tsx` `initialState`), both of
   which build new confs.
3. `GenericList` renders stored data as-is and the forms spread `...data`, so a
   field absent from a conf stays absent through an unrelated edit.

`dashboard/.../destinations/Messenger.test.tsx` exercises exactly that scenario.
**If you touch the destination forms, keep that test passing.**

### 2.2 There are two ref modes, and only ever two

`RefMode = Literal["metadata", "encoded"]`. A ref either carries the stratum
inline or carries a token that resolves to it. "Carry neither" attributes nobody
and is not something anyone chooses — a study with no stratification simply has a
short ref, because `creative_metadata` has nothing to put in it. That is thick
with nothing to say, not a mode.

A third mode `"shortcode"` and a boolean `include_metadata_in_ref` used to exist.
Both are **deleted**, in `4b335b03`. Neither was ever deployed (committed
2026-08-17, removed before reaching production), so nothing stored carries them
and there is no migration to worry about.

Deleting them **deleted a bug rather than patching one**: confs are stored as
`model_dump()`, which writes defaults, so a destination saved with
`ref_mode: "encoded"` landed as `{"ref_mode": "encoded",
"include_metadata_in_ref": true}` — and re-reading it tripped the validator that
rejected that exact pair, leaving the study permanently unparseable after a save
that returned 201. With one field there is nothing left to contradict.

### 2.3 The save-time 422 is one-directional, and conditional

`ref_mode_incoherence(destinations, inference_data)` in `study_conf.py`, wired
into `create_destinations_conf` and `create_inference_data_conf`.

- **Refused**: a thin write with no read — ads stop carrying the stratum and
  nothing looks the token up, so every stratum counts zero and the optimizer
  reallocates on empty data, silently.
- **Allowed**: a read with no thin write — those confs extract nothing and
  swoosh skips them; the respondent is still attributed inline.

That asymmetry is **not tolerance, it is the mechanism**: it prescribes the safe
order for switching a live study (add the lookup confs first, where they lie
dormant; then flip the destination). Refusing both directions would deadlock the
flip, each conf waiting on the other.

It fires **only when the counterpart conf exists**, because the wizard saves
Destinations at step four of ten. The never-configured case stays with
`thins_its_ref_without_reading_the_mapping`, which warns every reconciliation run.

### 2.4 swoosh reports only the unmappable

`adAttributionOutcome` used to classify three ways and count `ad=organic` for any
event with no token. That classified by *mechanism state* when an error surface
should carry *outcome*, and the "must not alarm" carve-out it needed was the
admission it did not belong there.

It was also **false** for flipped studies: both eras attribute (they partition by
presence of the token), but pre-flip respondents carry none, and swoosh recomputes
all history every run — so it reported the whole back-catalogue as "not
attributed to any stratum", forever, while those respondents sat there attributed.
Same shape as the 52,090-row `source=Fly` permanent false alarm in
`planning/swoosh-config-reconciliation.md`.

Now: no token → nothing; token that resolves → nothing; token that does not
resolve → `unmapped` at severity `error`.

**Deliberately given up**: the share of respondents arriving with no ad
provenance — which is what would catch a leaked shortcode *and* an encoded study
receiving no tokens at all. Neither worked as an error count. That is a **rate**,
needing a denominator an error list has not got. Filed as **VIR-32** (Linear,
Virtual Lab team, Backlog).

---

## 3. What two rounds of review already changed

Do not reintroduce any of this. The consistent direction was **delete code that
defends cases that do not exist**.

| Round | Change |
|---|---|
| 1 | Thin removed from the dashboard; `REF_MODE_THIN`, the disabled current-value option, and the `disabled` support added to shared `Select` all deleted (`Select.tsx` is byte-identical to `main` again) |
| 1 | `displayedRefMode` lost its per-channel branch — absent means thick, full stop |
| 1 | `refModeOptions` collapsed to "pure-Messenger study → both modes, else encoded"; the per-destination type check was redundant |
| 1 | Read-side generation became a **plain default**, not a merge: `mergeLookupConfs`, `wouldGenerateAnything` and the button all deleted. A source with saved confs shows those; one without shows the generated ones. Nothing merges, no second copy in memory |
| 2 | Thin deleted from adopt too — literal, flag, validator, serialiser, fall-throughs (§2.2) |

---

## 4. Open items

1. **The merge review on PR #246 — unread.** This is the main task. Read it,
   act on it, reply per thread.
2. **Netlify.** Three `vlab-dashboard-frontend` checks report failure on the PR
   head. Established as *not* caused by this branch: `CI=true npx craco build`
   compiles clean locally, and the parallel `deploy/netlify` site builds the same
   commit successfully ("Deploy Preview ready!"). Points at that second site's
   own config (base directory or env vars). Needs Netlify access to read the
   build log. Independent of this PR's correctness.
3. **VIR-32** — the no-ad-provenance rate. Backlog, out of scope here.
4. **Deliberately out of scope**: the shared `TextInput`/`Select` render a
   `<label>` with no `htmlFor`, so `getByLabelText` does not work and component
   tests query by role/placeholder. A real accessibility gap, but fixing it
   touches every form in the app.

---

## 5. Verifying, and the traps in doing so

Dependencies are **not** shared between worktrees. This worktree already has
`dashboard/node_modules` and `adopt/.venv` installed; a fresh one will not.

```bash
cd /home/nandan/Documents/vlab-research/vlab-ref-mode-ux

# dashboard — 184 tests
cd dashboard && npx tsc --noEmit && CI=true npx craco test
# production build (CRA treats warnings as errors under CI=true)
CI=true npx craco build

# adopt — 721 tests, 1 skipped. Needs the test database.
cd ../adopt && make test-db && poetry run pytest . -q

# inference — all packages
cd ../inference && go vet ./... && go test ./...
```

Traps worth knowing:

- `poetry` picks Python 3.10 here; the system Python is 3.14 and the project
  requires `>=3.9,<3.11`. `poetry install` handles it.
- `make test-db` starts CockroachDB in a container and runs migrations. adopt's
  server tests and the ad-attributions tests need it.
- `go build ./swoosh/...` fails with "build output already exists and is a
  directory" — use `go vet` / `go test`, not `go build`, on that package.
- Some adopt tests are order-dependent; run the whole file rather than a single
  test when something looks odd.

**Last verified at `e0e38e98`:** dashboard 184 passed / `tsc` clean / production
build compiles; adopt 721 passed, 1 skipped; inference all packages pass,
`go vet` clean. GitHub CI green on `tests`, `CodeQL`, `Analyze (go/javascript/python)`.

---

## 6. Where the code lives

| Thing | Path |
|---|---|
| Ref mode (pure) | `dashboard/src/pages/StudyConfPage/forms/destinations/refMode.ts` |
| Ref mode (component) | `.../destinations/RefModeField.tsx`, rendered by `{Messenger,WhatsApp,Multi}.tsx` |
| New-conf defaults | `.../destinations/Destination.tsx` (`emptyStates`), `Destinations.tsx` (`initialState`) |
| Read-side defaults | `.../inferenceData/generateLookupConfs.ts`, consumed in `InferenceData.tsx` |
| Ad Attributions step | `.../forms/adAttributions/AdAttributions.tsx`, `hooks/useAdAttributions.tsx`, registered in `shared.ts` |
| Ref mode (model) | `adopt/adopt/study_conf.py` — `RefMode`, `RefModeDestination.resolved_ref_mode` |
| Save-time refusal | `adopt/adopt/study_conf.py` (`ref_mode_incoherence`), `adopt/adopt/server/server.py` |
| Ref serialisation | `adopt/adopt/marketing.py` — `messenger_ref`, `whatsapp_ref` |
| JSON + CSV export | `adopt/adopt/server/csv_export.py` (`ad_attributions_table` shares columns with the CSV) |
| Outcome classification | `inference/swoosh/inference_data.go` (`adAttributionOutcome`), `events.go` |

**Note on `shared.ts`:** its `confs` array doubles as the wizard's next-step
chain (`getNextConf`), so registering the Ad Attributions step changed where
Current Data advances to. Intended, and user-visible.
