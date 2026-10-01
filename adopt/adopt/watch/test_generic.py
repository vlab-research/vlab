"""Every check on a one-part study with no proposal, WhatsApp number, bails or
dinersclub, in a currency and timezone of its own: what it lacks is skipped."""

from datetime import datetime, timedelta, timezone

import pytest

from . import core
from .checks import CHECKS, providers

NOW = datetime.now(timezone.utc)


def ago(days):
    return (NOW - timedelta(days=days)).isoformat()


class FakeVlab:
    def get_confs(self, org, slug):
        assert slug == "solo"
        return {"general": {"ad_account": "9"},
                "recruitment": {"start_date": ago(20), "end_date": ago(-30),
                                "ad_campaign_name_base": "vlab-solo", "budget_per_arm": 900,
                                "destinations": ["Messenger"], "incentive_per_respondent": 1}}

    def current_data(self, org, slug):
        return [{"variable": "done", "timestamp": ago(0.5 + i % 5)} for i in range(40)]

    def meta_insights(self, org, **query):
        row = {"campaign_name": "vlab-solo-Messenger", "adset_id": "s1", "adset_name": "all",
               "ad_name": "a1", "date_start": ago(2)[:10], "spend": "40", "impressions": "900",
               "reach": "500", "frequency": "1.8"}
        return {"data": [row], "paging": {"truncated": False}, "account_id": "act_9",
                "timezone": "Asia/Kolkata", "currency": "INR"}

    def recruitment_stats(self, org, slug):
        return {"arm": {"total_cost": 200.0}}


def fly_get(*path, params=None):
    if path[-1] == "states":
        return {"total": 0, "states": []}
    raise AssertionError(f"read Fly {path} for a feature the study does not have")


def run(tmp_path, monkeypatch, **extra):
    cfg = {"study_dir": tmp_path, "vlab": {"org": "o"}, "pace": {"completion_ref": "done"},
           "parts": [{"vlab_slug": "solo", "survey_name": "Solo", "target": 100}], **extra}
    monkeypatch.setattr(core, "HISTORY", 0)
    monkeypatch.setattr("adopt.watch.io.vlab_client", FakeVlab)
    monkeypatch.setattr("adopt.watch.io.fly_get", fly_get)
    return {f.key: f for f in core.run(CHECKS, cfg, tmp_path, False, NOW)}


def test_a_bare_one_part_study_runs_every_check_and_skips_what_it_lacks(tmp_path, monkeypatch):
    found = run(tmp_path, monkeypatch)
    assert not [k for k in found if k.endswith("-error")], found
    assert {k: f.level for k, f in found.items()} == {
        "pace:solo": "ok", "payments:responding": "ok", "ads_budget:budget-per-arm": "ok",
        "ads_budget:fading": "ok", "ads_budget:frequency": "ok", "ads_budget:yesterday": "ok"}
    arm = found["ads_budget:budget-per-arm"].evidence["solo"]
    assert (arm["spent"], arm["budget"], arm["missing"]) == (200.0, 900, [])


def test_one_wallet_and_pay_forms_add_just_those_findings(tmp_path, monkeypatch):
    wallet = {"balance": 50.0, "currency": "EUR", "transfers": []}
    monkeypatch.setitem(providers.PROVIDERS, "reloadly", (lambda since: wallet, "SUCCESSFUL"))
    found = run(tmp_path, monkeypatch, providers={"wallets": ["reloadly"]},
                parts=[{"vlab_slug": "solo", "survey_name": "Solo", "target": 100,
                        "pay": ["pay"]}])
    assert {k for k in found if k.startswith(("payments", "providers"))} == {
        "payments:held", "payments:responding", "providers:runway:reloadly"}


@pytest.mark.parametrize("cfg,error", [
    ({"parts": [{"survey_name": "s"}]}, "needs vlab_slug"),
    ({"parts": [{"vlab_slug": "a", "survey_name": "s"}] * 2}, "two parts"),
    ({"parts": []}, "empty"),
    ({}, "parts"),
    ({"parts": [{"vlab_slug": "a", "survey_name": "s", "pay": "p1"}]}, "list"),
])
def test_parts_are_loud_when_wrong(cfg, error):
    with pytest.raises((KeyError, TypeError, ValueError), match=error):
        core.parts(cfg)
