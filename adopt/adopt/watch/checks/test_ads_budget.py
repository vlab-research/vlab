from datetime import date, timedelta

import pytest

from . import ads_budget as ab

TODAY = date(2026, 10, 1)
CONV = "onsite_conversion.messaging_conversation_started_7d"


def day(n):
    """`n` days before TODAY, ISO."""
    return (TODAY - timedelta(days=n)).isoformat()


def cfg(**over):
    sec = {
        "countries": {"AR": {"campaigns": ["ar-"], "incentive_usd": 2.0},
                      "HN": {"campaigns": ["hn-"], "incentive_usd": 8.0}},
        **over,
    }
    return {"ads_budget": sec}


def ad_row(n, adset="s1", ad="a1", impressions=1000, conversations=10, campaign="ar-wa"):
    return {"campaign_name": campaign, "campaign_id": "c1", "adset_id": adset,
            "adset_name": f"name-{adset}", "ad_id": ad, "ad_name": ad, "date": day(n),
            "spend": 1.0, "impressions": impressions, "reach": impressions, "frequency": 1.0,
            "ctr": 1.0, "conversations": conversations, "country": "AR"}


def snap(ad_days=(), adsets=(), ar_spent=500.0, hn_spent=500.0, ar_completes=500,
         hn_completes=500, ar_paid=600, hn_paid=600, lines=None, budget_per_arm=10_000,
         campaign_days=None):
    """Two countries, target 750 each. Over the last 7 complete days each
    country spent $70 on ads for 70 completes ($1 per complete)."""
    def country(completes, paid):
        # 70 completes in the 7-day cost window, the rest long before.
        return {"completes": [day(1 + i % 7) for i in range(70)]
                + ["2026-09-01"] * (completes - 70),
                "target": 750, "paid": paid,
                "arm": {"budget_per_arm": budget_per_arm, "destinations": ["WhatsApp"],
                        "incentive_per_respondent": 2.0, "vlab_spent": 1000.0}}

    def cday(n, campaign, country):
        return {"campaign_name": campaign, "campaign_id": campaign, "date": day(n),
                "spend": 10.0, "impressions": 2000, "reach": 1500, "ctr": 1.2,
                "conversations": 20, "frequency": 1.3, "country": country}

    days = campaign_days if campaign_days is not None else [
        cday(n, c, k) for n in range(1, 8) for c, k in (("ar-wa", "AR"), ("hn-wa", "HN"))]
    ar = country(ar_completes, ar_paid)
    hn = country(hn_completes, hn_paid)
    return {
        "account": "act_1", "timezone": "Europe/Madrid", "currency": "USD",
        "today": TODAY.isoformat(),
        "campaign_totals": [
            {"campaign_name": "ar-wa", "spend": ar_spent, "country": "AR"},
            {"campaign_name": "hn-wa", "spend": hn_spent, "country": "HN"}],
        "campaign_days": days,
        "ad_days": list(ad_days),
        "adsets": list(adsets),
        "countries": {"AR": ar, "HN": hn},
        "proposal": {"path": "p.yaml", "lines": lines or {"ads": 5000.0, "incentives": 9600.0}},
    }


def levels(findings):
    return {f.key: f.level for f in findings}


# ---- shaping ---------------------------------------------------------------

def test_shape_reads_numbers_and_pulls_conversations_out_of_actions():
    row = {"campaign_id": "1", "campaign_name": "ar-wa", "date_start": "2026-09-30",
           "spend": "1.50", "impressions": "300", "reach": "250", "frequency": "1.2",
           "ctr": "0.8", "actions": [{"action_type": "link_click", "value": "9"},
                                     {"action_type": CONV, "value": "4"}]}
    out = ab.shape(row)
    assert out == {"campaign_id": "1", "campaign_name": "ar-wa", "date": "2026-09-30",
                   "spend": 1.5, "impressions": 300, "reach": 250, "frequency": 1.2,
                   "ctr": 0.8, "conversations": 4}
    assert ab.shape({"campaign_name": "x"})["conversations"] == 0


def test_country_of_matches_name_prefixes_only():
    prefixes = {"AR": ["vlab-lac-hd-argentina", "vlab-lac-healthy-diets-argentina"]}
    assert ab.country_of("vlab-lac-hd-argentina-channel-Messenger", prefixes) == "AR"
    assert ab.country_of("Templates - LAC Healthy Diets", prefixes) is None


def test_proposal_lines_by_description_and_loud_when_missing():
    proposal = {"budget_line_items": [
        {"description": "Facebook Ad Costs", "total_price": 5000.0},
        {"description": "Respondent Incentives", "total_price": 9600.0}]}
    lines = {"ads": "Facebook Ad Costs", "incentives": "Respondent Incentives"}
    assert ab.proposal_lines(proposal, lines) == {"ads": 5000.0, "incentives": 9600.0}
    with pytest.raises(KeyError, match="Incentives Typo"):
        ab.proposal_lines(proposal, {**lines, "incentives": "Incentives Typo"})
    with pytest.raises(KeyError, match="exactly ads and incentives"):
        ab.proposal_lines(proposal, {"ads": "Facebook Ad Costs"})


# ---- budget ----------------------------------------------------------------

def test_within_budget_is_ok_with_the_projection():
    findings = ab.check(cfg(), snap(), [])
    assert levels(findings) == {"ads_budget:budget": "ok", "ads_budget:yesterday": "ok"}
    [budget] = [f for f in findings if f.key == "ads_budget:budget"]
    ar = budget.evidence["countries"]["AR"]
    # 250 remaining at $1 ads + $2 incentive per complete.
    assert (ar["remaining"], ar["ad_cost_per_complete"]) == (250, 1.0)
    assert ar["projected_ads"] == 500 + 250
    assert ar["projected_incentives"] == 600 * 2.0 + 250 * 2.0
    assert budget.evidence["projected"] == {"ads": 1500.0, "incentives": 1700 + 6800}


def test_over_the_total_is_a_decision():
    findings = ab.check(cfg(), snap(lines={"ads": 1000.0, "incentives": 5000.0}), [])
    assert levels(findings)["ads_budget:over-total"] == "decision"
    assert "ads_budget:budget" not in levels(findings)


def test_one_line_over_is_a_decision_unless_the_lines_are_pooled():
    lines = {"ads": 5000.0, "incentives": 8000.0}
    assert levels(ab.check(cfg(), snap(lines=lines), []))[
        "ads_budget:over-line:incentives"] == "decision"
    pooled = levels(ab.check(cfg(pooled=True), snap(lines=lines), []))
    assert pooled["ads_budget:budget"] == "ok"
    assert not any(k.startswith("ads_budget:over") for k in pooled)


def test_budget_per_arm_below_spent_plus_need_is_a_decision():
    # vlab_spent 1000 + 250 remaining x ($1 ads + $2 incentive) = 1750.
    findings = levels(ab.check(cfg(), snap(budget_per_arm=1700), []))
    assert findings["ads_budget:budget-per-arm:AR"] == "decision"
    assert findings["ads_budget:budget-per-arm:HN"] == "decision"
    assert "ads_budget:budget-per-arm:AR" not in levels(
        ab.check(cfg(), snap(budget_per_arm=1750), []))


def test_a_country_past_target_needs_nothing_more():
    f = [f for f in ab.check(cfg(), snap(ar_completes=800), []) if f.key == "ads_budget:budget"]
    assert f[0].evidence["countries"]["AR"]["remaining"] == 0
    assert f[0].evidence["countries"]["AR"]["projected_ads"] == 500


def test_no_completes_to_price_by_is_unknown_not_dropped():
    s = snap(campaign_days=[])
    s["countries"]["HN"].update(completes=[], paid=0)
    findings = levels(ab.check(cfg(), s, []))
    assert findings["ads_budget:no-cost-per-complete:HN"] == "unknown"
    assert "ads_budget:budget" not in findings


def test_without_recent_completes_ad_cost_falls_back_to_lifetime():
    s = snap()
    s["countries"]["AR"]["completes"] = ["2026-09-01"] * 500
    [b] = [f for f in ab.check(cfg(), s, []) if f.key == "ads_budget:budget"]
    ar = b.evidence["countries"]["AR"]
    assert (ar["ad_cost_per_complete"], ar["ad_cost_basis"]) == (
        round(500 / 600, 2), "lifetime spend / paid")


def test_another_currency_is_unknown():
    s = {**snap(), "currency": "EUR"}
    assert levels(ab.check(cfg(), s, [])) == {"ads_budget:currency": "unknown"}


# ---- ads -------------------------------------------------------------------

def steady(adset="s1", ad="a1", rate=10, days=range(1, 11), impressions=1000):
    return [ad_row(n, adset, ad, impressions, rate * impressions // 1000) for n in days]


def test_a_steady_ad_set_raises_nothing():
    findings = ab.ad_findings(snap(steady()), ab.settings(cfg()))
    assert findings == []


def test_a_fading_ad_set_is_a_decision_with_the_numbers():
    rows = steady(days=range(4, 11)) + steady(rate=4, days=range(1, 4))
    [f] = ab.ad_findings(snap(rows), ab.settings(cfg()))
    assert (f.level, f.key) == ("decision", "ads_budget:fading:s1")
    assert f.evidence["recent"]["per_1000"] == 4.0
    assert f.evidence["baseline"]["per_1000"] == 10.0
    assert f.evidence["recent"]["days"] == [day(3), day(2), day(1)]
    assert f.evidence["ads"] == {"a1": {"recent": 4.0, "baseline": 10.0}}
    assert "ar-wa / name-s1" in f.summary


def test_a_small_drop_or_a_quiet_ad_set_is_not_judged():
    s = ab.settings(cfg())
    mild = steady(days=range(4, 11)) + steady(rate=7, days=range(1, 4))
    assert ab.ad_findings(snap(mild), s) == []
    quiet = steady(days=range(4, 11)) + steady(rate=0, days=range(1, 4), impressions=200)
    assert ab.ad_findings(snap(quiet), s) == []


def test_todays_partial_day_is_left_out():
    # Today has impressions and, as yet, no conversations: counted, it would
    # read as a creative that stopped converting.
    rows = steady() + [ad_row(0, impressions=50_000, conversations=0)]
    assert ab.ad_findings(snap(rows), ab.settings(cfg())) == []
    s = snap(campaign_days=[
        {"campaign_name": "ar-wa", "date": day(0), "spend": 99.0, "impressions": 1,
         "reach": 1, "ctr": 0, "conversations": 0},
        {"campaign_name": "ar-wa", "date": day(1), "spend": 10.0, "impressions": 2000,
         "reach": 1500, "ctr": 1.2, "conversations": 20}])
    y = ab.yesterday(s)
    assert y.evidence["day"] == day(1)
    assert y.evidence["campaigns"]["ar-wa"] == {
        "spend": 10.0, "impressions": 2000, "reach": 1500, "ctr": 1.2, "conversations": 20,
        "cost_per_conversation": 0.5, "per_1000": 10.0}


def test_high_frequency_on_a_delivering_ad_set_is_a_decision():
    adsets = [{"adset_id": "s1", "adset_name": "name-s1", "campaign_name": "ar-wa",
               "reach": 10_000, "frequency": 2.4, "impressions": 24_000, "country": "AR"},
              {"adset_id": "old", "adset_name": "name-old", "campaign_name": "ar-wa",
               "reach": 5_000, "frequency": 3.1, "impressions": 15_500, "country": "AR"},
              {"adset_id": "s2", "adset_name": "name-s2", "campaign_name": "ar-wa",
               "reach": 5_000, "frequency": 1.5, "impressions": 7_500, "country": "AR"}]
    rows = steady() + steady(adset="s2")
    findings = ab.ad_findings(snap(rows, adsets), ab.settings(cfg()))
    # `old` stopped delivering, so its frequency no longer matters.
    assert levels(findings) == {"ads_budget:frequency:s1": "decision"}
    assert findings[0].evidence["frequency"] == 2.4


# ---- collect ---------------------------------------------------------------

class FakeClient:
    def __init__(self):
        self.calls = []

    def get_confs(self, org, slug):
        return {"general": {"ad_account": "111", "credentials_key": "Facebook"},
                "recruitment": {"budget_per_arm": 2460, "destinations": ["WhatsApp"],
                                "incentive_per_respondent": 2.35}}

    def recruitment_stats(self, org, slug):
        return {"s1": {"total_cost": 100.0}, "s2": {"total_cost": 50.5}}

    def meta_insights(self, org, **q):
        self.calls.append(q)
        row = {"campaign_id": "1", "campaign_name": "ar-wa", "adset_id": "s1",
               "adset_name": "n", "ad_id": "a", "ad_name": "a", "date_start": day(1),
               "spend": "2", "impressions": "100"}
        other = {**row, "campaign_name": "someone-else"}
        if q["after"] is None:
            return {"data": [row], "paging": {"truncated": True, "after": "C1"},
                    "timezone": "Europe/Madrid", "currency": "USD", "account_id": "act_111"}
        return {"data": [other], "paging": {"truncated": False, "after": None},
                "timezone": "Europe/Madrid", "currency": "USD", "account_id": "act_111"}


def test_collect_follows_pages_keeps_only_the_studys_campaigns(monkeypatch, tmp_path):
    proposal = tmp_path / "p.yaml"
    proposal.write_text("budget_line_items:\n"
                        "  - {description: Ads, total_price: 5000}\n"
                        "  - {description: Inc, total_price: 9600}\n")
    client = FakeClient()
    monkeypatch.setattr(ab.io, "vlab_client", lambda: client)
    monkeypatch.setattr(ab.io, "fly_get", lambda path, params=None: {"summary": [
        {"current_form": "arpay", "count": 5}, {"current_form": "arend", "count": 2},
        {"current_form": "ar1", "count": 99}]})
    monkeypatch.setattr(ab.pace, "collect", lambda c: {"countries": {"AR": {
        "completes": ["2026-09-30T10:00:00+00:00"], "target": 750}}})
    c = {"vlab": {"org": "o"},
         "countries": {"AR": {"vlab_slug": "ar", "survey_name": "AR", "pay": ["arpay"],
                              "end": "arend", "apology": "arsorry"}},
         "ads_budget": {"proposal": str(proposal), "lines": {"ads": "Ads", "incentives": "Inc"},
                        "countries": {"AR": {"campaigns": ["ar-"], "incentive_usd": 2.0}}}}

    s = ab.collect(c)

    assert [r["campaign_name"] for r in s["campaign_totals"]] == ["ar-wa"]
    assert s["campaign_totals"][0]["country"] == "AR"
    assert s["countries"]["AR"] == {
        "completes": ["2026-09-30"], "target": 750, "paid": 7,
        "arm": {"budget_per_arm": 2460, "destinations": ["WhatsApp"],
                "incentive_per_respondent": 2.35, "vlab_spent": 150.5}}
    assert s["proposal"]["lines"] == {"ads": 5000.0, "incentives": 9600.0}
    assert s["timezone"] == "Europe/Madrid"
    daily = [q for q in client.calls if q.get("time_increment") == "1"]
    assert {q["level"] for q in daily} == {"campaign", "ad"}
    assert all(q["until"] == s["today"] and q["account"] == "111"
               and q["credentials_key"] == "Facebook" for q in daily)


def test_a_relative_proposal_path_is_refused(monkeypatch):
    monkeypatch.setattr(ab.io, "vlab_client", FakeClient)
    c = {"vlab": {"org": "o"},
         "countries": {"AR": {"vlab_slug": "ar"}},
         "ads_budget": {"proposal": "rel/p.yaml", "lines": {},
                        "countries": {"AR": {"campaigns": ["ar-"]}}}}
    with pytest.raises(ValueError, match="absolute"):
        ab.collect(c)
