"""The study watch: checks on a live study, with no LLM. See README.md.

    vlab watch <study_dir> [--only a,b] [--act] [--json]

A CHECK is a module in `checks/`, listed in `checks.CHECKS`, with:

    collect(cfg) -> dict
        All the IO. The runner adds `read_at` (the run's UTC time, ISO) and
        saves the result as a snapshot, <study>/data/watch/<check>/<UTC ts>.json,
        so it must be JSON-able (anything else is written with str()).
    check(cfg, snapshot, history) -> list[Finding]
        Pure. `history` is up to `HISTORY` earlier snapshots, newest first,
        not including `snapshot`. The snapshot is saved only once `check`
        returns; if it raises, it is kept as <UTC ts>.failed.json and never
        enters history, so the next run still sees that window.
    act(cfg, findings) -> list[Finding]        (optional)
        Runs only with --act, after `check`, given its findings. Returns the
        findings for what it did; they are reported after the check's own.

`cfg` is the whole watch.yaml plus `study_dir` (absolute Path). Each check
reads its own top-level section, named after the check, with
`core.settings(cfg, name, DEFAULTS)`, plus the shared keys (`vlab`,
`countries`); `core.utc` parses timestamps. An exception from collect, check
or act becomes an `unknown` finding for that check, and the other checks
still run.

Finding levels: ok (nothing to do), acted (code did something), decision
(needs a person), unknown (not recognised; never dropped). The run exits 1
if any finding is decision or unknown.
"""
