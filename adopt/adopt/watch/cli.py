"""`vlab watch` -- run the study watch's checks on one study."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from ..sdk.cli import cli
from . import core
from .checks import CHECKS
from .io import load_env_files


@cli.command("watch")
@click.argument("study_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--only", default=None, help="Comma-separated check names to run.")
@click.option("--act", is_flag=True, help="Let checks that can act do so.")
@click.option("--json", "as_json", is_flag=True, help="Print findings as JSON.")
def watch(study_dir: Path, only: Optional[str], act: bool, as_json: bool) -> None:
    """Run the study watch on STUDY_DIR (holding watch.yaml).

    Writes findings and snapshots under STUDY_DIR/data/watch/. Exits 1 if any
    finding needs a person (decision) or is not recognised (unknown).
    """
    cfg = core.load_config(study_dir)
    load_env_files(study_dir, cfg.get("env_files") or [])
    names = [c.strip() for c in (only or "").split(",") if c.strip()] or list(CHECKS)
    missing = [c for c in names if c not in CHECKS]
    if missing:
        raise click.BadParameter(f"No such check: {', '.join(missing)} "
                                 f"(have: {', '.join(CHECKS)})", param_hint="--only")
    checks = {c: CHECKS[c] for c in names}
    now = datetime.now(timezone.utc)
    findings = core.run(checks, cfg, study_dir, act, now)
    title = f"Watch {study_dir.resolve().name} {now.strftime(core.TS)}"
    markdown = core.render_markdown(findings, title)
    core.write_report(study_dir, findings, markdown, list(checks), now)
    click.echo(core.to_json(findings) if as_json else markdown)
    raise SystemExit(core.exit_code(findings))
