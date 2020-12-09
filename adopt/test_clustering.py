from datetime import datetime

import pandas as pd
import pytest

from .clustering import (budget_trimming, get_budget_lookup,
                         get_saturated_clusters, only_latest_survey,
                         only_target_users, proportional_budget, shape_df,
                         users_fulfilling)
from .facebook.state import BudgetWindow, unix_time_millis
from .marketing import StratumConf, parse_conf

DATE = datetime(2020, 1, 1)


def make_conf(c):
    return parse_conf({"audiences": [], "strata": c})


def conf(quota=2, field="response"):
    c = [
        {
            "id": "foo",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "target_questions": [
                {"ref": "dist", "op": "equal", "field": "response", "value": "foo"},
                {
                    "ref": "rand",
                    "op": "greater_than",
                    "field": field,
                    "value": 100,
                },
            ],
        },
        {
            "id": "bar",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "target_questions": [
                {"ref": "dist", "op": "equal", "field": "response", "value": "bar"},
                {
                    "ref": "rand",
                    "op": "greater_than",
                    "field": field,
                    "value": 100,
                },
            ],
        },
        {
            "id": "baz",
            "quota": quota,
            "shortcodes": ["foo", "bar"],
            "creatives": [],
            "target_questions": [
                {"ref": "dist", "op": "equal", "field": "response", "value": "baz"},
                {
                    "ref": "rand",
                    "op": "greater_than",
                    "field": field,
                    "value": 100,
                },
            ],
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
            ("rand", 50, 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 60, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", 105, 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", 105, 5, "bar"),
        ],
        columns=cols,
    )
    return _format_df(d)


def test_only_latest_survey_removes_duplicate_surveyids_per_user():
    cols = ["question_ref", "response", "userid", "shortcode", "surveyid"]
    d = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo", "bar"),
            ("rand", 50, 1, "foo", "bar"),
            ("dist", "fooz", 1, "foo", "baz"),
            ("dist", "bar", 2, "foo", "foo"),
            ("rand", 55, 2, "foo", "foo"),
            ("dist", "bar", 3, "foo", "foo"),
            ("rand", 60, 3, "foo", "foo"),
            ("dist", "bar", 4, "bar", "foo"),
            ("rand", 105, 4, "bar", "foo"),
        ],
        columns=cols,
    )

    df = only_latest_survey(_add_timestamp(d))
    assert df.shape[0] == 7
    assert df[df.userid == 1].response.tolist() == ["fooz"]


# def test_shape_df_removes_duplicate_surveyids_per_user():
# pass


def test_user_fulfilling_multiple(cnf):
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 50, 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 101, 3, "foo"),
            ("dist", "bar", 4, "foo"),
            ("rand", 103, 4, "foo"),
            ("dist", "baz", 5, "foo"),
            ("rand", 103, 5, "foo"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    out = users_fulfilling(
        [
            ("rand", lambda x: x.response > 100),
            ("rand", lambda x: x.response < 103),
            ("dist", lambda x: x.response == "bar"),
        ],
        df,
    )

    assert out.userid.unique().tolist() == [3]


def test_get_only_target_users_with_empty_target_questions_filters_none(df):
    s = {
        "id": "foo",
        "quota": 1,
        "creatives": [],
        "shortcodes": ["foo", "bar"],
        "audiences": [],
        "excluded_audiences": [],
        "target_questions": [],
    }

    stratum = StratumConf(**s)
    res = only_target_users(df, stratum)
    assert res.equals(df)


def test_get_saturated_clusters_with_some_fulfilled(cnf):

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 50, 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 101, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", 103, 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", 99, 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)
    assert res == ["bar"]


def test_get_saturated_clusters_with_some_fulfilled_on_translated_response():
    cnf = conf(2, "translated_response")
    print([s.target_questions for s in cnf.strata])
    cols = ["question_ref", "response", "translated_response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", None, 1, "foo"),
            ("rand", 50, 50, 1, "foo"),
            ("dist", "bar", None, 2, "foo"),
            ("rand", 55, 55, 2, "foo"),
            ("dist", "bar", None, 3, "foo"),
            ("rand", 101, 101, 3, "foo"),
            ("dist", "bar", None, 4, "bar"),
            ("rand", 103, 103, 4, "bar"),
            ("dist", "baz", None, 5, "bar"),
            ("rand", 99, 99, 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)
    assert res == ["bar"]


def test_get_saturated_clusters_with_some_users_no_cluster(cnf):
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 50, 1, "foo"),
            ("rand", 55, 2, "foo"),
            ("rand", 60, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", 105, 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", 99, 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)

    assert res == []


def test_get_saturated_clusters_with_no_fulfilled(cnf):
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 50, 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 60, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", 105, 4, "bar"),
            ("dist", "baz", 5, "bar"),
            ("rand", 99, 5, "bar"),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)

    assert res == []


def test_get_saturated_clusters_filters_only_appropriate_shortcodes():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "shortcodes": ["foo"],
            "target_questions": [
                {
                    "ref": "rand",
                    "op": "greater_than",
                    "field": "response",
                    "value": 100,
                },
            ],
        },
        {
            "id": "barfoo",
            "quota": 1,
            "creatives": [],
            "shortcodes": ["bar"],
            "target_questions": [
                {
                    "ref": "rook",
                    "op": "greater_than",
                    "field": "response",
                    "value": 100,
                },
            ],
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 105, 1, "foo"),
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 60, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rook", 50, 4, "bar"),
            ("dist", "foo", 5, "foo"),
            ("rook", 105, 5, "foo"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)
    assert res == ["foo"]


def test_get_saturated_clusters_with_different_id_fields():

    s = [
        {
            "id": "foo",
            "quota": 1,
            "creatives": [],
            "shortcodes": ["foo", "bar"],
            "target_questions": [
                {"ref": "dist", "op": "equal", "field": "response", "value": "foo"},
                {
                    "ref": "rand",
                    "op": "greater_than",
                    "field": "response",
                    "value": 100,
                },
            ],
        },
        {
            "id": "bar",
            "quota": 1,
            "creatives": [],
            "shortcodes": ["foo", "bar"],
            "target_questions": [
                {"ref": "dood", "op": "equal", "field": "response", "value": "bar"},
                {
                    "ref": "rook",
                    "op": "less_than",
                    "field": "response",
                    "value": 100,
                },
            ],
        },
    ]
    cnf = make_conf(s)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1, "foo"),
            ("rand", 105, 1, "foo"),
            ("dood", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dood", "bar", 3, "foo"),
            ("rand", 60, 3, "foo"),
            ("dood", "bar", 4, "bar"),
            ("rook", 50, 4, "bar"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf.strata)
    assert res == ["foo", "bar"]


def test_get_budget_lookup(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}

    res = get_budget_lookup(df, cnf.strata, 30, 1, window, spend, days_left=5)
    assert res == {"bar": 2.0, "baz": 2.0, "foo": 4.0}


def test_get_budget_lookup_respects_maximum_budget(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}

    res = get_budget_lookup(df, cnf.strata, 200, 1, window, spend, days_left=2)
    assert sum(res.values()) <= 200
    assert set(res.keys()) == {"bar", "baz", "foo"}


def test_get_budget_lookup_respects_min_budget(cnf, df):
    window = BudgetWindow(DATE, DATE)
    spend = {"bar": 100.0, "baz": 100.0, "foo": 10.0}

    res = get_budget_lookup(df, cnf.strata, 500, 100, window, spend, days_left=2)

    assert min(res.values()) >= 100
    assert sum(res.values()) <= 500
    assert set(res.keys()) == {"bar", "baz", "foo"}


# def test_get_budget_throws_when_min_and_max_incompatible(cnf, df):
#     window = BudgetWindow(DATE, DATE)
#     spend = {'bar': 50.0, 'baz': 50.0, 'foo': 10.0}

#     res = get_budget_lookup(df, cnf['stratum'], 150, 75, 10, 2, window, spend)

#     assert min(res.values()) >= 100
#     assert sum(res.values()) <= 200
#     assert set(res.keys()) == {'bar', 'baz', 'foo'}


def test_get_budget_lookup_returns_zero_for_saturated_clusters(cnf, df):
    cnf = conf(1)
    spend = {"bar": 10.0, "baz": 10.0, "foo": 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 1000, 1, window, spend, days_left=5)

    assert res == {"foo": 2.0, "bar": 0.0, "baz": 0.0}


def test_get_budget_lookup_handles_missing_spend_by_assuming_mean(cnf, df):
    spend = {"bar": 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 1000, 1, window, spend, days_left=5)

    assert res == {"bar": 2.0, "foo": 4.0, "baz": 2.0}


def test_get_budget_lookup_handles_missing_spend_in_saturated_clusters(cnf, df):
    cnf = conf(1)
    spend = {"foo": 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 1000, 1, window, spend, days_left=5)

    assert res == {"foo": 2.0, "bar": 0.0, "baz": 0.0}


def test_get_budget_lookup_handles_zero_spend_doesnt_affect_trimming(cnf, df):
    spend = {"foo": 10.0, "bar": 15.0, "baz": 20.0, "qux": 0.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 1000, 1, window, spend, days_left=5)
    assert res == {"bar": 3, "foo": 4, "baz": 4}


def test_get_budget_lookup_handles_initial_conditions(cnf):
    spend = {}
    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [],
        columns=cols,
    )

    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 1000, 1, window, spend, days_left=5)
    assert res == {"bar": 333, "foo": 333, "baz": 333}


def test_get_budget_lookup_works_with_missing_data_from_clusters(cnf):
    cnf = conf(1)

    cols = ["question_ref", "response", "userid", "shortcode"]
    df = pd.DataFrame(
        [
            ("dist", "bar", 2, "foo"),
            ("rand", 55, 2, "foo"),
            ("dist", "bar", 3, "foo"),
            ("rand", 60, 3, "foo"),
            ("dist", "bar", 4, "bar"),
            ("rand", 105, 4, "bar"),
        ],
        columns=cols,
    )

    df = _format_df(df)

    spend = {"bar": 10.0, "foo": 10.0, "baz": 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf.strata, 20, 1, window, spend, days_left=5)

    assert res == {"foo": 2.0, "bar": 0.0, "baz": 2.0}


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


def test_proportional_budget():
    budget = {"foo": 100, "bar": 25}
    assert proportional_budget(budget, 100, 20) == {"foo": 80, "bar": 20}

    budget = {"foo": 100, "bar": 75, "baz": 25}
    assert proportional_budget(budget, 75, 25) == {"foo": 25, "bar": 25, "baz": 25}

    budget = {"foo": 100, "bar": 25}
    print(proportional_budget(budget, 30, 15))


def test_proportional_budget_evenly_spreads_the_burden():
    budget = {"foo": 100, "bar": 75, "baz": 25}
    assert proportional_budget(budget, 75, 1) == {"foo": 37, "bar": 28, "baz": 9}

    budget = {"foo": 100, "bar": 75, "baz": 25}
    assert proportional_budget(budget, 75, 15) == {"foo": 34, "bar": 26, "baz": 15}
