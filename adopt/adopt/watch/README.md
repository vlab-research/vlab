# The study watch

Checks on a live survey study (the messaging number, recruitment pace,
payments, ads and budget) in plain Python, with no LLM. A step that needs
judgment is reported as a `decision` finding, not decided. The plan is
`projects/watch/PLAN.md`; the check interface is in `__init__.py`.

    vlab watch <study_dir> [--only a,b] [--act] [--json]

- **Config**: `<study_dir>/watch.yaml`. Shared keys (`vlab`, `countries`,
  `env_files`) plus one top-level section per check, named after it.
- **Data**: `<study_dir>/data/watch/`: `<check>/<UTC ts>.json` snapshots,
  `<check>/<UTC ts>.failed.json` when `check` raised (not read as history),
  `findings-<UTC ts>.json` and `.md` per run, and `watch.log`, one line per run.
  **Snapshots can hold respondent data: never commit `data/`.**
- **Credentials** come from the environment: a Fly key (`FLY_API_KEY`) and a
  vlab key (`VLAB_API_KEY`), no Meta token, plus provider keys from the
  `.env` files `env_files` names. A missing one raises, naming it.
- **Exit code**: 1 if any finding is `decision` or `unknown`, else 0.
- Read-only unless `--act`, which only checks with an `act` honour.

## Adding a check

Write `checks/<name>.py` with `collect`, `check` and optionally `act` (see
`__init__.py`), add it to `CHECKS` in `checks/__init__.py`, and test `check`
on saved snapshots in a colocated `test_<name>.py`.

## Running from a checkout

The main checkout's venv works if `PYTHONPATH` points at this checkout's
`adopt/`, so that it imports this code rather than its own:

    WT=/path/to/this/checkout/adopt
    VENV=/home/nandan/Documents/vlab-research/vlab/adopt/.venv
    cd $WT && PYTHONPATH=$WT $VENV/bin/python -m pytest adopt/watch -q
    PYTHONPATH=$WT $VENV/bin/vlab watch ../../projects/lac-healthy-diets

`python -m adopt.sdk.cli watch` does not work: run as `__main__`, the CLI
module is a second copy that the `watch` command never registered on.

## payments

Read-only. Bail events and dinersclub's `withholding` lines are read over the
last `window_hours`; refusals are grouped by distinct respondents over that
whole window, so a pattern does not flicker between dean's re-drives. A run
more than `window_hours` after the last good one reports the unread stretch as
`unknown`. dinersclub, DingConnect and Reloadly are each read in one function
until Fly serves them.

## pace

A complete is a user's first answer to `pace.completion_ref` on a questionnaire
version created from `count_from` on, read from Fly's response stream (vlab's
`strata_progress` only moves when a plan runs). Pace is completes in the last
`window_hours`, never under 24: nights are silent, so a shorter window
extrapolates from silence or a burst. `completes()` is shared with ads_budget.

## ads_budget

Projected = spent + remaining x (ad cost per complete over `cost_days` +
`incentive_usd`), against each proposal line; incentives spent is an estimate
(respondents on a pay, end or apology form x `incentive_usd`). `budget_per_arm`
must cover vlab's own spent plus remaining x (ad cost + `incentive_per_respondent`),
or adopt stops spending short of target. Meta days are the ad account's: completes
are dated in its timezone, and today, still accruing, is in no window.
