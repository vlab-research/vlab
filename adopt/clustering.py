import logging
import warnings
from datetime import datetime, timezone
from math import floor
from typing import Dict, List, NamedTuple, Optional

import pandas as pd

from .facebook.state import BudgetWindow
from .forms import TranslationError
from .marketing import FacebookTargeting


class MissingResponseError(BaseException):
    pass


class TargetQuestion(NamedTuple):
    name: str
    ref: str
    op: str
    field: str
    value: Optional[str]


class Stratum(NamedTuple):
    id: str
    metadata: Dict[str, str]
    facebook_targeting: FacebookTargeting
    quota: int
    creative_group: str
    custom_audience: str
    shortcodes: List[str]
    target_questions: List[TargetQuestion]


def res_col(ref, row, t):
    response = row[ref]

    if pd.isna(response):
        raise MissingResponseError("user missing response")

    return t(response)


def _res_col(ref, col_name, t, row):
    try:
        row[col_name] = res_col(ref, row, t)
    except MissingResponseError:
        logging.warning(f"User without {col_name}: {row.userid}")
        row[col_name] = None
    except TranslationError:
        row[col_name] = None

    return row


def add_res_cols(new_cols, df):
    for col, ref, t in new_cols:
        df = df.apply(lambda r: _res_col(ref, col, t, r), axis=1)
    return df


def make_reqs(target_questions):
    return [(q["ref"], make_pred(q)) for q in target_questions]


def shape_df(df):
    df = (
        df.groupby(["surveyid", "shortcode"])
        .apply(lambda df: df.pivot("userid", "question_ref", "response"))
        .reset_index()
    )

    df["timestamp"] = df["md:startTime"].map(
        lambda x: datetime.fromtimestamp(x / 1000, tz=timezone.utc)
    )

    # Clean anyone who answered multiple surveys in this group of shortcodes
    # in theory should only be testers.
    # Keep the lastest survey they took.
    return df.sort_values("timestamp").drop_duplicates(["userid"], keep="last")


def users_fulfilling(treqs, df):
    for ref, pred in treqs:
        try:
            d = df[df[ref].map(pred)]
            users = d.userid.unique()
            df = df[df.userid.isin(users)]
        except KeyError:
            return None
        except AttributeError:
            return None

    return df


def users_answering(treqs, df):
    for ref, _ in treqs:
        try:
            d = df[~df[ref].isna()]
            users = d.userid.unique()
            df = df[df.userid.isin(users)]
        except AttributeError:
            return None

    return df


def make_pred(q):
    fns = {
        "answered": lambda a, _: pd.notna(a),
        "not_equal": lambda a, b: a != b,
        "equal": lambda a, b: a == b,
        "greater_than": lambda a, b: a > b,
        "less_than": lambda a, b: a < b,
    }

    try:
        fn = fns[q["op"]]
    except KeyError:
        raise TypeError(f"op function: {q['op']} is not supported!")

    return lambda x: fn(x, q["value"])


def only_target_users(df, stratum, fn=users_fulfilling):
    reqs = make_reqs(stratum["target_questions"])
    df = df[df.shortcode.isin(stratum["shortcodes"])]
    if df.shape[0] == 0:
        return None

    filtered = fn(reqs, df)
    if filtered is None:
        return None

    if filtered.shape[0] == 0:
        return None

    return filtered


def get_saturated_clusters(df, strata):
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [(s, d) for s, d in dfs if d is not None]

    saturated = [s["id"] for s, d in dfs if d.userid.unique().shape[0] >= s["quota"]]
    return saturated


def budget_trimming(budget, max_budget, min_budget, step=100):
    budg = {k: max(min_budget, v) for k, v in budget.items()}
    mx = max(budg.values())
    while sum(budg.values()) > max_budget:
        mx = mx - step
        if mx < min_budget:
            raise Exception(
                "Cant make the budget work, minimum under 0! Reduce step size?"
            )
        budg = {k: min(v, mx) for k, v in budg.items()}
    return budg


def calc_price(df, window, spend):
    # filter out anything that hasn't been spent in the last day
    # TODO: Make this constraint explicit or get rid of it.
    # it means you can never increase the number of clusters
    spend = {k: v for k, v in spend.items() if v > 0}

    # filter by time
    windowed = df[
        (df["md:startTime"] >= window.start_unix)
        & (df["md:startTime"] <= window.until_unix)
    ]
    counts = windowed.groupby("cluster").userid.count().to_dict()
    counts = {**{k: 1 for k in spend.keys()}, **counts}
    price = {k: spend[k] / v for k, v in counts.items() if k in spend}

    return price


def prep_df_for_budget(df, strata):
    # get all unique target_question and response_surveys
    # so that you can add them all???
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [d.assign(cluster=s["id"]) for s, d in dfs if d is not None]

    if not dfs:
        return None

    return pd.concat(dfs)


def proportional_budget(budget, max_budget, min_budget):
    while sum(budget.values()) > max_budget:
        s = sum(budget.values())
        budget = {k: floor(max_budget * (v / s)) for k, v in budget.items()}
        budget = {k: max(min_budget, v) for k, v in budget.items()}

    return budget


def _base_budget(strata, max_budget, min_budget):
    budget = {s["id"]: max_budget for s in strata}
    return proportional_budget(budget, max_budget, min_budget)


def get_budget_lookup(
    df,
    strata,
    max_budget,
    min_budget,
    window: BudgetWindow,
    spend: Dict[str, float],
    days_left=None,
    proportional=False,
    return_price=False,
):

    if proportional and days_left is not None:
        warnings.warn("days_left is ignored in proportional budget optimization")

    if not proportional and days_left is None:
        raise Exception("days_left is required if proportional is False")

    if days_left is None:
        days_left = 1

    df = prep_df_for_budget(df, strata)
    if df is None:
        return _base_budget(strata, max_budget, min_budget)

    # make a spend lookup that has 0 for all clusters
    # in strata with no spend and then optimize only
    # for those given in the strata.
    goal_lookup = {s["id"]: s["quota"] for s in strata}
    spend = {k: v for k, v in spend.items() if k in goal_lookup}
    tot = df.groupby("cluster").userid.count().to_dict()
    tot = {**{k: 0 for k in spend.keys()}, **tot}

    remain = {k: goal_lookup[k] - v for k, v in tot.items()}
    saturated = [k for k, v in remain.items() if v <= 0]

    price = calc_price(df, window, spend)

    budget = {k: v * remain[k] / days_left for k, v in price.items()}
    budget = {k: floor(v) for k, v in budget.items()}
    budget = {**budget, **{k: 0 for k in saturated}}
    budget = {k: v for k, v in budget.items() if v > 0.0}

    # from here, you can move to proportion or target
    # days_left can be replaced with 1 if proportion targeting
    if proportional:
        budget = proportional_budget(budget, max_budget, min_budget)
    else:
        budget = budget_trimming(budget, max_budget, min_budget)

    if return_price:
        return budget, price
    return budget
