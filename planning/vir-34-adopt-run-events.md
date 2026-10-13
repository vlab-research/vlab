# VIR-34: adopt errors reach the dashboard

**Status:** implemented on `fix/vir-34-adopt-errors-to-dashboard`. Not
released. Linear: VIR-34, "adopt errors never reach the dashboard —
study_run_events has one writer".

The behaviour now in the code is documented in `adopt/README.md`, "Study run
events". This file keeps the decisions, the discrepancies found along the way,
and the rollout.

## What the ticket asked for, and what was built

| Ticket item | Built |
|---|---|
| Wire adopt as an event source around the `except` in `malaria.py` | `run_updates` writes `run_started` / `run_ok` / `run_error` per study per run (`adopt/adopt/run_events.py`) |
| Fingerprint stable across runs | `<source>:run`, which contains no run id and no message text |
| Per-source recency window, about 3x the cron period | `run_events.recency_window`, applied by `server/db.py::open_errors` |
| Correct the docstring's cadence claim | `get_study_errors` docstring rewritten; all "90 minutes / 30-min swoosh" text in code, CLI help, MCP descriptions and docs updated |

## Decisions

1. **One source per job (`optimizer:ads`, `optimizer:audience`,
   `optimizer:recruitment_data`), not the ticket's `'optimizer'`.** The
   derivation groups by `(source, fingerprint)` and the latest event wins. With
   a single source, a clean recruitment-data run would close a failing ads run,
   and the three jobs run on different crons, which the per-source window needs
   to tell apart.
   *Alternative:* keep one source and put the job in the fingerprint. Rejected
   because the window is keyed by source, and the dashboard groups its list by
   source, so the job would then be invisible there.
2. **The window uses the slowest schedule in any committed values file.** The
   reader cannot see a deployment's cron. adopt-ads runs every 2h in prod and
   every 4h in staging and curiouslearning. A window sized for prod would
   flicker in the other two. A window sized for the slowest environment only
   lengthens how long a *silent* writer's last error stays open, because a fixed
   problem still closes on the next `run_ok`.
   *Alternatives:* inject each cron's schedule into its pod through the helm
   chart and write it into `details` (more moving parts, and every writer would
   need it); infer the period from gaps between `run_started` events (clever,
   fragile for new studies). Both are possible later without a schema change.
   A test parses `devops/values/*.yaml` so a slowed cron fails CI.
3. **The window is applied in Python rather than SQL.** The SQL returns each
   row's age by the database clock and bounds the scan by the widest window.
   That keeps the per-source rule a pure, unit-tested function, not a CASE
   expression built from a dict.
4. **Stage in the message.** `load` / `plan` / `execute` / `heal` becomes a
   short prefix ("Could not work out what to change on Facebook: …"), because a
   bare `KeyError: 'general'` in a banner means nothing on its own.
5. **`FacebookRequestError` is never stringified into an event.** Its `str()`
   includes request params, which can include the access token, and events are
   shown to everyone in the org. The event is built from Meta's error fields.
   The pod log line is unchanged and still uses `str()`. That is existing
   behaviour, and out of scope here.
6. **No schema change.** `source` is a free string and every other column
   already fits. No migration.

## Out of scope (follow-ups)

- **Log-only warnings**: `warn_on_incomplete_targeting`,
  `warn_on_thinned_ref_without_mapping`, unhealable ads in
  `heal_ad_attributions`, and failed respondents/cost reports. Surfacing them
  needs per-entity fingerprints (`optimizer:ads:targeting:<stratum>`, and so on)
  and threading an event sink into `update_ads_for_campaign`. The
  `missing_targeting_variables` and `thins_its_ref_without_reading_the_mapping`
  predicates are already pure, so the mapping is the easy half.
- **`plan_study` / Optimize-tab runs** write no events. They return the error
  to the caller. Their successes also do not write `run_ok`, so they cannot
  close a cron error early.
- **`adopt-heal-reports`** (daily) is not wired in. It has its own loop in
  `run_report_healing`.
- **Heartbeat sweep** (Phase 2 of the study-errors plan) is still unbuilt.

## Discrepancies found between docs and code

| Where | Said | Actually |
|---|---|---|
| `adopt/adopt/server/db.py` docstring, `mcp_tools.study_errors`, `cli.errors`, `documentation/agent-api.md` §6b table | swoosh runs every 30 minutes, so 90 min = 3 periods | swoosh is `30 * * * *`, i.e. hourly. 90 min was 1.5 periods |
| `documentation/agent-api.md` §2.3 | the derivation is at `db.py:18`; the writer is at `events.go:37` | line numbers had drifted. They are now referenced by name |
| `planning/study-errors-surfacing.md` (cited by the ticket, the code and docs) | a committed plan | exists only as an **untracked** file in the main `vlab` checkout. It is not on `origin/main`, so every reference to it is dangling for anyone else |
| `mcp_tools.py` "what refreshes what" comment | adopt-ads is two-hourly | true in `toixo-prod` only. It is four-hourly in staging and curiouslearning |

## Rollout

- Ships with the next adopt release (`scripts/release.sh adopt <next>`, then a
  values bump). The server (reader) and the crons (writers) use the same image.
- Deploying the reader alone is safe: existing `inference` rows get a 3h window
  instead of 90 min, so an unclosed swoosh error stays visible up to 90 minutes
  longer.
- The first adopt-ads run after the deploy writes a `run_error` for every study
  that currently fails. Expect the Errors tab to light up on studies whose
  errors have been invisible until now (e.g. `vl-pulse-nigeria-smoke`). That is
  the point of the change, not a regression.
- Write volume: 2 rows per active study per adopt run, at most three jobs.
  That is far below swoosh's hourly volume, and the table has a 90-day TTL.
- No migration.
