from datetime import date, timedelta
from pathlib import Path

import pytest

from . import ads_budget as ab

TODAY = date(2026, 10, 1)
CONV = "onsite_conversion.messaging_conversation_started_7d"
CFG = {"ads_budget": {"countries": {"AR": {"campaigns": ["ar-"], "incentive_usd": 2.0},
                                    "HN": {"campaigns": ["hn-"], "incentive_usd": 8.0}}}}
S = ab.settings(CFG, ab.NAME, ab.DEFAULTS)


def day(n):
    """`n` days before TODAY, ISO."""
    return (TODAY - timedelta(days=n)).isoformat()


def ad_row(n, adset="s1", ad="a1", impressions=1000, conversations=10, campaign="ar-wa",
           country="AR", spend=1.0):
    return {"campaign_name": campaign, "adset_id": adset, "adset_name": f"name-{adset}",
            "ad_name": ad, "date": day(n), "spend": spend, "impressions": impressions,
            "conversations": conversations, "country": country}


def adset(adset_id, frequency, country="AR", spend=0.0):
    return {"adset_id": adset_id, "adset_name": f"name-{adset_id}", "campaign_name": "ar-wa",
            "reach": 1000, "frequency": frequency, "spend": spend, "country": country}


def snap(ad_days=None, adsets=None, ar_completes=500, lines=None, budget_per_arm=10_000,
         incentive=2.0):
    """AR and HN, target 750 each, $500 lifetime ad spend each. Over the last 7
    complete days each spent $70 on ads for 70 completes ($1 per complete)."""
    def country(completes):
        return {"completes": [day(1 + i % 7) for i in range(70)] + ["2026-09-01"] * (completes - 70),
                "target": 750, "paid": 600,
                "arm": {"budget_per_arm": budget_per_arm, "destinations": ["WhatsApp"],
                        "incentive_per_respondent": incentive, "vlab_spent": 1000.0}}

    return {
        "account": "act_1", "timezone": "Europe/Madrid", "currency": "USD", "today": TODAY.isoformat(),
        "adsets": adsets if adsets is not None else [
            adset("ar", 1.0, spend=500.0), adset("hn", 1.0, "HN", spend=500.0)],
        "ad_days": ad_days if ad_days is not None else [
            ad_row(n, adset=k, campaign=f"{k}-wa", country=k.upper(), spend=10.0)
            for n in range(1, 8) for k in ("ar", "hn")],
        "countries": {"AR": country(ar_completes), "HN": country(500)},
        "proposal": {"path": "p.yaml", "lines": lines or {"ads": 5000.0, "incentives": 9600.0}},
    }


def levels(findings):
    return {f.key: f.level for f in findings}


def test_shape_reads_numbers_conversations_and_country():
    row = {"campaign_name": "ar-wa", "date_start": "2026-09-30", "spend": "1.50",
           "impressions": "300", "reach": "250", "frequency": "1.2",
           "actions": [{"action_type": "link_click", "value": "9"},
                       {"action_type": CONV, "value": "4"}]}
    assert ab.shape(row, {"AR": ["ar-"]}) == {
        "campaign_name": "ar-wa", "country": "AR", "date": "2026-09-30", "spend": 1.5,
        "impressions": 300, "reach": 250, "frequency": 1.2, "conversations": 4}
    assert ab.shape({"campaign_name": "x"}, {"AR": ["ar-"]})["country"] is None


def test_proposal_lines_by_description_and_loud_when_missing():
    proposal = {"budget_line_items": [{"description": "Ads", "total_price": 5000.0},
                                      {"description": "Inc", "total_price": 9600.0}]}
    lines = {"ads": "Ads", "incentives": "Inc"}
    assert ab.proposal_lines(proposal, lines) == {"ads": 5000.0, "incentives": 9600.0}
    with pytest.raises(KeyError, match="Typo"):
        ab.proposal_lines(proposal, {**lines, "incentives": "Typo"})


# ---- budget ----------------------------------------------------------------

def test_within_budget_is_ok_with_the_projection():
    findings = ab.check(CFG, snap(), [])
    assert levels(findings) == {"ads_budget:budget-per-arm": "ok", "ads_budget:budget": "ok",
                                "ads_budget:fading": "ok", "ads_budget:frequency": "ok",
                                "ads_budget:yesterday": "ok"}
    [budget] = [f for f in findings if f.key == "ads_budget:budget"]
    ar = budget.evidence["countries"]["AR"]
    assert (ar["remaining"], ar["ad_cost_per_complete"]) == (250, 1.0)
    assert ar["projected_ads"] == 500 + 250
    assert ar["projected_incentives"] == 600 * 2.0 + 250 * 2.0
    assert budget.evidence["projected"] == {"ads": 1500.0, "incentives": 1700 + 6800}


def test_over_the_total_and_one_line_over_unless_pooled():
    assert levels(ab.check(CFG, snap(lines={"ads": 1000.0, "incentives": 5000.0}), []))[
        "ads_budget:over-total"] == "decision"
    lines = {"ads": 5000.0, "incentives": 8000.0}
    assert levels(ab.check(CFG, snap(lines=lines), []))["ads_budget:over-line:incentives"] == "decision"
    pooled = {"ads_budget": {**CFG["ads_budget"], "pooled": True}}
    assert levels(ab.check(pooled, snap(lines=lines), []))["ads_budget:budget"] == "ok"


def test_budget_per_arm_short_or_missing():
    # vlab_spent 1000 + 250 remaining x ($1 ads + $2 incentive) = 1750.
    [f] = [f for f in ab.check(CFG, snap(budget_per_arm=1700), []) if "arm" in f.key]
    assert f.level == "decision" and "AR" in f.summary and "HN" in f.summary
    assert levels(ab.check(CFG, snap(budget_per_arm=1750), []))["ads_budget:budget-per-arm"] == "ok"
    for missing in (snap(budget_per_arm=None), snap(incentive=None)):
        assert levels(ab.check(CFG, missing, []))["ads_budget:budget-per-arm"] == "unknown"


def test_a_country_past_target_needs_no_cost_per_complete():
    s = snap(ar_completes=800)
    s["countries"]["AR"]["completes"] = ["2026-09-01"] * 800
    [b] = [f for f in ab.check(CFG, s, []) if f.key == "ads_budget:budget"]
    assert b.evidence["countries"]["AR"]["projected_ads"] == 500


def test_no_recent_completes_to_price_by_is_unknown():
    s = snap()
    s["countries"]["HN"]["completes"] = ["2026-09-01"] * 500
    found = levels(ab.check(CFG, s, []))
    assert found["ads_budget:no-cost-per-complete"] == "unknown"
    assert "ads_budget:budget" not in found


def test_another_currency_is_unknown():
    assert levels(ab.check(CFG, {**snap(), "currency": "EUR"}, [])) == {"ads_budget:currency": "unknown"}


def test_a_campaign_matching_no_country_that_spent_is_unknown():
    s = snap()
    s["ad_days"] += [ad_row(2, campaign="Templates", country=None, spend=3.0),
                     ad_row(2, campaign="Paused", country=None, spend=0.0)]
    [f] = [f for f in ab.check(CFG, s, []) if f.key == "ads_budget:unmatched-campaigns"]
    assert f.level == "unknown" and f.evidence == {"spend": {"Templates": 3.0}}


# ---- ads -------------------------------------------------------------------

def steady(adset="s1", ad="a1", rate=10, days=range(1, 11), impressions=1000):
    return [ad_row(n, adset, ad, impressions, rate * impressions // 1000) for n in days]


def by_key(findings):
    return {f.key.split(":")[-1]: f for f in findings}


def test_fading_ad_sets_are_one_decision_with_the_numbers():
    rows = (steady(days=range(4, 11)) + steady(rate=4, days=range(1, 4))
            + steady("s2", days=range(4, 11)) + steady("s2", rate=7, days=range(1, 4)))
    f = by_key(ab.ad_findings(snap(rows), S, []))["fading"]
    assert f.level == "decision" and "ar-wa / name-s1" in f.summary
    assert f.evidence["days"]["recent"] == [day(3), day(2), day(1)]
    assert f.evidence["adsets"] == {"s1": {
        "campaign_name": "ar-wa", "adset_name": "name-s1", "recent": 4.0, "baseline": 10.0,
        "ads": {"a1": {"recent": 4.0, "baseline": 10.0}}}}
    quiet = steady(days=range(4, 11)) + steady(rate=0, days=range(1, 4), impressions=200)
    assert by_key(ab.ad_findings(snap(quiet), S, []))["fading"].level == "ok"


def test_todays_partial_day_is_left_out():
    rows = steady() + [ad_row(0, impressions=50_000, conversations=0, spend=99.0)]
    assert by_key(ab.ad_findings(snap(rows), S, []))["fading"].level == "ok"
    y = ab.yesterday(snap(rows))
    assert y.evidence["day"] == day(1)
    assert y.evidence["campaigns"] == {"ar-wa": {
        "spend": 1.0, "impressions": 1000, "conversations": 10,
        "per_1000": 10.0, "cost_per_conversation": 0.1}}


def test_frequency_is_a_decision_only_for_ad_sets_newly_over():
    rows = steady() + steady("s2") + steady("s3")
    old = snap(rows, [adset("s1", 2.4), adset("s2", 1.5), adset("gone", 3.1)])
    now = snap(rows, [adset("s1", 2.5), adset("s2", 2.1), adset("s3", 1.0), adset("gone", 3.1)])
    f = by_key(ab.ad_findings(now, S, [old]))["frequency"]
    # `gone` stopped delivering; s1 was over already.
    assert (f.level, f.evidence["new"], sorted(f.evidence["adsets"])) == ("decision", ["s2"], ["s1", "s2"])
    assert by_key(ab.ad_findings(now, S, [now]))["frequency"].level == "ok"


# ---- collect ---------------------------------------------------------------

class FakeClient:
    def __init__(self, accounts=("111", "111")):
        self.accounts, self.calls = list(accounts), []

    def get_confs(self, org, slug):
        return {"general": {"ad_account": self.accounts.pop(0), "credentials_key": "Facebook"},
                "recruitment": {"budget_per_arm": 2460, "destinations": ["WhatsApp"],
                                "incentive_per_respondent": 2.35}}

    def recruitment_stats(self, org, slug):
        return {"s1": {"total_cost": 100.0}, "s2": {"total_cost": 50.5}}

    def meta_insights(self, org, **q):
        self.calls.append(q)
        row = {"campaign_name": "ar-wa", "adset_id": "s1", "date_start": day(1), "spend": "2"}
        first = q["after"] is None
        return {"data": [row if first else {**row, "campaign_name": "other"}],
                "paging": {"truncated": first, "after": "C1"},
                "timezone": "America/Argentina/Buenos_Aires", "currency": "USD", "account_id": "act_111"}


def study(tmp_path):
    (tmp_path / "p.yaml").write_text("budget_line_items:\n  - {description: Ads, total_price: 5000}\n"
                                     "  - {description: Inc, total_price: 9600}\n")
    country = {"vlab_slug": "x", "survey_name": "X", "pay": ["pay"], "end": "end", "apology": "sorry"}
    return {"study_dir": Path(tmp_path), "vlab": {"org": "o"}, "pace": {"target": 750},
            "countries": {"AR": country, "HN": country},
            "ads_budget": {"proposal": "p.yaml", "lines": {"ads": "Ads", "incentives": "Inc"},
                           "countries": {"AR": {"campaigns": ["ar-"]}, "HN": {"campaigns": ["hn-"]}}}}


def test_collect_pages_tags_countries_and_dates_completes_in_the_account_timezone(monkeypatch, tmp_path):
    client = FakeClient()
    monkeypatch.setattr(ab.io, "vlab_client", lambda: client)
    monkeypatch.setattr(ab.io, "fly_get", lambda *path: {"summary": [
        {"current_form": "pay", "count": 5}, {"current_form": "end", "count": 2},
        {"current_form": "q", "count": 99}]})
    monkeypatch.setattr(ab.pace, "completes", lambda cfg, c: ["2026-09-30T02:00:00+00:00"])

    s = ab.collect(study(tmp_path))

    assert [(r["campaign_name"], r["country"]) for r in s["adsets"]] == [("ar-wa", "AR"), ("other", None)]
    assert s["countries"]["AR"] == {
        "completes": ["2026-09-29"], "target": 750, "paid": 7,
        "arm": {"budget_per_arm": 2460, "destinations": ["WhatsApp"],
                "incentive_per_respondent": 2.35, "vlab_spent": 150.5}}
    assert s["proposal"]["lines"] == {"ads": 5000.0, "incentives": 9600.0}
    assert {(q["level"], q.get("time_increment")) for q in client.calls} == {("adset", None), ("ad", "1")}
    assert all(q["account"] == "111" and q["credentials_key"] == "Facebook" for q in client.calls)


def test_collect_refuses_countries_on_different_ad_accounts(monkeypatch, tmp_path):
    monkeypatch.setattr(ab.io, "vlab_client", lambda: FakeClient(("111", "222")))
    with pytest.raises(ValueError, match="different ad accounts"):
        ab.collect(study(tmp_path))
