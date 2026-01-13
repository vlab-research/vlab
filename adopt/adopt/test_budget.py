from datetime import datetime, timedelta
from typing import Dict, Any

import numpy as np
import pandas as pd
import pytest

from .budget import (
    add_incentive,
    calc_price,
    estimate_price,
    get_budget_lookup,
    get_stats,
    make_report,
    prep_df_for_budget,
    proportional_budget,
    calculate_strata_stats,
    _users_per_cluster,
)
from .facebook.date_range import DateRange
from .test_clustering import DATE, _format_df, cnf, conf, df
from .campaign_queries import DBConf
from .study_conf import StratumConf
from .recruitment_data import (
    RecruitmentData,
    TimePeriod,
    AdPlatformRecruitmentStats,
    RecruitmentStats,
)


START_DATE = DATE
UNTIL_DATE = datetime(2020, 1, 3)


def test_get_stats_adds_zero_spend_when_no_info(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0}
    df = prep_df_for_budget(df, cnf)

    spend, _, _ = get_stats(df, cnf, window, spend, 10)
    assert spend == {"bar": 10.0, "baz": 10.0, "foo": 0.0}


def test_estimate_price_exponential_updating():
    res = estimate_price(0, 0)
    assert res == 2

    res = estimate_price(0.4, 0)
    assert res == 2

    res = estimate_price(0.6, 0)
    assert res == 4

    res = estimate_price(1, 0)
    assert res == 4

    res = estimate_price(3, 0)
    assert res == 8

    res = estimate_price(5, 0)
    assert res == 12

    res = estimate_price(10, 0)
    assert res == 22

    res = estimate_price(10, 1)
    assert res == 7.33

    res = estimate_price(20, 1)
    assert res == 14

    res = estimate_price(50, 1)
    assert res == 34

    res = estimate_price(40, 2)
    assert round(res) == 16

    res = estimate_price(5, 40)
    assert round(res, 2) == 0.15

    res = estimate_price(10, 40)
    assert round(res, 2) == 0.27


def test_calc_price_increases_price_when_no_user_after_spend(cnf, df):
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    df = prep_df_for_budget(df, cnf)
    window = DateRange(START_DATE, UNTIL_DATE)

    price = calc_price(df, window, spend, 0)
    assert price == {"bar": 7.33, "baz": 7.33, "foo": 22.0}

    # with incentive, it goes up by the incentive.
    price = calc_price(df, window, spend, 10)
    assert price == {"bar": 17.33, "baz": 17.33, "foo": 32.0}


def test_calc_price_picks_prior_if_no_spend(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend, 0)
    assert price == {"bar": 7.33, "baz": 7.33, "foo": 2.0}


def test_calc_price_works_with_nobody_in_window(cnf, df):
    window = DateRange(UNTIL_DATE + timedelta(days=2), UNTIL_DATE + timedelta(days=4))
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend, 0)
    assert price == {"bar": 22.0, "baz": 22.0, "foo": 22.0}


def test_calc_price_with_none_df():
    """Test calc_price behavior when df is None."""
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    # Test with no incentive
    price = calc_price(None, window, spend, 0)
    assert price == {
        "bar": 22.0,
        "baz": 22.0,
        "foo": 22.0,
    }  # High price when no users found

    # Test with incentive
    price = calc_price(None, window, spend, 10)
    assert price == {
        "bar": 32.0,
        "baz": 32.0,
        "foo": 32.0,
    }  # With incentive, it goes up by the incentive

    # Test with different spend amounts
    spend = {"bar": 100.0, "baz": 50.0, "foo": 0.0}
    price = calc_price(None, window, spend, 0)
    assert price == {
        "bar": 202.0,
        "baz": 102.0,
        "foo": 2.0,
    }  # Price increases with spend, 2.0 for zero spend


def test_proportional_budget_optimizes_all_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, expected, counterfactual_spend, counterfactual_recruits = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert round(budget["foo"]) == 40
    assert round(budget["bar"]) == 30
    assert round(budget["baz"]) == 30
    assert round(expected["foo"]) == 4.0
    assert round(expected["bar"]) == 4.0
    assert round(expected["baz"]) == 4.0
    # No counterfactuals when only budget constraint
    assert counterfactual_spend is None
    assert counterfactual_recruits is None


def test_proportional_budget_optimizes_for_weights():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    tot = {"bar": 1, "baz": 1, "foo": 1}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 0.3, "bar": 0.2, "baz": 0.5}
    budget, expected, _, _ = proportional_budget(goal, spend, tot, price, 10000, None, 1.0)

    assert round(expected["foo"]) == 301
    assert round(expected["bar"]) == 200
    assert round(expected["baz"]) == 502


def test_proportional_budget_drops_strata_under_min_to_min_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert round(budget["foo"]) == 40
    assert round(budget["bar"]) == 30
    assert round(budget["baz"]) == 30


def test_proportional_budget_can_drop_to_zero_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 10, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert round(budget["foo"]) == 55
    assert round(budget["bar"]) == 0
    assert round(budget["baz"]) == 45


def test_proportional_budget_prioritizes_underperforming_when_its_obvious():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 2}
    price = {"bar": 20.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert round(budget["foo"]) == 66
    assert round(budget["bar"]) == 17
    assert round(budget["baz"]) == 17


def test_proportional_budget_prioritizes_underperforming_even_at_high_cost():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 10, "foo": 2}
    price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert budget["foo"] == 100
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_works_to_turn_off_super_underperforming_and_unimportant():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 20, "foo": 0}
    price = {"bar": 5.0, "baz": 5.0, "foo": 500.0}
    goal = {"foo": 1 / 10, "bar": 4 / 10, "baz": 5 / 10}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 100, None, 1.0)
    assert budget["foo"] == 0
    assert round(budget["bar"]) == 33
    assert round(budget["baz"]) == 67


def test_proportional_budget_optimizes_even_if_already_pretty_good():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 3333, "baz": 3333, "foo": 3000}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _, _, _ = proportional_budget(goal, spend, tot, price, 1000, None, 1.0)
    assert budget["foo"] == 1000
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_raises_exception_when_not_near_one():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 2 / 3}
    with pytest.raises(Exception):
        proportional_budget(goal, spend, tot, price, 100, 16, 1.0)


def test_proportional_budget_with_max_recuits_optimizes_for_weights():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    tot = {"bar": 1, "baz": 1, "foo": 1}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 0.3, "bar": 0.5, "baz": 0.2}

    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=100, efficiency_weight=1.0
    )

    assert round(expected["foo"]) == 30
    assert round(expected["bar"]) == 50
    assert round(expected["baz"]) == 20


def test_proportional_budget_with_max_recruits_spends_on_missing_section():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 2}
    price = {"bar": 20.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, _, _, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=15, efficiency_weight=1.0
    )
    assert round(budget["foo"]) == 150
    assert round(budget["bar"]) == 0
    assert round(budget["baz"]) == 0


def test_proportional_budget_with_max_recruits_can_turn_off_empty_groups_without_zero_divide_errors():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 25, "baz": 25, "foo": 0}
    price = {"bar": 20.0, "baz": 20.0, "foo": 200.0}
    goal = {"foo": 1 / 100, "bar": 39 / 100, "baz": 60 / 100}

    budget, _, _, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=60, efficiency_weight=1.0
    )
    assert round(budget["foo"]) == 0
    assert round(budget["bar"]) == 0
    assert round(budget["baz"]) == 200


def test_proportional_budget_with_max_recruits_evenly_recruits_with_dif_prices():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 40.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, _, _, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=30, efficiency_weight=1.0
    )
    assert round(budget["foo"]) == 250
    assert round(budget["bar"]) == 100
    assert round(budget["baz"]) == 200


def test_proportional_budget_with_both_budget_and_max_recruits_picks_constraint():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, budget=100, max_recruits=30, efficiency_weight=1.0
    )
    assert round(sum(expected.values())) == 20
    assert round(sum(budget.values())) == 100

    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, budget=500, max_recruits=30, efficiency_weight=1.0
    )
    assert round(sum(expected.values())) == 30
    assert round(sum(budget.values())) == 300


def test_proportional_budget_with_efficiency_weight_zero_allocates_all_to_cheapest():
    """Test that efficiency_weight=0 allocates entire budget to cheapest stratum."""
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 10.0, "foo": 30.0}  # baz is cheapest
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, 300, None, 0.0
    )

    # With efficiency_weight=0, all budget should go to cheapest stratum (baz)
    assert budget["baz"] > budget["bar"]
    assert budget["baz"] > budget["foo"]
    # Most (if not all) budget should go to the cheapest option
    assert budget["baz"] / sum(budget.values()) > 0.8


def test_proportional_budget_with_efficiency_weight_one_matches_current_behavior():
    """Test that efficiency_weight=1.0 matches the original behavior (pure variance optimization)."""
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 10, "foo": 2}
    price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    # Test with efficiency_weight=1.0 (pure variance optimization)
    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, 100, None, 1.0
    )

    # Original test expectations (from test_proportional_budget_prioritizes_underperforming_even_at_high_cost)
    # With pure variance optimization, all budget goes to underperforming foo despite high cost
    assert budget["foo"] == 100
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_with_efficiency_weight_half_balances():
    """Test that efficiency_weight=0.5 balances between variance and efficiency."""
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 10, "foo": 2}
    price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    # Test with efficiency_weight=0.5 (balanced)
    budget_balanced, expected_balanced, _, _ = proportional_budget(
        goal, spend, tot, price, 100, None, 0.5
    )

    # Test with efficiency_weight=1.0 (pure variance - all to foo)
    budget_variance, expected_variance, _, _ = proportional_budget(
        goal, spend, tot, price, 100, None, 1.0
    )

    # Test with efficiency_weight=0.0 (pure efficiency - prefers cheapest)
    budget_efficiency, expected_efficiency, _, _ = proportional_budget(
        goal, spend, tot, price, 100, None, 0.0
    )

    # Balanced approach should allocate to multiple strata
    # Not all to foo like variance, and not all to cheapest (bar) like efficiency
    assert budget_balanced["foo"] < budget_variance["foo"]  # Less than pure variance
    assert budget_balanced["foo"] > 0  # But still some to underperforming foo
    assert budget_balanced["bar"] > 0  # Some to cheap bar (efficiency consideration)


def test_efficiency_weight_one_gives_variance_optimization():
    """Test that efficiency_weight=1.0 gives pure variance optimization."""
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 3333, "baz": 3333, "foo": 3000}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    # Call with explicit efficiency_weight=1.0
    budget, expected, _, _ = proportional_budget(
        goal, spend, tot, price, 1000, None, 1.0
    )

    # With pure variance optimization, all budget goes to underperforming foo
    assert budget["foo"] == 1000
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_get_budget_lookup(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    budget, _ = get_budget_lookup(df, cnf, 60, 0, 100, window, spend, spend, 1.0)
    assert round(budget["foo"]) == 16
    assert round(budget["bar"]) == 7
    assert round(budget["baz"]) == 7


def test_get_budget_lookup_with_proportional_budget_when_budget_is_spent(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    lifetime_spend = spend
    budget, _ = get_budget_lookup(df, cnf, 30, 0, 100, window, spend, lifetime_spend, 1.0)
    assert budget == {"bar": 0, "baz": 0, "foo": 0}


def test_get_budget_lookup_works_with_missing_data_from_clusters():
    cnf = conf(1)

    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rand", "105", 4),
        ],
        columns=cols,
    )

    df = _format_df(df)

    spend = {"bar": 10.0, "foo": 10.0, "baz": 10.0}
    window = DateRange(START_DATE, UNTIL_DATE)
    lifetime_spend = spend
    res, _ = get_budget_lookup(df, cnf, 40, 0, 100, window, spend, lifetime_spend, 1.0)

    assert {k: round(v, 1) for k, v in res.items()} == {
        "foo": 4.6,
        "bar": 0.7,
        "baz": 4.6,
    }


def test_make_report():
    r = make_report(
        [("goal", {"foo": 100, "bar": 10}), ("remain", {"foo": 90, "bar": 0})]
    )

    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}
    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}
    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}


def test_add_incentive():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 2, "foo": 0}

    res = add_incentive(spend, tot, 10)
    assert res == {"bar": 150.0, "baz": 120.0, "foo": 100.0}

    res = add_incentive(spend, tot, 0)
    assert res == spend


def test_get_budget_lookup_includes_incentive_in_total_spend(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    lifetime_spend = spend
    incentive = 10.0

    # Test data has 2 users total:
    # - 1 user in "bar" cluster
    # - 1 user in "baz" cluster
    # So total spend should be:
    # lifetime_spend (30) + (2 users * 10 incentive) = 50

    # First let's verify with a small budget to ensure we're counting incentives
    budget, report = get_budget_lookup(
        df,
        cnf,
        max_budget=40,
        incentive_per_respondent=incentive,
        max_sample_size=100,
        window=window,
        spend=spend,
        lifetime_spend=lifetime_spend,
        efficiency_weight=1.0,
    )

    # If incentives are properly counted, we should have no budget left
    assert budget == {"bar": 0, "baz": 0, "foo": 0}

    # Now test with a larger budget to verify remaining calculation
    budget, report = get_budget_lookup(
        df,
        cnf,
        max_budget=100,
        incentive_per_respondent=incentive,
        max_sample_size=100,
        window=window,
        spend=spend,
        lifetime_spend=lifetime_spend,
        efficiency_weight=1.0,
    )

    assert sum(budget.values()) == pytest.approx(50)


def test_get_budget_lookup_works_with_zero_incentive(cnf, df):
    window = DateRange(START_DATE, UNTIL_DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    lifetime_spend = spend

    # With no incentive, total_spend should just be lifetime_spend (30)
    budget, _ = get_budget_lookup(
        df,
        cnf,
        max_budget=30,
        incentive_per_respondent=0,
        max_sample_size=100,
        window=window,
        spend=spend,
        lifetime_spend=lifetime_spend,
        efficiency_weight=1.0,
    )
    assert budget == {"bar": 0, "baz": 0, "foo": 0}

    budget, _ = get_budget_lookup(
        df,
        cnf,
        max_budget=60,
        incentive_per_respondent=0,
        max_sample_size=100,
        window=window,
        spend=spend,
        lifetime_spend=lifetime_spend,
        efficiency_weight=1.0,
    )
    assert sum(budget.values()) == pytest.approx(30)  # 60 - 30 = 30 remaining


def test_make_report():
    r = make_report(
        [("goal", {"foo": 100, "bar": 10}), ("remain", {"foo": 90, "bar": 0})]
    )

    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}
    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}
    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}


def test_add_incentive():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 2, "foo": 0}

    res = add_incentive(spend, tot, 10)
    assert res == {"bar": 150.0, "baz": 120.0, "foo": 100.0}

    res = add_incentive(spend, tot, 0)
    assert res == spend


def make_recruitment_data_from_dict(rd_dict, start_date):
    # rd_dict: dict with keys as stratum_id and values as dict of metrics
    # returns a list with a single RecruitmentData object
    return [
        RecruitmentData(
            TimePeriod(start_date, start_date),
            False,
            {"campaign": {k: v for k, v in rd_dict.items()}},
        )
    ]


def test_calculate_strata_stats_basic(cnf, df):
    """Test basic functionality of calculate_strata_stats."""
    window = DateRange(START_DATE, UNTIL_DATE)
    recruitment_stats = {
        "foo": AdPlatformRecruitmentStats(
            spend=100.0,
            frequency=2.0,
            reach=500,
            cpm=100.0,
            unique_clicks=100,
            unique_ctr=0.1,
        ),
        "bar": AdPlatformRecruitmentStats(
            spend=200.0,
            frequency=2.0,
            reach=1000,
            cpm=100.0,
            unique_clicks=200,
            unique_ctr=0.1,
        ),
        "baz": AdPlatformRecruitmentStats(
            spend=300.0,
            frequency=2.0,
            reach=1500,
            cpm=100.0,
            unique_clicks=300,
            unique_ctr=0.1,
        ),
    }

    # Ensure at least one respondent in 'foo' for the test window using _format_df and correct targeting
    df_foo = pd.DataFrame(
        [
            ("dist", "foo", 999),
            ("rand", "105", 999),
        ],
        columns=["variable", "value", "user_id"],
    )
    df_foo = _format_df(df_foo)
    df = pd.concat([df, df_foo], ignore_index=True)

    df = prep_df_for_budget(df, cnf)
    respondents_dict = _users_per_cluster(df)

    stats = calculate_strata_stats(
        respondents_dict,
        cnf,
        recruitment_stats,
        incentive_per_respondent=10.0,
    )

    # Check that all strata are present
    assert set(stats.keys()) == {"foo", "bar", "baz"}

    # Check recruitment data was properly copied
    assert stats["foo"].spend == 100.0
    assert stats["bar"].frequency == 2.0
    assert stats["baz"].unique_clicks == 300

    # Check calculated fields
    assert stats["foo"].incentive_cost == 10.0  # 1 respondent * 10 incentive
    assert stats["foo"].total_cost == 110.0  # 100 spend + 10 incentive
    assert stats["foo"].conversion_rate == 0.01  # 1 respondent / 100 unique_clicks


def test_calculate_strata_stats_missing_recruitment_data(cnf, df):
    """Test calculate_strata_stats with missing recruitment data."""
    window = DateRange(START_DATE, UNTIL_DATE)
    recruitment_stats = {
        "foo": AdPlatformRecruitmentStats(
            spend=100.0,
            frequency=2.0,
            reach=500,
            cpm=100.0,
            unique_clicks=100,
            unique_ctr=0.1,
        ),
        "bar": AdPlatformRecruitmentStats(
            spend=200.0,
            frequency=2.0,
            reach=1000,
            cpm=100.0,
            unique_clicks=200,
            unique_ctr=0.1,
        ),
        # Missing 'baz'
    }

    # Create respondents dictionary from DataFrame
    df = prep_df_for_budget(df, cnf)
    respondents_dict = _users_per_cluster(df)

    stats = calculate_strata_stats(
        respondents_dict,
        cnf,
        recruitment_stats,
        incentive_per_respondent=10.0,
    )

    # Check that all strata are present with zeros for missing data
    assert set(stats.keys()) == {"foo", "bar", "baz"}
    assert stats["baz"].spend == 0.0
    assert stats["baz"].frequency == 0.0
    assert stats["baz"].unique_clicks == 0


def test_calculate_strata_stats_missing_response_data(cnf):
    """Test calculate_strata_stats with no response data."""
    recruitment_stats = {
        "foo": AdPlatformRecruitmentStats(
            spend=100.0,
            frequency=2.0,
            reach=500,
            cpm=100.0,
            unique_clicks=100,
            unique_ctr=0.1,
        ),
        "bar": AdPlatformRecruitmentStats(
            spend=200.0,
            frequency=2.0,
            reach=1000,
            cpm=100.0,
            unique_clicks=200,
            unique_ctr=0.1,
        ),
        "baz": AdPlatformRecruitmentStats(
            spend=300.0,
            frequency=2.0,
            reach=1500,
            cpm=100.0,
            unique_clicks=300,
            unique_ctr=0.1,
        ),
    }

    stats = calculate_strata_stats(
        None,  # No response data
        cnf,
        recruitment_stats,
        incentive_per_respondent=10.0,
    )

    # Check that respondents and derived fields are zero
    assert stats["foo"].respondents == 0
    assert stats["foo"].incentive_cost == 0.0
    assert stats["foo"].total_cost == 100.0  # Just the spend
    assert stats["foo"].conversion_rate == 0.0


def test_calculate_strata_stats_invalid_stratum(cnf, df):
    """Test calculate_strata_stats with invalid stratum IDs."""
    recruitment_stats = {
        "invalid_stratum": AdPlatformRecruitmentStats(
            spend=100.0,
            frequency=2.0,
            reach=500,
            cpm=100.0,
            unique_clicks=100,
            unique_ctr=0.1,
        ),
    }

    # Create respondents dictionary with invalid stratum
    respondents_dict = {"invalid_stratum": 10}

    stats = calculate_strata_stats(
        respondents_dict,
        cnf,
        recruitment_stats,
        incentive_per_respondent=10.0,
    )

    # Check that all valid strata are present with default values
    assert set(stats.keys()) == {"foo", "bar", "baz"}
    assert stats["foo"].spend == 0.0
    assert stats["bar"].spend == 0.0
    assert stats["baz"].spend == 0.0


def test_calculate_strata_stats_zero_values(cnf, df):
    """Test calculate_strata_stats with zero values."""
    recruitment_stats = {
        "foo": AdPlatformRecruitmentStats(
            spend=0.0,
            frequency=0.0,
            reach=0,
            cpm=0.0,
            unique_clicks=0,
            unique_ctr=0.0,
        ),
        "bar": AdPlatformRecruitmentStats(
            spend=0.0,
            frequency=0.0,
            reach=0,
            cpm=0.0,
            unique_clicks=0,
            unique_ctr=0.0,
        ),
        "baz": AdPlatformRecruitmentStats(
            spend=0.0,
            frequency=0.0,
            reach=0,
            cpm=0.0,
            unique_clicks=0,
            unique_ctr=0.0,
        ),
    }

    # Create respondents dictionary from DataFrame
    df = prep_df_for_budget(df, cnf)
    respondents_dict = _users_per_cluster(df)

    stats = calculate_strata_stats(
        respondents_dict,
        cnf,
        recruitment_stats,
        incentive_per_respondent=10.0,
    )

    # Check that conversion rate is 0 when unique_clicks is 0
    assert stats["foo"].conversion_rate == 0.0
    assert stats["bar"].conversion_rate == 0.0
    assert stats["baz"].conversion_rate == 0.0


def test_proportional_budget_with_both_constraints_shows_counterfactual_spend():
    """Test that when budget constraint binds, counterfactual_spend is returned."""
    # Using parameters that DEFINITELY make budget bind:
    # budget=100, max_recruits=30 (from existing test at line 312-319)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected, counterfactual_spend, counterfactual_recruits = proportional_budget(
        goal, spend, tot, price, budget=100, max_recruits=30, efficiency_weight=1.0
    )

    # When budget binds, counterfactual_spend shows cost to fill sample without budget constraint
    assert sum(budget.values()) == pytest.approx(100), "Budget constraint should bind with these parameters"
    assert counterfactual_spend is not None, "counterfactual_spend should be present when budget binds"
    assert counterfactual_recruits is None, "counterfactual_recruits should be None when budget binds"
    # counterfactual_spend should be higher than actual spend (cost to fill sample)
    assert sum(counterfactual_spend.values()) > 100


def test_proportional_budget_with_both_constraints_shows_counterfactual_recruits():
    """Test that when respondent constraint binds, counterfactual_recruits is returned."""
    # Using parameters that DEFINITELY make respondents bind:
    # budget=500, max_recruits=30 (from existing test at line 318-325)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected, counterfactual_spend, counterfactual_recruits = proportional_budget(
        goal, spend, tot, price, budget=500, max_recruits=30, efficiency_weight=1.0
    )

    # When respondent constraint binds, counterfactual_recruits shows what could be achieved
    assert sum(budget.values()) < 500, "Respondent constraint should bind with these parameters"
    assert counterfactual_recruits is not None, "counterfactual_recruits should be present when respondents bind"
    assert counterfactual_spend is None, "counterfactual_spend should be None when respondents bind"
    # counterfactual_recruits should be higher than actual (recruits with unlimited budget)
    assert sum(counterfactual_recruits.values()) >= sum(expected.values()), "counterfactual_recruits should be at least as large as actual recruits"


def test_proportional_budget_no_counterfactual_when_only_max_recruits():
    """Test that no counterfactual is returned when only max_recruits constraint is provided."""
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected, cf_spend, cf_recruits = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=30, efficiency_weight=1.0
    )

    # No counterfactual possible without both constraints
    assert cf_spend is None
    assert cf_recruits is None
