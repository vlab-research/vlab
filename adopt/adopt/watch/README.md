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

## Organisation

The watch lives in vlab because a study is vlab's unit: one study spans vlab
recruitment, Fly surveys, payment providers and a proposal. Servers own facts,
the watch owns policy: data that needs a privileged credential or is useful
beyond one study is an endpoint on the server that owns it (WhatsApp health on
Fly, Meta insights on the conf server), and checks read it over HTTP with
`FLY_API_KEY` and `VLAB_API_KEY`. Three stopgaps, each to move when its
condition arrives:

- `providers` is operator code (kubectl, provider keys) a researcher cannot
  run; it moves onto Fly's payment sub-bot endpoints when they exist.
- `io.fly_get`/`fly_post` are a minimal Fly client; if other vlab code needs
  Fly, make it a client in `adopt/sdk` beside `VlabClient`.
- `watch.yaml` sits in the study's `projects/` folder while agents run the
  watch locally; to run it unattended, it becomes a section of the vlab study
  conf, so the server can run it and the dashboard can show findings.

## Adding a check

Write `checks/<name>.py` with `collect`, `check` and optionally `act`, add it
to `CHECKS` in `checks/__init__.py`, and test `check` in `test_<name>.py`.

## Running from a checkout

The main checkout's venv works with `PYTHONPATH` at this checkout's `adopt/`:

    WT=/path/to/this/checkout/adopt VENV=/path/to/main/vlab/adopt/.venv
    cd $WT && PYTHONPATH=$WT $VENV/bin/python -m pytest adopt/watch -q
    PYTHONPATH=$WT $VENV/bin/vlab watch ../../projects/lac-healthy-diets

Not `python -m adopt.sdk.cli watch`: as `__main__` it never registers `watch`.

## payments and providers

Split by source so one failed read hides nothing else: `payments` reads Fly;
`providers` reads dinersclub (`kubectl logs`), DingConnect and Reloadly locally.
Bails and `withholding` lines are read over the last `window_hours`, at least
dean's re-drive interval; a run over that after the last good one reports the
unread stretch as `unknown`. Refusals count distinct respondents held on a pay
form over the whole window, so a pattern does not flicker between re-drives:
many failing one way is the form, pin or account (`decision`); a few refused
again and again is their line, which only a new number fixes (`ok`).

## pace

A complete is a user whose `pace.completion_ref` variable in vlab's current data
(the optimizer's view, one row per user per variable) is timestamped from
`count_from` on. vlab copies Fly's responses hourly (`source-fly` at :10,
`swoosh` at :30), so counts lag Fly by up to ~80 minutes; `strata_progress`
lags more, moving only when a plan runs. Current data keeps the answer, not the
form version, so a user who started a version older than `count_from` and
answered after it counts too. Pace is completes in
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
