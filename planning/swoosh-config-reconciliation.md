# Swoosh config reconciliation — ignore events from removed sources (don't warn, don't delete)

**Status:** implemented in `inference/swoosh/` (`GetEvents` source filter + `swooshStudy` reorder).
**Related:** `planning/study-errors-surfacing.md` (the run-events log this stopped spamming), `planning/swoosh-per-study-isolation.md` (the `sIcNrF05`/`Fly` incident that first surfaced unmapped-source handling).

## The problem (OWIS Nigeria "zombie source")

Study `owis-nigeria-study` (`59c82a12-3737-4d8b-8656-6c2e2a8a7e8b`) showed a permanent warning banner:

> `data source not in SourceVariableMapping (skipped): Fly. Sources in mapping: [Fly HPV Double Fly HPV Triple]`

On **2026-07-13** the owner split the study's single data source **`Fly`** into two — **`Fly HPV Double`** and **`Fly HPV Triple`** (both `source: fly`, same `credentials_key: Fly`, differing by `survey_name`). The config (`data_sources` conf + `inference_data` mapping) is internally consistent and lists exactly those two.

But **52,090 historical `inference_data_events`** (2026-05-13 → 2026-07-13) are still tagged `source_name = 'Fly'`. No `Fly` key exists in the config anymore. `Reduce` treated any event whose source isn't in the mapping as an aggregated `extraction_warning` (fingerprint `inference:extraction:source=Fly`). Because swoosh re-scans those 52k rows **every hourly run**, the warning re-emitted every run and never aged out via the derivation's recency predicate — a permanent false alarm.

## The decision

**The current config is the authority on which sources a study cares about.** Deleting a source in the UI is a deliberate statement of intent: the study should no longer care about it — regardless of whether data is still arriving under that name. The old warning was **event-anchored** ("I found an event I can't place → warn"); it should be **config-anchored** ("do I have a source I expected to process?").

So: **ignore events from sources absent from the current config, at the read boundary. Do not warn, and do not delete the data.**

### Why ignore, not delete

- **Non-destructive.** Once the upstream survey source is deleted, the vlab `inference_data_events` copy is the *only* surviving record of those responses. "It's just a cache, deleting is safe" holds only while the upstream exists; here it doesn't.
- **Reversible.** Re-adding the source to the conf lights its history straight back up — no restore, no re-pull (which is impossible anyway once upstream is gone).
- **Matches the surrounding architecture.** `study_run_events` is event-sourced: append-only, immutable facts, derive the current view. Deleting underlying event data to fix a *surfacing* problem cuts against that grain. Reconcile the **view**, not the **facts**.
- **Blast radius.** An auto-delete driven by config state is the same class of mechanism as the `connector_runs` misfire (commit `999b09d1`, 116 studies pulled into collection) — but irreversible. A bad/empty latest conf could wipe wanted data. Filtering at read time has none of that risk.

### Why filter at the read boundary (not just suppress the warning in `Reduce`)

Filtering in `GetEvents` gets the same "don't warn" outcome **and** stops swoosh from reading + iterating the dead rows every run. Fully reversible, no schema change, no destructive op.

## The change

`inference/swoosh/swoosh.go`:

1. `GetEvents(pool, study, sources []string)` — added `AND source_name = ANY($2)`. `source_name` is part of the `inference_data_events` primary key, so this is a cheap residual filter on the existing per-study scan.
2. `swooshStudy` — load `GetInferenceDataConf` **before** `GetEvents`, then `GetEvents(pool, study, mapping.Sources())`. (No conf → skip, as before; now we also skip the event read entirely.)

`Reduce`'s unmapped-source skip branch (`inference-data/…`) is left intact as defense-in-depth — in prod it is now unreachable because only configured sources are ever loaded. The two unit tests that assert on that warning call `Reduce` directly, so they still exercise (and pass) it.

## What this deliberately does NOT do

- **Does not delete the 52,090 `Fly` rows.** They sit inert; they return automatically if `Fly` is ever re-added to the conf.
- **Does not catch a *genuine* mis-map** ("a source the owner still has in config is silently getting no data" — the real `sIcNrF05` failure). That detection belongs on the config side (a configured source producing zero rows) and is future work — Phase 2 heartbeat territory in `study-errors-surfacing.md`. Flipping the anchor here does not regress it, because that case was never reliably caught by the event-anchored warning either.

## Release

Standard swoosh release per `planning/release-process.md`: `go vet ./swoosh/... && go test ./swoosh/...` → `scripts/release.sh swoosh <next>` (tag → push → verify image in GHCR) → bump `devops/values/*.yaml` → `helm upgrade`. Confirm the next scheduled run for OWIS Nigeria emits `run_started`/`run_ok` with **no** `extraction_warning` for `source=Fly`.
