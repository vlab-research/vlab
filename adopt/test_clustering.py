from datetime import datetime

import pandas as pd
import pytest

from .clustering import (budget_trimming, calc_price, get_budget_lookup,
                         get_saturated_clusters, get_stats, make_report,
                         only_latest_survey, only_target_users,
                         prep_df_for_budget, proportional_budget, shape_df)
from .facebook.state import BudgetWindow, unix_time_millis
from .marketing import make_stratum_conf

DATE = datetime(2020, 1, 1)


def make_conf(c):
    return [make_stratum_conf(d) for d in c]


def conf(quota=2, field="response"):
    c = [
        {
            "id": "foo",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "foo"},
                        ],
                    },
                    {
                        "op": "greater_than",
                        "vars": [
                            {"type": field, "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
        {
            "id": "bar",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "bar"},
                        ],
                    },
                    {
                        "op": "greater_than",
                        "vars": [
                            {"type": field, "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
        {
            "id": "baz",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "excluded_audiences": [],
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "baz"},
                        ],
                    },
                    {
                        "op": "greater_than",
                        "vars": [
                            {"type": field, "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
    ]
    return make_conf(c)


@pytest.fixture
def cnf():
    return conf()


def _add_timestamp(df):
    df["timestamp"] = pd.Timestamp(DATE)
    return df


def _add_time(df):
    return (
        df.groupby(["userid", "surveyid"])
        .apply(
            lambda df: df.append(
                [
                    {
                        **df.iloc[0].to_dict(),
                        "question_ref": "md:startTime",
                        "response": unix_time_millis(DATE),
                    }
                ]
            )
        )
        .reset_index(drop=True)
    )


def _format_df(df):
    df["surveyid"] = df.shortcode
    df = _add_time(df)
    df = _add_timestamp(df)
    df = shape_df(df)
    return df


@pytest.fixture
def df():
    cols = ["question_ref", "response", "userid", "shortcode"]
    d = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "50", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "105", 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", "105", 5, "bar"),
        ],
        columns=cols,
    )
    return _format_df(d)


def test_only_latest_survey_removes_duplicate_surveyids_per_user():
    cols = ["question_ref", "response", "userid", "shortcode", "surveyid"]
    d = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo", "bar"),
            ("rand", "50", 1, "foo", "bar"),
            ("dist", "fooz", 1, "foo", "baz"),
            ("dist", "bar", 2, "foo", "foo"),
            ("rand", "55", 2, "foo", "foo"),
            ("dist", "bar", 3, "foo", "foo"),
            ("rand", "60", 3, "foo", "foo"),
            ("dist", "bar", 4, "bar", "foo"),
            ("rand", "105", 4, "bar", "foo"),
        ],
        columns=cols,
    )

    df = only_latest_survey(_add_timestamp(d))
    assert df.shape[0] == 7
    assert df[df.userid == 1].response.tolist() == ["fooz"]


def test_get_only_target_users_with_empty_target_questions_filters_none(df):
    s = {
        "id": "foo",
        "quota": 1,
        "creatives": [],
        "shortcodes": ["foo", "bar"],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {},
        "metadata": {},
        "question_targeting": None,
    }

    stratum = make_stratum_conf(s)
    res = only_target_users(df, stratum)
    assert res.equals(df)


def test_get_saturated_clusters_with_some_fulfilled(cnf):

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "50", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "101", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "103", 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", "99", 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["bar"]


def test_get_saturated_clusters_ignores_poorly_formated_numbers(cnf):

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "50", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "jkljk", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "101", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "103", 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", "99", 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["bar"]


def test_get_saturated_clusters_with_some_fulfilled_on_translated_response():
    cnf = conf(2, "translated_response")
    cols = ["question_ref", "response", "translated_response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", None, 1, "foo"),
            ("rand", "50", 50, 1, "foo"),
            ("dist", "bar", None, 2, "foo"),
            ("rand", "55", 55, 2, "foo"),
            ("dist", "bar", None, 3, "foo"),
            ("rand", "101", 101, 3, "foo"),
            ("dist", "bar", None, 4, "bar"),
            ("rand", "103", 103, 4, "bar"),
            ("dist", "baz", None, 5, "bar"),
            ("rand", "99", 99, 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["bar"]


def test_get_saturated_clusters_with_some_users_no_cluster(cnf):
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "50", 1, "foo"),
            ("rand", "55", 2, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "105", 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", "99", 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)

    assert res == []


def test_get_saturated_clusters_with_no_fulfilled(cnf):
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "50", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "105", 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", "99", 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)

    assert res == []


def test_get_saturated_clusters_filters_only_appropriate_shortcodes():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "shortcodes": ["foo"],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "greater_than",
                "vars": [
                    {"type": "response", "value": "rand"},
                    {"type": "constant", "value": 100},
                ],
            },
        },
        {
            "id": "barfoo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "shortcodes": ["bar"],
            "question_targeting": {
                "op": "greater_than",
                "vars": [
                    {"type": "response", "value": "rook"},
                    {"type": "constant", "value": 100},
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "105", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rook", 50, 4, "bar"),
            ("dist", "foo", 5, "foo"),
            ("rook", 105, 5, "foo"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["foo"]


def test_get_saturated_clusters_with_different_id_fields():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "shortcodes": ["foo", "bar"],
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "foo"},
                        ],
                    },
                    {
                        "op": "greater_than",
                        "vars": [
                            {"type": "response", "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
        {
            "id": "bar",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "shortcodes": ["foo", "bar"],
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dood"},
                            {"type": "constant", "value": "bar"},
                        ],
                    },
                    {
                        "op": "less_than",
                        "vars": [
                            {"type": "response", "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "105", 1, "foo"),
            ("dood", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dood", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dood", "bar", 4, "bar"),
            ("rook", 50, 4, "bar"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["foo", "bar"]


def test_get_saturated_clusters_with_complex_nested_or_condition():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "shortcodes": ["foo", "bar"],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "foo"},
                        ],
                    },
                    {
                        "op": "or",
                        "vars": [
                            {
                                "op": "greater_than",
                                "vars": [
                                    {"type": "response", "value": "rand"},
                                    {"type": "constant", "value": 100},
                                ],
                            },
                            {
                                "op": "equal",
                                "vars": [
                                    {"type": "response", "value": "rand"},
                                    {"type": "constant", "value": 999},
                                ],
                            },
                            {
                                "op": "less_than",
                                "vars": [
                                    {"type": "response", "value": "rand"},
                                    {"type": "constant", "value": 54},
                                ],
                            },
                        ],
                    },
                ],
            },
        },
        {
            "id": "bar",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "shortcodes": ["foo", "bar"],
            "facebook_targeting": {},
            "metadata": {},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "response", "value": "dist"},
                            {"type": "constant", "value": "bar"},
                        ],
                    },
                    {
                        "op": "or",
                        "vars": [
                            {
                                "op": "greater_than",
                                "vars": [
                                    {"type": "response", "value": "rand"},
                                    {"type": "constant", "value": 100},
                                ],
                            },
                            {
                                "op": "less_than",
                                "vars": [
                                    {"type": "response", "value": "rand"},
                                    {"type": "constant", "value": 54},
                                ],
                            },
                        ],
                    },
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "105", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "50", 4, "bar"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["foo", "bar"]


def test_get_saturated_clusters_works_with_is_answered_op():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "shortcodes": ["foo"],
            "question_targeting": {
                "op": "answered",
                "vars": [{"type": "response", "value": "rand"}],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", "105", 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rook", 50, 4, "bar"),
            ("dist", "foo", 5, "foo"),
            ("rook", 105, 5, "foo"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["foo"]


def test_get_saturated_clusters_not_equal_only_those_who_answered():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "metadata": {},
            "shortcodes": ["foo"],
            "question_targeting": {
                "op": "not_equal",
                "vars": [
                    {"type": "response", "value": "rook"},
                    {"type": "constant", "value": "105"},
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("rand", "105", 1, "foo"),
            ("rand", "55", 2, "foo"),
            ("rand", "60", 3, "foo"),
            ("rook", "105", 1, "bar"),
            ("rook", "105", 2, "foo"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == []


def test_get_stats_adds_zero_spend_when_no_info(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0}
    df = prep_df_for_budget(df, cnf)

    spend, _, _ = get_stats(df, cnf, window, spend)
    assert spend == {"bar": 10.0, "baz": 10.0, "foo": 0.0}


def test_calc_price_pretends_as_if_found_half_user_when_no_user(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend)
    assert price == {"bar": 10.0, "baz": 10.0, "foo": 20.0}


def test_calc_price_picks_mean_if_no_spend_(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    df = prep_df_for_budget(df, cnf)

    price = calc_price(df, window, spend)
    assert price == {"bar": 10.0, "baz": 10.0, "foo": 10.0}


def test_proportional_budget_optimizes_all_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, expected = proportional_budget(goal, spend, tot, price, 100, 10, 1)
    assert budget["foo"] == 39
    assert budget["bar"] == 30
    assert budget["baz"] == 30
    assert expected["foo"] == 3.9
    assert expected["bar"] == 4
    assert expected["baz"] == 4.0


def test_proportional_budget_drops_strata_under_min_to_min_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100, 16, 2)
    assert budget["foo"] == 19
    assert budget["bar"] == 16
    assert budget["baz"] == 16


def test_proportional_budget_can_drop_to_zero_budget():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 10, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100, 16, 2)
    assert budget["foo"] == 27
    assert budget["bar"] == 0
    assert budget["baz"] == 22


def test_proportional_budget_prioritizes_underperforming_when_its_obvious():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 5, "baz": 5, "foo": 2}
    price = {"bar": 20.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100, 16, 2)
    assert budget["foo"] == 38
    assert budget["bar"] == 16
    assert budget["baz"] == 16


def test_proportional_budget_prioritizes_underperforming_even_at_high_cost():
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
    tot = {"bar": 20, "baz": 10, "foo": 2}
    price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 1 / 3}
    budget, _ = proportional_budget(goal, spend, tot, price, 100, 16, 2)
    assert budget["foo"] == 50
    assert budget["bar"] == 0
    assert budget["baz"] == 0


def test_proportional_budget_raises_exception_when_not_near_one():
    spend = {"bar": 10.0, "baz": 10.0, "foo": 0.0}
    tot = {"bar": 1, "baz": 1, "foo": 0}
    price = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    goal = {"foo": 1 / 3, "bar": 1 / 3, "baz": 2 / 3}
    with pytest.raises(Exception):
        proportional_budget(goal, spend, tot, price, 100, 16, 2)


def test_get_budget_lookup(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    res, _ = get_budget_lookup(df, cnf, 30, 1, window, spend, 100, 5)
    assert res == {"bar": 2.0, "baz": 2.0, "foo": 8.0}


def test_get_budget_lookup_when_no_days_left(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    res, _ = get_budget_lookup(df, cnf, 30, 1, window, spend, 100, 0)
    assert res == {"bar": 0.0, "baz": 0.0, "foo": 0.0}


# def test_get_budget_lookup_with_proportional_budget(cnf, df):
#     window = BudgetWindow(DATE, DATE)
#     spend = {"bar": 10.0, "baz": 10.0, "foo": 5.0}

#     res, _ = get_budget_lookup(df, cnf, 50, 1, window, spend, 30, 1, proportional=True)
#     assert round(res["bar"], 2) == 3.33
#     assert round(res["baz"], 2) == 3.33
#     assert round(res["foo"], 2) == 3.33


def test_get_budget_lookup_with_proportional_budget_when_budget_is_spent(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    res, _ = get_budget_lookup(df, cnf, 30, 1, window, spend, 0.3, 1, proportional=True)
    assert res == {"bar": 0, "baz": 0, "foo": 0}


def test_get_budget_lookup_respects_maximum_budget(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}

    res, _ = get_budget_lookup(df, cnf, 200, 1, window, spend, 100, 2)
    assert sum(res.values()) <= 200
    assert set(res.keys()) == {"bar", "baz", "foo"}


def test_get_budget_lookup_respects_min_budget(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 10.0}

    res, _ = get_budget_lookup(df, cnf, 500, 100, window, spend, 100, days_left=2)

    assert min(res.values()) >= 100
    assert sum(res.values()) <= 500
    assert set(res.keys()) == {"bar", "baz", "foo"}


def test_get_budget_lookup_returns_zero_for_saturated_clusters(cnf, df):
    cnf = conf(1)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 1000, 1, window, spend, 100, days_left=5)

    assert res == {"foo": 4.0, "bar": 0.0, "baz": 0.0}


def test_get_budget_lookup_handles_missing_spend_by_assuming_mean(cnf, df):
    spend = {"bar": 10.0}
    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 1000, 1, window, spend, 100, days_left=5)

    assert res == {"bar": 2.0, "foo": 4.0, "baz": 2.0}


def test_get_budget_lookup_handles_missing_spend_in_saturated_clusters(cnf, df):
    cnf = conf(1)
    spend = {"foo": 10.0}
    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 1000, 1, window, spend, 100, days_left=5)

    assert res == {"foo": 4.0, "bar": 0.0, "baz": 0.0}


def test_get_budget_lookup_handles_zero_spend_doesnt_affect_trimming(cnf, df):
    spend = {"foo": 10.0, "bar": 15.0, "baz": 20.0, "qux": 0.0}
    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 1000, 1, window, spend, 100, days_left=5)
    assert res == {"bar": 3, "foo": 8, "baz": 4}


def test_get_budget_lookup_handles_initial_conditions_with_min(cnf):
    spend = {}
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [],
        columns=cols,
    )

    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 1000, 1, window, spend, 0.1, days_left=1)
    assert res == {"bar": 1, "foo": 1, "baz": 1}

    res, _ = get_budget_lookup(df, cnf, 2000, 1, window, spend, 0.1, days_left=2)
    assert res == {"bar": 1, "foo": 1, "baz": 1}


def test_get_budget_lookup_works_with_missing_data_from_clusters(cnf):
    cnf = conf(1)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "bar", 2, "foo"),
            ("rand", "55", 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", "60", 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", "105", 4, "bar"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    spend = {"bar": 10.0, "foo": 10.0, "baz": 10.0}
    window = BudgetWindow(DATE, DATE)
    res, _ = get_budget_lookup(df, cnf, 20, 1, window, spend, 100, days_left=5)

    assert res == {"foo": 4.0, "bar": 0.0, "baz": 4.0}


def test_budget_trimming():
    budget = {"foo": 100, "bar": 25}
    assert budget_trimming(budget, 100, 1, 1) == {"foo": 75, "bar": 25}

    budget = {"foo": 100, "bar": 75, "baz": 25}
    assert budget_trimming(budget, 75, 1, 1) == {"foo": 25, "bar": 25, "baz": 25}

    budget = {"foo": 100, "bar": 75, "baz": 25}
    assert budget_trimming(budget, 50, 1, 1) == {"foo": 16, "bar": 16, "baz": 16}


def test_budget_trimming_throws_when_impossible():
    budget = {"foo": 100, "bar": 25}
    with pytest.raises(Exception):
        budget_trimming(budget, 30, 15, 10)


def test_make_report():
    r = make_report(
        [("goal", {"foo": 100, "bar": 10}), ("remain", {"foo": 90, "bar": 0})]
    )

    assert r["foo"] == {"goal": 100, "remain": 90}
    assert r["bar"] == {"goal": 10, "remain": 0}
