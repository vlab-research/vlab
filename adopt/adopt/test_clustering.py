from datetime import datetime

import pandas as pd
import pytest

from .clustering import get_saturated_clusters, only_target_users
from .facebook.date_range import DateRange, unix_time_millis
from .study_conf import StratumConf

DATE = datetime(2020, 1, 1)


def make_stratum_conf(d):
    return StratumConf(**d)


def make_conf(c):
    return [make_stratum_conf(d) for d in c]


def conf(quota=2, field="variable"):
    c = [
        {
            "id": "foo",
            "quota": quota,
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
                            {"type": "variable", "value": "dist"},
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
                            {"type": "variable", "value": "dist"},
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
                            {"type": "variable", "value": "dist"},
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
        df.groupby(["user_id"])
        .apply(
            lambda df: df.append(
                [
                    {
                        **df.iloc[0].to_dict(),
                        "variable": "md:startTime",
                        "value": unix_time_millis(DATE),
                    }
                ]
            )
        )
        .reset_index(drop=True)
    )


def _format_df(df):
    df = _add_time(df)
    df = _add_timestamp(df)
    return df


# question_ref -> variable
# response ->. value
# userid -> user_id
# shortcode -> no longer applicable,
# inference data conf should take care of it
@pytest.fixture
def df():
    cols = ["variable", "value", "user_id"]
    d = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "50", 1),
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rand", "105", 4),
            ("dist", "baz", 5),
            ("rand", "105", 5),
        ],
        columns=cols,
    )
    return _format_df(d)


def test_get_only_target_users_with_empty_target_questions_filters_none(df):
    s = {
        "id": "foo",
        "quota": 1,
        "creatives": [],
        "audiences": [],
        "excluded_audiences": [],
        "facebook_targeting": {},
        "metadata": {},
        "question_targeting": None,
    }

    stratum = make_stratum_conf(s)
    res = only_target_users(df, stratum)
    assert res.equals(df)


def test_only_target_users_works_with_number_predicates(cnf):
    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "50", 1),
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "101", 3),
            ("dist", "bar", 4),
            ("rand", "103", 4),
            ("dist", "baz", 5),
            ("rand", "99", 5),
        ],
        columns=cols,
    )
    df = _format_df(df)

    users = only_target_users(df, cnf[1])
    assert set(users.user_id.unique().tolist()) == {3, 4}


def test_only_target_users_ignores_poorly_formated_numbers(cnf):
    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "50", 1),
            ("dist", "bar", 2),
            ("rand", "jkljk", 2),
            ("dist", "bar", 3),
            ("rand", "101", 3),
            ("dist", "bar", 4),
            ("rand", "103", 4),
            ("dist", "baz", 5),
            ("rand", "99", 5),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == ["bar"]


def test_get_saturated_clusters_with_some_users_no_cluster(cnf):
    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "50", 1),
            ("rand", "55", 2),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rand", "105", 4),
            ("dist", "baz", 5),
            ("rand", "99", 5),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)

    assert res == []


def test_get_saturated_clusters_with_no_fulfilled(cnf):
    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "50", 1),
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rand", "105", 4),
            ("dist", "baz", 5),
            ("rand", "99", 5),
        ],
        columns=cols,
    )
    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)

    assert res == []


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
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "dist"},
                            {"type": "constant", "value": "foo"},
                        ],
                    },
                    {
                        "op": "greater_than",
                        "vars": [
                            {"type": "variable", "value": "rand"},
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
            "question_targeting": {
                "op": "and",
                "vars": [
                    {
                        "op": "equal",
                        "vars": [
                            {"type": "variable", "value": "dood"},
                            {"type": "constant", "value": "bar"},
                        ],
                    },
                    {
                        "op": "less_than",
                        "vars": [
                            {"type": "variable", "value": "rand"},
                            {"type": "constant", "value": 100},
                        ],
                    },
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "105", 1),
            ("dood", "bar", 2),
            ("rand", "55", 2),
            ("dood", "bar", 3),
            ("rand", "60", 3),
            ("dood", "bar", 4),
            ("rook", 50, 4),
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
                            {"type": "variable", "value": "dist"},
                            {"type": "constant", "value": "foo"},
                        ],
                    },
                    {
                        "op": "or",
                        "vars": [
                            {
                                "op": "greater_than",
                                "vars": [
                                    {"type": "variable", "value": "rand"},
                                    {"type": "constant", "value": 100},
                                ],
                            },
                            {
                                "op": "equal",
                                "vars": [
                                    {"type": "variable", "value": "rand"},
                                    {"type": "constant", "value": 999},
                                ],
                            },
                            {
                                "op": "less_than",
                                "vars": [
                                    {"type": "variable", "value": "rand"},
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
                            {"type": "variable", "value": "dist"},
                            {"type": "constant", "value": "bar"},
                        ],
                    },
                    {
                        "op": "or",
                        "vars": [
                            {
                                "op": "greater_than",
                                "vars": [
                                    {"type": "variable", "value": "rand"},
                                    {"type": "constant", "value": 100},
                                ],
                            },
                            {
                                "op": "less_than",
                                "vars": [
                                    {"type": "variable", "value": "rand"},
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

    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "105", 1),
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rand", "50", 4),
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
            "question_targeting": {
                "op": "answered",
                "vars": [{"type": "variable", "value": "rand"}],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("dist", "foo", 1),
            ("rand", "105", 1),
            ("dist", "bar", 2),
            ("rand", "55", 2),
            ("dist", "bar", 3),
            ("rand", "60", 3),
            ("dist", "bar", 4),
            ("rook", 50, 4),
            ("dist", "foo", 5),
            ("rook", 105, 5),
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
            "question_targeting": {
                "op": "not_equal",
                "vars": [
                    {"type": "variable", "value": "rook"},
                    {"type": "constant", "value": "105"},
                ],
            },
        },
    ]
    cnf = make_conf(s)

    cols = ["variable", "value", "user_id"]
    df = pd.DataFrame(
        [
            ("rand", "105", 1),
            ("rand", "55", 2),
            ("rand", "60", 3),
            ("rook", "105", 1),
            ("rook", "105", 2),
        ],
        columns=cols,
    )

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf)
    assert res == []
