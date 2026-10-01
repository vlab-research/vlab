import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from . import core
from .core import Finding

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def fake(name, level="ok", collect=None, act=None):
    """A check module that reports how much history it saw."""
    def check(cfg, snapshot, history):
        return [Finding(name, level, f"{name}:k", "s",
                        {"snapshot": snapshot, "history": history})]
    mod = SimpleNamespace(collect=collect or (lambda cfg: {"n": 1}), check=check)
    if act:
        mod.act = act
    return mod


def boom(cfg):
    raise RuntimeError("no network")


def test_finding_rejects_unknown_level():
    with pytest.raises(ValueError):
        Finding("c", "warning", "k", "s")


@pytest.mark.parametrize("levels,code", [
    ([], 0), (["ok", "acted"], 0), (["ok", "decision"], 1), (["unknown"], 1)])
def test_exit_code(levels, code):
    assert core.exit_code([Finding("c", lv, "k", "s") for lv in levels]) == code


def test_render_puts_unknown_first_and_collapses_ok():
    md = core.render_markdown([Finding("a", "ok", "a:1", "fine"),
                               Finding("c", "ok", "c:1", "also fine"),
                               Finding("d", "decision", "d:1", "choose"),
                               Finding("b", "unknown", "b:1", "odd")])
    assert md.index("## unknown") < md.index("## decision") < md.index("ok: 2")
    assert "- **b** odd `b:1`" in md
    assert "ok: 2 — a: fine; c: also fine" in md and "## ok" not in md
    assert "No findings." in core.render_markdown([])


def test_snapshot_round_trip_and_history_order(tmp_path):
    for i in range(4):
        core.save_snapshot(tmp_path, "c", {"i": i}, NOW + timedelta(hours=i))
    core.save_snapshot(tmp_path, "c", {"i": "bad"}, NOW + timedelta(hours=2, minutes=30),
                       failed=True)
    last = NOW + timedelta(hours=3)
    assert core.load_history(tmp_path, "c", 10, before=last) == [
        {"i": 2}, {"i": 1}, {"i": 0}]
    assert core.load_history(tmp_path, "c", 1, before=last) == [{"i": 2}]


def test_a_raising_check_keeps_its_window_for_the_next_run(tmp_path):
    core.run_check("c", fake("c"), {}, tmp_path, False, NOW)
    bad = SimpleNamespace(collect=lambda cfg: {"n": 2}, check=lambda c, s, h: boom(c))
    [f] = core.run_check("c", bad, {}, tmp_path, False, NOW + timedelta(hours=1))
    assert (f.level, f.key) == ("unknown", "c:check-error")
    files = sorted(p.name for p in (tmp_path / "data" / "watch" / "c").iterdir())
    assert files == ["20260930T120000Z.json", "20260930T130000Z.failed.json"]
    [f] = core.run_check("c", fake("c"), {}, tmp_path, False, NOW + timedelta(hours=2))
    assert f.evidence["history"] == [{"n": 1, "read_at": NOW.isoformat()}]
    assert f.evidence["snapshot"]["read_at"] == (NOW + timedelta(hours=2)).isoformat()


def test_bad_collect_or_check_is_unknown_and_others_still_run(tmp_path):
    checks = {"down": fake("down", collect=boom), "list": fake("list", collect=lambda cfg: [1]),
              "none": SimpleNamespace(collect=lambda cfg: {}, check=lambda c, s, h: None),
              "good": fake("good")}
    findings = core.run(checks, {}, tmp_path, False, NOW)
    assert [(f.key, f.level) for f in findings] == [
        ("down:collect-error", "unknown"), ("list:collect-error", "unknown"),
        ("none:check-error", "unknown"), ("good:k", "ok")]
    assert "no network" in findings[0].summary
    assert not (tmp_path / "data" / "watch" / "down").exists()


def test_act_only_with_flag_and_its_error_keeps_check_findings(tmp_path):
    acted = Finding("p", "acted", "p:paid", "paid 3")
    mod = fake("p", level="decision", act=lambda cfg, fs: [acted])
    assert [f.level for f in core.run_check("p", mod, {}, tmp_path, False, NOW)] == ["decision"]
    assert core.run_check("p", mod, {}, tmp_path, True, NOW)[1] == acted
    mod.act = lambda cfg, fs: boom(cfg)
    assert [f.level for f in core.run_check("p", mod, {}, tmp_path, True, NOW)] == [
        "decision", "unknown"]


@pytest.mark.parametrize("value,expected", [
    ("2026-09-30 12:00:00+00", NOW),
    ("2026-09-30T09:00:00-03:00", NOW),
    ("2026-09-30T12:00:00", NOW),
    ("2026-09-30T12:00:00.123456789Z", NOW.replace(microsecond=123456)),
    ("2026-09-30", NOW.replace(hour=0)),
    (None, None),
])
def test_utc(value, expected):
    got = core.utc(value)
    assert got == expected and (got is None or got.tzinfo == timezone.utc)


def test_utc_end_of_day_and_bad_input():
    assert core.utc("2026-09-30", end_of_day=True) == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert core.utc(NOW.isoformat(), end_of_day=True) == NOW
    with pytest.raises(ValueError):
        core.utc("yesterday")


def test_need_and_settings():
    assert core.need({"a": {"b": 1}}, "a.b") == 1
    with pytest.raises(KeyError, match="a.c"):
        core.need({"a": {"b": 1}}, "a.c")
    defaults = {"a": 1, "b": 2}
    assert core.settings({"c": {"b": 3, "x": 4}}, "c", defaults) == {"a": 1, "b": 3, "x": 4}
    assert core.settings({"c": None}, "c", defaults) == defaults
    with pytest.raises(TypeError, match="'c'"):
        core.settings({"c": [1]}, "c", defaults)


def test_load_config_adds_absolute_study_dir(tmp_path, monkeypatch):
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "watch.yaml").write_text("vlab: {org: x}\n")
    monkeypatch.chdir(tmp_path)
    assert core.load_config(Path("s")) == {"vlab": {"org": "x"}, "study_dir": tmp_path / "s"}
    (tmp_path / "s" / "watch.yaml").write_text("study_dir: elsewhere\n")
    with pytest.raises(ValueError):
        core.load_config(Path("s"))


def test_cli_only_writes_report_and_exits_on_findings(tmp_path, monkeypatch):
    from ..sdk.cli import cli
    from . import cli as watch_cli

    (tmp_path / "watch.yaml").write_text("vlab: {org: x}\n")
    monkeypatch.setattr(watch_cli, "CHECKS", {"a": fake("a"), "b": fake("b", "decision")})
    runner = CliRunner()

    r = runner.invoke(cli, ["watch", str(tmp_path), "--only", "a", "--json"])
    assert r.exit_code == 0, r.output
    assert [f["check"] for f in json.loads(r.output)] == ["a"]
    assert runner.invoke(cli, ["watch", str(tmp_path)]).exit_code == 1
    assert runner.invoke(cli, ["watch", str(tmp_path), "--only", "zz"]).exit_code == 2

    out = tmp_path / "data" / "watch"
    assert len(list(out.glob("findings-*.json"))) >= 1
    log = (out / "watch.log").read_text().splitlines()
    assert len(log) == 2 and "checks=a" in log[0] and "decision=1" in log[1]


def test_cli_runs_the_checks_watch_yaml_names_including_a_studys_own(tmp_path):
    from ..sdk.cli import cli

    (tmp_path / "mine.py").write_text(
        "from adopt.watch.core import Finding\n"
        "def collect(cfg):\n    return {}\n"
        "def check(cfg, snapshot, history):\n    return [Finding('mine', 'ok', 'mine:k', 's')]\n")
    (tmp_path / "watch.yaml").write_text("vlab: {org: x}\nchecks: [./mine.py]\n")
    r = CliRunner().invoke(cli, ["watch", str(tmp_path), "--json"])
    assert r.exit_code == 0, r.output
    assert [f["key"] for f in json.loads(r.output)] == ["mine:k"]
    (tmp_path / "watch.yaml").write_text("vlab: {org: x}\nchecks: [nope]\n")
    assert CliRunner().invoke(cli, ["watch", str(tmp_path)]).exit_code == 1
