"""`vlab watch` -- run the study watch's checks on one study."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from ..sdk.cli import cli
from . import core
from .checks import CHECKS
from .io import load_env_files


def load_checks(study_dir: Path, names: List[str]) -> Dict[str, Any]:
    """Each entry a built-in check's name, or a study's own check module by its
    path from the study dir, named after the file."""
    out = {}
    for n in names:
        if n.endswith(".py"):
            path = (Path(study_dir) / n).resolve()
            spec = importlib.util.spec_from_file_location(f"watch_check_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            out[path.stem] = module
        elif n in CHECKS:
            out[n] = CHECKS[n]
        else:
            raise click.ClickException(f"watch.yaml checks: no check {n!r} (have: "
                                       f"{', '.join(CHECKS)}, or a path to a .py file)")
    return out


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
    available = load_checks(study_dir, cfg.get("checks") or list(CHECKS))
    names = [c.strip() for c in (only or "").split(",") if c.strip()] or list(available)
    missing = [c for c in names if c not in available]
    if missing:
        raise click.BadParameter(f"No such check: {', '.join(missing)} "
                                 f"(have: {', '.join(available)})", param_hint="--only")
    checks = {c: available[c] for c in names}
    now = datetime.now(timezone.utc)
    findings = core.run(checks, cfg, study_dir, act, now)
    title = f"Watch {study_dir.resolve().name} {now.strftime(core.TS)}"
    markdown = core.render_markdown(findings, title)
    core.write_report(study_dir, findings, markdown, list(checks), now)
    click.echo(core.to_json(findings) if as_json else markdown)
    raise SystemExit(core.exit_code(findings))
