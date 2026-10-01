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
