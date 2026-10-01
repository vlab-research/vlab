# The study watch

Checks on a live study in plain Python, no LLM: a step that needs judgment is
a `decision` finding. Plan: `projects/watch/PLAN.md`; interface: `__init__.py`.

    vlab watch <study_dir> [--only a,b] [--act] [--json]

- **Config**: `<study_dir>/watch.yaml`. Shared keys (`vlab`, `countries`,
  `env_files`) plus one top-level section per check, named after it.
- **Data**, in `<study_dir>/data/watch/`: snapshots `<check>/<UTC ts>.json`
  (`.failed.json` if `check` raised: never read as history), and per run
  `findings-<UTC ts>.json` and `.md` and a `watch.log` line. **Snapshots can
  hold respondent data: never commit `data/`.**
- **Credentials**: `FLY_API_KEY`, `VLAB_API_KEY` (no Meta token) and provider
  keys, from the environment or the `.env` files `env_files` names.
- **Exit** 1 if any finding is `decision` or `unknown`. Read-only unless `--act`.

## Adding a check

Write `checks/<name>.py` with `collect`, `check` and optionally `act`, add it
to `CHECKS` in `checks/__init__.py`, and test `check` in `test_<name>.py`.

## Running from a checkout

The main checkout's venv works with `PYTHONPATH` at this checkout's `adopt/`:

    WT=/path/to/this/checkout/adopt VENV=/path/to/main/vlab/adopt/.venv
    cd $WT && PYTHONPATH=$WT $VENV/bin/python -m pytest adopt/watch -q
    PYTHONPATH=$WT $VENV/bin/vlab watch ../../projects/lac-healthy-diets

Not `python -m adopt.sdk.cli watch`: as `__main__` it never registers `watch`.

## payments

Bail events and dinersclub's `withholding` lines are read over the last
`window_hours`, at least dean's re-drive interval. Refusals are grouped by
distinct held respondents over that whole window, so a pattern does not flicker
between re-drives: many numbers failing one way is the form, pin or account
(`decision`); a few refused again and again is their line, which only a new
number fixes (`ok`). A run over `window_hours` after the last good one reports
the unread stretch as `unknown`. dinersclub (`kubectl logs`, one pod),
DingConnect and Reloadly are each read in one function until Fly serves them.

## pace

A complete is a user's first answer to `pace.completion_ref` on a questionnaire
version created from `count_from` on, read from Fly's filtered response stream
(vlab's `strata_progress` moves only when a plan runs). Pace is completes in
the last `window_hours`, never under 24: nights are silent, so a shorter window
extrapolates from silence or a burst.

## ads_budget

Projected = spent + remaining x (ad cost per complete over `cost_days` +
`incentive_usd`), against each proposal line; incentives spent is an estimate
(respondents on a pay, end or apology form x `incentive_usd`). `budget_per_arm`
must cover vlab's own spent plus remaining x (ad cost + `incentive_per_respondent`),
or adopt stops spending short of target; either missing is `unknown`. Meta days
are the ad account's: completes are dated in its timezone, and today, still
accruing, is in no window.
