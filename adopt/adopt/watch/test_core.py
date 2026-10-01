import json
from datetime import datetime, timedelta, timezone
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


def test_render_orders_unknown_first_and_handles_empty():
    md = core.render_markdown([Finding("a", "ok", "a:1", "fine"),
                               Finding("b", "unknown", "b:1", "odd")])
    assert md.index("## unknown") < md.index("## ok")
    assert "- **b** odd `b:1`" in md
    assert "No findings." in core.render_markdown([])


def test_snapshot_round_trip_and_history_order(tmp_path):
    for i in range(3):
        core.save_snapshot(tmp_path, "c", {"i": i}, NOW + timedelta(hours=i))
    last = core.save_snapshot(tmp_path, "c", {"i": 3}, NOW + timedelta(hours=3))
    assert core.load_history(tmp_path, "c", 10, before=last.name) == [
        {"i": 2}, {"i": 1}, {"i": 0}]
    assert core.load_history(tmp_path, "c", 1, before=last.name) == [{"i": 2}]


def test_run_check_passes_earlier_snapshots_only(tmp_path):
    core.run_check("c", fake("c"), {}, tmp_path, False, NOW)
    [f] = core.run_check("c", fake("c"), {}, tmp_path, False, NOW + timedelta(hours=1))
    assert f.evidence["history"] == [{"n": 1}]


def test_raising_check_is_unknown_and_others_still_run(tmp_path):
    checks = {"bad": fake("bad", collect=boom), "good": fake("good")}
    findings = core.run(checks, {}, tmp_path, False, NOW)
    assert [(f.check, f.level) for f in findings] == [("bad", "unknown"), ("good", "ok")]
    assert findings[0].key == "bad:collect-error"
    assert "no network" in findings[0].summary


def test_check_returning_wrong_type_is_unknown(tmp_path):
    mod = SimpleNamespace(collect=lambda cfg: {}, check=lambda c, s, h: None)
    [f] = core.run_check("c", mod, {}, tmp_path, False, NOW)
    assert (f.level, f.key) == ("unknown", "c:check-error")


def test_act_only_with_flag_and_its_error_keeps_check_findings(tmp_path):
    acted = Finding("p", "acted", "p:paid", "paid 3")
    mod = fake("p", level="decision", act=lambda cfg, fs: [acted])
    assert [f.level for f in core.run_check("p", mod, {}, tmp_path, False, NOW)] == ["decision"]
    assert core.run_check("p", mod, {}, tmp_path, True, NOW)[1] == acted
    mod.act = lambda cfg, fs: boom(cfg)
    assert [f.level for f in core.run_check("p", mod, {}, tmp_path, True, NOW)] == [
        "decision", "unknown"]


def test_select():
    checks = {"a": 1, "b": 2}
    assert core.select(checks, None) == checks
    assert core.select(checks, ["b"]) == {"b": 2}
    with pytest.raises(KeyError, match="nope"):
        core.select(checks, ["nope"])


def test_need():
    assert core.need({"a": {"b": 1}}, "a.b") == 1
    with pytest.raises(KeyError, match="a.c"):
        core.need({"a": {"b": 1}}, "a.c")


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
