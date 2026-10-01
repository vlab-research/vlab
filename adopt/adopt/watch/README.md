# The study watch

Checks on a live vlab study in plain Python, no LLM: a step that needs judgment
is a `decision` finding. Plan: `projects/watch/PLAN.md`; interface: `__init__.py`.

    vlab watch <study_dir> [--only a,b] [--act] [--json]

- **Config**: `<study_dir>/watch.yaml`, below. Shared keys (`vlab`, `parts`,
  `env_files`) plus one optional top-level section per check, named after it.
- **Data**, in `<study_dir>/data/watch/`: snapshots `<check>/<UTC ts>.json`
  (`.failed.json` if `check` raised: never read as history), and per run
  `findings-<UTC ts>.json` and `.md` and a `watch.log` line. **Snapshots can
  hold respondent data: never commit `data/`.**
- **Credentials**: `FLY_API_KEY`, `VLAB_API_KEY` (no Meta token) and provider
  keys, from the environment or the `.env` files `env_files` names.
- **Exit** 1 if any finding is `decision` or `unknown`. Read-only unless `--act`.

## watch.yaml

A study is one or more **parts**, each a vlab study and the Fly survey it
recruits to: one part for a simple study, one per country or site for a study
run as several vlab studies. A feature the config leaves out is skipped (no
`pay` forms: no held check; no `proposal`: no budget lines); config that is
present but wrong raises. Required keys are marked; the rest show defaults.

```yaml
vlab: {org: <uuid>}                     # required
env_files: [../keys/.env]               # KEY=VALUE files, relative to this dir
parts:                                  # required, at least one
  - vlab_slug: my-study                 # required
    survey_name: My Study               # required: the Fly survey
    name: my-study                      # in findings; defaults to vlab_slug
    target: 500                         # required here or in pace: completes wanted
    pay: [pay1]                         # Fly forms that pay
    after_pay: [end1]                   # forms reached once paid (incentive estimate)
    campaigns: [vlab-my-study]          # Meta campaign prefixes; default: vlab's
                                        #   ad_campaign_name_base
    incentive: 2.0                      # per complete; default: vlab's
                                        #   incentive_per_respondent
    # count_from, client_date: per-part overrides of pace's
pace:
  completion_ref: q_last                # required: vlab variable answered on completing
  count_from: null                      # count completes answered from this time
  client_date: null                     # the date promised to the client
  window_hours: 24                      # never fewer
  near_target_days: 1
  closing_hours: 24
payments:
  held_minutes: 30
  responding_minutes: 10
  window_hours: 6                       # bail lookback, at least dean's re-drive interval
  bail_prefix: null                     # the study's bails' names start with this
providers:
  wallets: []                           # among dingconnect, reloadly
  dinersclub: null                      # {namespace, deployment} to read refusals
  known_codes: []                       # dinersclub codes understood; others are unknown
  ref_prefixes: []                      # DingConnect refs checked for double payment
  pattern_min_users: 3
  runway_hours_min: 6
  rate_hours: 24
  window_hours: 6
number_health:
  phone_number_ids: []                  # WhatsApp numbers to read
  rules: {}                             # rating (GREEN, YELLOW, RED) -> study policy text
  recovered: ""                         # text for a confirmed return to GREEN
ads_budget:
  other_campaigns: []                   # prefixes of other studies sharing the ad account
  proposal: null                        # {path, currency, lines: {ads, incentives}, pooled}
  recent_days: 3
  baseline_days: 7
  fade_drop: 0.4
  min_impressions: 1000
  max_frequency: 2.0
  cost_days: 7
```

The ad account, its currency and timezone come from vlab and Meta; `end_date`,
`start_date` and `budget_per_arm` from each part's recruitment conf.

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
`test_generic.py` runs every check on a bare one-part study: a new check must
pass it, skipping what that study lacks.

## Running from a checkout

The main checkout's venv works with `PYTHONPATH` at this checkout's `adopt/`:

    WT=/path/to/this/checkout/adopt VENV=/path/to/main/vlab/adopt/.venv
    cd $WT && PYTHONPATH=$WT $VENV/bin/python -m pytest adopt/watch -q
    PYTHONPATH=$WT $VENV/bin/vlab watch <study_dir>

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

Amounts are in the ad account's currency. `budget_per_arm` must cover vlab's
own spent plus remaining x (ad cost per complete over `cost_days` +
`incentive_per_respondent`), or adopt stops spending short of target; either
missing is `unknown`. With a `proposal`, projected = spent + remaining x (ad
cost per complete + the part's `incentive`) is judged against each line;
incentives spent is an estimate (respondents on a `pay` or `after_pay` form x
`incentive`), and a proposal in another currency than the account is `unknown`.
Meta days are the ad account's: completes are dated in its timezone, and
today, still accruing, is in no window. All parts must share one ad account.
