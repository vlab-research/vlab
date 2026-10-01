from datetime import date, timedelta

import pytest

from . import ads_budget as ab

TODAY = date(2026, 10, 1)
CONV = "onsite_conversion.messaging_conversation_started_7d"
CFG = {"parts": [{"name": "AR", "vlab_slug": "ar", "survey_name": "s", "incentive": 2.0},
                 {"name": "HN", "vlab_slug": "hn", "survey_name": "s", "incentive": 8.0}],
       "ads_budget": {}}
S = ab.settings(CFG, ab.NAME, ab.DEFAULTS)


def day(n):
    """`n` days before TODAY, ISO."""
    return (TODAY - timedelta(days=n)).isoformat()


def ad_row(n, adset="s1", ad="a1", impressions=1000, conversations=10, campaign="ar-wa",
           part="AR", spend=1.0):
    return {"campaign_name": campaign, "adset_id": adset, "adset_name": f"name-{adset}",
            "ad_name": ad, "date": day(n), "spend": spend, "impressions": impressions,
            "conversations": conversations, "part": part}


def adset(adset_id, frequency, part="AR", spend=0.0):
    return {"adset_id": adset_id, "adset_name": f"name-{adset_id}", "campaign_name": "ar-wa",
            "reach": 1000, "frequency": frequency, "spend": spend, "part": part}


def snap(ad_days=None, adsets=None, ar_completes=500, lines=None, budget_per_arm=10_000,
         incentive=2.0):
    """AR and HN, target 750 each, $500 lifetime ad spend each. Over the last 7
    complete days each spent $70 on ads for 70 completes ($1 per complete)."""
    def part(n):
        recent = [f"{day(1 + i % 7)}T12:00:00Z" for i in range(70)]
        return {"completes": recent + ["2026-09-01T12:00:00Z"] * (n - 70),
                "target": 750, "paid": 600,
                "arm": {"budget_per_arm": budget_per_arm, "destinations": ["WhatsApp"],
                        "incentive_per_respondent": incentive, "vlab_spent": 1000.0}}

    default_days = [ad_row(n, adset=k, campaign=f"{k}-wa", part=k.upper(), spend=10.0)
                    for n in range(1, 8) for k in ("ar", "hn")]
    return {
        "account": "act_1", "timezone": "Europe/Madrid", "currency": "USD",
        "today": TODAY.isoformat(), "ad_days": default_days if ad_days is None else ad_days,
        "adsets": adsets or [adset("ar", 1.0, spend=500.0), adset("hn", 1.0, "HN", spend=500.0)],
        "parts": {"AR": part(ar_completes), "HN": part(500)},
        "proposal": {"path": "p.yaml", "currency": "USD",
                     "lines": lines or {"ads": 5000.0, "incentives": 9600.0}},
    }


def levels(findings):
    return {f.key: f.level for f in findings}


def test_shape_reads_numbers_conversations_and_part():
    row = {"campaign_name": "ar-wa", "date_start": "2026-09-30", "spend": "1.50",
           "impressions": "300", "reach": "250", "frequency": "1.2",
           "actions": [{"action_type": "link_click", "value": "9"},
                       {"action_type": CONV, "value": "4"}]}
    assert ab.shape(row, {"AR": ["ar-"]}) == {
        "campaign_name": "ar-wa", "part": "AR", "date": "2026-09-30", "spend": 1.5,
        "impressions": 300, "reach": 250, "frequency": 1.2, "conversations": 4}
    assert ab.shape({"campaign_name": "x"}, {"AR": ["ar-"]})["part"] is None


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
    keys = ("budget-per-arm", "budget", "fading", "frequency", "yesterday")
    assert levels(findings) == {f"ads_budget:{k}": "ok" for k in keys}
    [budget] = [f for f in findings if f.key == "ads_budget:budget"]
    ar = budget.evidence["parts"]["AR"]
    assert (ar["remaining"], ar["ad_cost_per_complete"]) == (250, 1.0)
    assert ar["projected_ads"] == 500 + 250
    assert ar["projected_incentives"] == 600 * 2.0 + 250 * 2.0
    assert budget.evidence["projected"] == {"ads": 1500.0, "incentives": 1700 + 6800}


def test_completes_are_dated_in_the_ad_accounts_timezone():
    # 02:00 UTC today is yesterday in Buenos Aires, so inside the cost days.
    s = {**snap(), "timezone": "America/Argentina/Buenos_Aires"}
    s["parts"]["AR"]["completes"] = [f"{day(0)}T02:00:00Z"] * 10 + ["2026-09-01"] * 490
    assert ab.project("AR", s["parts"]["AR"], s, S, 2.0)["ad_cost_per_complete"] == 7.0


def test_over_the_total_or_one_line_over():
    assert levels(ab.check(CFG, snap(lines={"ads": 1000.0, "incentives": 5000.0}), []))[
        "ads_budget:over-total"] == "decision"
    lines = {"ads": 5000.0, "incentives": 8000.0}
    over = levels(ab.check(CFG, snap(lines=lines), []))
    assert over["ads_budget:over-line:incentives"] == "decision"


def test_budget_per_arm_short_or_missing():
    # vlab_spent 1000 + 250 remaining x ($1 ads + $2 incentive) = 1750.
    [f] = [f for f in ab.check(CFG, snap(budget_per_arm=1700), []) if "arm" in f.key]
    assert f.level == "decision" and "AR" in f.summary and "HN" in f.summary
    key = "ads_budget:budget-per-arm"
    assert levels(ab.check(CFG, snap(budget_per_arm=1750), []))[key] == "ok"
    for missing in (snap(budget_per_arm=None), snap(incentive=None)):
        assert levels(ab.check(CFG, missing, []))[key] == "unknown"


def test_past_target_needs_no_cost_per_complete_but_others_do():
    s = snap()
    s["parts"]["AR"]["completes"] = ["2026-09-01"] * 800
    [b] = [f for f in ab.check(CFG, s, []) if f.key == "ads_budget:budget"]
    assert b.evidence["parts"]["AR"]["projected_ads"] == 500
    s["parts"]["HN"]["completes"] = ["2026-09-01"] * 500
    found = levels(ab.check(CFG, s, []))
    assert found["ads_budget:no-cost-per-complete"] == "unknown"
    assert "ads_budget:budget" not in found


def test_a_proposal_in_another_currency_or_an_unmatched_campaign_that_spent_is_unknown():
    eur = levels(ab.check(CFG, {**snap(), "currency": "EUR"}, []))
    assert eur["ads_budget:currency"] == "unknown" and "ads_budget:budget" not in eur
    assert eur["ads_budget:budget-per-arm"] == "ok"
    s = snap()
    s["ad_days"] += [ad_row(2, campaign="Templates", part=None, spend=3.0),
                     ad_row(2, campaign="Paused", part=None, spend=0.0)]
    [f] = [f for f in ab.check(CFG, s, []) if f.key == "ads_budget:unmatched-campaigns"]
    assert f.level == "unknown" and f.evidence == {"spend": {"Templates": 3.0}}
    other = {**CFG, "ads_budget": {**CFG["ads_budget"], "other_campaigns": ["Temp"]}}
    assert "ads_budget:unmatched-campaigns" not in levels(ab.check(other, s, []))


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
    assert (f.level, f.evidence["new"]) == ("decision", ["s2"])
    assert sorted(f.evidence["adsets"]) == ["s1", "s2"]
    assert by_key(ab.ad_findings(now, S, [now]))["frequency"].level == "ok"


# ---- collect ---------------------------------------------------------------

class FakeVlab:
    def get_confs(self, org, slug):
        return {"general": {"ad_account": "1", "credentials_key": "k"},
                "recruitment": {"budget_per_arm": 100, "ad_campaign_name_base": f"vlab-{slug}"}}

    def meta_insights(self, org, **query):
        return {"data": [], "paging": {"truncated": False}, "account_id": "1",
                "timezone": "UTC", "currency": "USD"}

    def recruitment_stats(self, org, slug):
        return {"s1": {"total_cost": 5.0}}

    def current_data(self, org, slug):
        return [{"variable": "done", "timestamp": "2026-09-20T10:00:00Z"},
                {"variable": "done", "timestamp": "2026-09-01T10:00:00Z"},
                {"variable": "age", "timestamp": "2026-09-21T10:00:00Z"}]


def test_collect_counts_completes_as_pace_does(tmp_path, monkeypatch):
    (tmp_path / "proposal.yaml").write_text(
        "budget_line_items:\n- {description: Ads, total_price: 10}\n"
        "- {description: Inc, total_price: 20}\n")
    cfg = {"study_dir": tmp_path, "vlab": {"org": "o"},
           "parts": [{"name": "AR", "vlab_slug": "ar", "survey_name": "s", "pay": ["p"],
                      "after_pay": ["e"], "target": 750}],
           "pace": {"completion_ref": "done", "count_from": "2026-09-10"},
           "ads_budget": {"proposal": {"path": "proposal.yaml", "currency": "USD",
                                       "lines": {"ads": "Ads", "incentives": "Inc"}}}}
    monkeypatch.setattr(ab.io, "vlab_client", FakeVlab)
    monkeypatch.setattr(ab.io, "fly_get", lambda *path, params=None: {"summary": [
        {"current_form": "e", "count": 3}, {"current_form": "q", "count": 9}]})
    snap = ab.collect(cfg)
    ar = snap["parts"]["AR"]
    assert (ar["completes"], ar["target"], ar["paid"]) == (["2026-09-20T10:00:00Z"], 750, 3)
    assert snap["proposal"]["lines"] == {"ads": 10.0, "incentives": 20.0}
