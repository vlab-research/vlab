"""Findings, the study file, snapshots and the report. IO is confined to the
load/save functions; everything else is pure."""

from __future__ import annotations

import json
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional, Sequence

import yaml

LEVELS = ("ok", "acted", "decision", "unknown")
ALERTING = ("decision", "unknown")
HISTORY = 24
TS = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True)
class Finding:
    check: str
    level: str
    key: str
    summary: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level not in LEVELS:
            raise ValueError(f"Finding level {self.level!r} is not one of {LEVELS}")


def need(cfg: Mapping[str, Any], dotted: str) -> Any:
    """`cfg["a"]["b"]` for "a.b", raising with the missing key's full name."""
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            raise KeyError(f"watch.yaml has no {dotted!r}")
        node = node[part]
    return node


def settings(cfg: Mapping[str, Any], name: str, defaults: Mapping[str, Any]) -> Dict[str, Any]:
    """The check's own watch.yaml section over its defaults; no section means
    all defaults."""
    section = cfg.get(name) or {}
    if not isinstance(section, Mapping):
        raise TypeError(f"watch.yaml {name!r} must be a mapping, got {section!r:.100}")
    return {**defaults, **section}


def utc(value: Any, end_of_day: bool = False) -> Optional[datetime]:
    """An aware UTC datetime from an ISO 8601 string, datetime or date; None
    for None or "". Naive values are UTC. A bare date is that day's midnight,
    or the next day's with `end_of_day` (so a deadline date includes the day)."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = date.fromisoformat(value) if len(value) == 10 else datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day) + timedelta(days=end_of_day)
    return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)


def watch_dir(study_dir: Path) -> Path:
    return Path(study_dir) / "data" / "watch"


def load_config(study_dir: Path) -> Dict[str, Any]:
    """watch.yaml, plus `study_dir` (absolute) for resolving relative paths."""
    path = Path(study_dir) / "watch.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"No watch.yaml in {study_dir}")
    cfg = yaml.safe_load(path.read_text()) or {}
    if not isinstance(cfg, dict) or "study_dir" in cfg:
        raise ValueError(f"{path} must be a mapping without a 'study_dir' key")
    return {**cfg, "study_dir": Path(study_dir).resolve()}


def save_snapshot(study_dir: Path, check: str, snapshot: dict, now: datetime,
                  failed: bool = False) -> Path:
    """`<ts>.json`, or `<ts>.failed.json` when `check` raised on it: kept to
    debug with, never read back as history."""
    suffix = ".failed.json" if failed else ".json"
    path = watch_dir(study_dir) / check / f"{now.strftime(TS)}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=1, default=str))
    return path


def load_history(study_dir: Path, check: str, n: int, before: datetime) -> List[dict]:
    """The last `n` good snapshots taken before `before`, newest first."""
    files = sorted((watch_dir(study_dir) / check).glob("*.json"), reverse=True)
    good = [f for f in files
            if not f.name.endswith(".failed.json") and f.stem < before.strftime(TS)]
    return [json.loads(f.read_text()) for f in good[:n]]


def select(checks: Mapping[str, ModuleType], only: Optional[Sequence[str]]) -> dict:
    if not only:
        return dict(checks)
    missing = [c for c in only if c not in checks]
    if missing:
        raise KeyError(f"No such check: {', '.join(missing)} (have: {', '.join(checks)})")
    return {c: checks[c] for c in only}


def _error(check: str, stage: str, e: Exception) -> Finding:
    return Finding(check, "unknown", f"{check}:{stage}-error",
                   f"{stage} raised {type(e).__name__}: {e}",
                   {"traceback": traceback.format_exc()})


def _findings(check: str, result: Any) -> List[Finding]:
    if not isinstance(result, list) or not all(isinstance(f, Finding) for f in result):
        raise TypeError(f"{check} must return a list of Finding, got {result!r:.200}")
    return result


def run_check(name: str, module: Any, cfg: dict, study_dir: Path, act: bool,
              now: datetime) -> List[Finding]:
    """The snapshot is saved only after `check` returns, so a failed check's
    window stays unread and is reported by the next run's history."""
    try:
        history = load_history(study_dir, name, HISTORY, before=now)
        snapshot = module.collect(cfg)
        if not isinstance(snapshot, dict):
            raise TypeError(f"{name}.collect must return a dict, got {snapshot!r:.200}")
        snapshot = {**snapshot, "read_at": now.isoformat()}
    except Exception as e:
        return [_error(name, "collect", e)]
    try:
        findings = _findings(name, module.check(cfg, snapshot, history))
    except Exception as e:
        save_snapshot(study_dir, name, snapshot, now, failed=True)
        return [_error(name, "check", e)]
    save_snapshot(study_dir, name, snapshot, now)
    if act and hasattr(module, "act"):
        try:
            findings = findings + _findings(name, module.act(cfg, findings))
        except Exception as e:
            findings = findings + [_error(name, "act", e)]
    return findings


def run(checks: Mapping[str, Any], cfg: dict, study_dir: Path, act: bool,
        now: datetime) -> List[Finding]:
    return [f for name, module in checks.items()
            for f in run_check(name, module, cfg, study_dir, act, now)]


def exit_code(findings: Sequence[Finding]) -> int:
    return 1 if any(f.level in ALERTING for f in findings) else 0


def counts(findings: Sequence[Finding]) -> Dict[str, int]:
    return {level: sum(f.level == level for f in findings) for level in LEVELS}


def render_markdown(findings: Sequence[Finding], title: str = "Watch") -> str:
    lines = [f"# {title}", ""]
    if not findings:
        return "\n".join(lines + ["No findings.", ""])
    for level in ("unknown", "decision", "acted"):
        group = [f for f in findings if f.level == level]
        if group:
            lines += [f"## {level} ({len(group)})", ""]
            lines += [f"- **{f.check}** {f.summary} `{f.key}`" for f in group]
            lines.append("")
    ok = [f for f in findings if f.level == "ok"]
    if ok:
        lines += [f"ok: {len(ok)} — " + "; ".join(f"{f.check}: {f.summary}" for f in ok), ""]
    return "\n".join(lines)


def to_json(findings: Sequence[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=1, default=str)


def write_report(study_dir: Path, findings: Sequence[Finding], markdown: str,
                 checks: Sequence[str], now: datetime) -> Path:
    out = watch_dir(study_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"findings-{now.strftime(TS)}"
    stem.with_suffix(".json").write_text(to_json(findings))
    stem.with_suffix(".md").write_text(markdown)
    tally = " ".join(f"{k}={v}" for k, v in counts(findings).items())
    with open(out / "watch.log", "a") as fh:
        fh.write(f"{now.strftime(TS)} {tally} checks={','.join(checks) or '-'}\n")
    return stem
