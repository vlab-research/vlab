from datetime import datetime

import pandas as pd
import pytest

from .budget import (calc_price, get_budget_lookup, get_stats, make_report,
                     prep_df_for_budget, proportional_budget)
from .facebook.date_range import DateRange
from .test_clustering import _format_df, cnf, conf, df

DATE = datetime(2020, 1, 1)


def test_get_stats_adds_zero_spend_when_no_info(cnf, df):
    window = DateRange(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0}
    df = prep_df_for_budget(df, cnf)

    spend, _, _ = get_stats(df, cnf, window, spend)
    assert spend == {"bar": 10.0, "baz": 10.0, "foo": 0.0}


def test_calc_price_pretends_as_if_found_half_user_when_no_user(cnf, df):
    window = DateRange(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend)
    assert price == {"bar": 10.0, "baz": 10.0, "foo": 20.0}


def test_calc_price_picks_mean_if_no_spend_(cnf, df):
    window = DateRange(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend)
    assert price == {"bar": 10.0, "baz": 10.0, "foo": 10.0}


def test_proportional_budget_optimizes_all_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, expected = proportional_budget(goal, spend, tot, price, 100)
    assert round(budget["foo"]) == 40
    assert round(budget["bar"]) == 30
    assert round(budget["baz"]) == 30
    assert round(expected["foo"]) == 4.0
    assert round(expected["bar"]) == 4.0
    assert round(expected["baz"]) == 4.0


def test_proportional_budget_optimizes_for_weights():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    tot = {"bar": 1, "baz": 1, "foo": 1}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 0.3, "bar": 0.2, "baz": 0.5}
    budget, expected = proportional_budget(goal, spend, tot, price, 10000)

    assert round(expected["foo"]) == 301
    assert round(expected["bar"]) == 201
    assert round(expected["baz"]) == 502


def test_proportional_budget_drops_strata_under_min_to_min_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100)
    assert round(budget["foo"]) == 40
    assert round(budget["bar"]) == 30
    assert round(budget["baz"]) == 30


def test_proportional_budget_can_drop_to_zero_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 10, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100)
    assert round(budget["foo"]) == 55
    assert round(budget["bar"]) == 0
    assert round(budget["baz"]) == 45


def test_proportional_budget_prioritizes_underperforming_when_its_obvious():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 2}
    price = {"bar": 20.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100)
    assert round(budget["foo"]) == 77
    assert round(budget["bar"]) == 12
    assert round(budget["baz"]) == 12


def test_proportional_budget_prioritizes_underperforming_even_at_high_cost():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 10, "foo": 2}
    price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100)
    assert budget["foo"] == 100
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_optimizes_even_if_already_pretty_good():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 3333, "baz": 3333, "foo": 3000}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 1000)
    assert budget["foo"] == 1000
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_raises_exception_when_not_near_one():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 2 / 3}
    with pytest.raises(Exception):
        proportional_budget(goal, spend, tot, price, 100, 16)


def test_proportional_budget_with_max_recuits_optimizes_for_weights():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    tot = {"bar": 1, "baz": 1, "foo": 1}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 0.3, "bar": 0.2, "baz": 0.5}

    budget, expected = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=100
    )

    assert round(expected["foo"]) == 30
    assert round(expected["bar"]) == 20
    assert round(expected["baz"]) == 50


def test_proportional_budget_with_max_recruits_spends_on_missing_section():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 2}
    price = {"bar": 20.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=15
    )
    assert round(budget["foo"]) == 150
    assert round(budget["bar"]) == 0
    assert round(budget["baz"]) == 0


def test_proportional_budget_with_max_recruits_evenly_recruits_with_dif_prices():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 40.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, _ = proportional_budget(
        goal, spend, tot, price, budget=None, max_recruits=30
    )
    assert round(budget["foo"]) == 250
    assert round(budget["bar"]) == 100
    assert round(budget["baz"]) == 200


def test_proportional_budget_with_both_budget_and_max_recruits_picks_constraint():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 5}
    price = {"bar": 20.0, "baz": 20.0, "foo": 20.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}

    budget, expected = proportional_budget(
        goal, spend, tot, price, budget=100, max_recruits=30
    )
    assert round(sum(expected.values())) == 20
    assert round(sum(budget.values())) == 100

    budget, expected = proportional_budget(
        goal, spend, tot, price, budget=500, max_recruits=30
    )
    assert round(sum(expected.values())) == 30
    assert round(sum(budget.values())) == 300


def test_get_budget_lookup(cnf, df):
    window = DateRange(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    budget, _ = get_budget_lookup(df, cnf, 60, 100, window, spend, 0.3)
    assert round(budget["foo"]) == 21
    assert round(budget["bar"]) == 5
    assert round(budget["baz"]) == 5


def test_get_budget_lookup_with_proportional_budget_when_budget_is_spent(cnf, df):
    window = DateRange(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    budget, _ = get_budget_lookup(df, cnf, 30, 100, window, spend, 3.0)
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
    window = DateRange(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 50, 100, window, spend, 0.40)

    assert res == {"foo": 5.0, "bar": 0.0, "baz": 5.0}


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
