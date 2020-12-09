import logging
import warnings
from math import floor
from statistics import mean
from typing import Dict, List, Optional, Union

import pandas as pd

from .facebook.state import BudgetWindow
from .forms import TranslationError
from .marketing import AudienceConf, Stratum, StratumConf, TargetQuestion


class MissingResponseError(BaseException):
    pass


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
    return [(q.ref, make_pred(q)) for q in target_questions]


def _latest_survey(df):
    return df[df.surveyid == df.sort_values("timestamp").surveyid.unique()[-1]]


def only_latest_survey(df):

    # Clean anyone who answered multiple surveys in this group of shortcodes
    # in theory should only be testers.
    # Keep the lastest survey they took.
    # return df.sort_values("timestamp").drop_duplicates(["userid"], keep="last")
    return df.groupby(["shortcode", "userid"]).apply(_latest_survey)


def shape_df(df):
    try:
        return only_latest_survey(df)
    except KeyError:
        return df


def _filter_by_response(df, ref, pred):
    if df.shape[0] == 0:
        return df
    d = df[df.question_ref == ref].reset_index(drop=True)
    mask = d.apply(pred, 1)
    users = d[mask].userid.unique()
    return df[df.userid.isin(users)].reset_index(drop=True)


def users_fulfilling(treqs, df):
    for ref, pred in treqs:
        try:
            df = _filter_by_response(df, ref, pred)
        except KeyError:
            return None
        except AttributeError:
            return None

    return df


def make_pred(q: TargetQuestion):
    fns = {
        "answered": lambda a, _: pd.notna(a),
        "not_equal": lambda a, b: a != b,
        "equal": lambda a, b: a == b,
        "greater_than": lambda a, b: a > b,
        "less_than": lambda a, b: a < b,
    }

    try:
        fn = fns[q.op]
    except KeyError:
        raise TypeError(f"op function: {q.op} is not supported!")

    return lambda x: fn(x[q.field], q.value)


def only_target_users(
    df, stratum: Union[Stratum, StratumConf, AudienceConf], fn=users_fulfilling
):

    reqs = make_reqs(stratum.target_questions)
    df = df[df.shortcode.isin(stratum.shortcodes)]
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

    saturated = [s.id for s, d in dfs if d.userid.unique().shape[0] >= s.quota]
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


def _users_per_cluster(df):
    return df.groupby("cluster").apply(lambda df: df.userid.unique().shape[0]).to_dict()


def calc_price(df, window, spend):
    # filter by time
    def pred(st):
        return st.response >= window.start_unix and st.response <= window.until_unix

    windowed = _filter_by_response(df, "md:startTime", pred)

    counts = _users_per_cluster(windowed)
    counts = {**{k: 1 for k in spend.keys()}, **counts}
    price = {k: spend[k] / v for k, v in counts.items() if k in spend}

    # set to mean if we don't have info on the price
    m = mean([p for p in price.values() if p != 0])
    make_mean = lambda v: v if v != 0 else m
    price = {k: make_mean(v) for k, v in price.items()}

    return price


def prep_df_for_budget(df, strata):
    # get all unique target_question and response_surveys
    # so that you can add them all???
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [d.assign(cluster=s.id) for s, d in dfs if d is not None]

    if not dfs:
        return None

    return pd.concat(dfs).reset_index(drop=True)


def proportional_budget(budget, max_budget, min_budget):
    while sum(budget.values()) > max_budget:
        s = sum(budget.values())
        budget = {k: floor(max_budget * (v / s)) for k, v in budget.items()}
        budget = {k: max(min_budget, v) for k, v in budget.items()}

    return budget


def _base_budget(strata, max_budget, min_budget):
    budget = {s.id: max_budget for s in strata}
    return proportional_budget(budget, max_budget, min_budget)


def get_budget_lookup(
    df: Optional[pd.DataFrame],
    strata: List[Union[Stratum, StratumConf]],
    max_budget: float,
    min_budget: float,
    window: BudgetWindow,
    spend: Dict[str, float],
    days_left: int = None,
    proportional: bool = False,
    return_price: bool = False,
):

    if proportional and days_left is not None:
        warnings.warn("days_left is ignored in proportional budget optimization")

    if not proportional and days_left is None:
        raise Exception("days_left is required if proportional is False")

    if days_left is None:
        days_left = 1

    df = prep_df_for_budget(df, strata) if df is not None else None

    if df is None:
        return _base_budget(strata, max_budget, min_budget)

    # make a spend lookup that has 0 for all clusters
    # in strata with no spend and then optimize only
    # for those given in the strata.
    goal_lookup = {s.id: s.quota for s in strata}
    spend = {k: v for k, v in spend.items() if k in goal_lookup}
    spend = {**{s.id: 0 for s in strata}, **spend}

    # unique users
    tot = _users_per_cluster(df)
    tot = {**{k: 0 for k in spend.keys()}, **tot}

    remain = {k: goal_lookup[k] - v for k, v in tot.items()}
    saturated = {k for k, v in remain.items() if v <= 0}

    price = calc_price(df, window, spend)

    budget = {k: v * remain[k] / days_left for k, v in price.items()}
    budget = {k: floor(v) for k, v in budget.items()}
    budget = {**budget, **{k: 0 for k in saturated}}

    zeroed = {k for k, v in budget.items() if v == 0.0}
    budget = {k: v for k, v in budget.items() if k not in zeroed}

    # from here, you can move to proportion or target
    # days_left can be replaced with 1 if proportion targeting
    if proportional:
        budget = proportional_budget(budget, max_budget, min_budget)
    else:
        budget = budget_trimming(budget, max_budget, min_budget)

    # add zero spend strata back in!
    budget = {**budget, **{k: 0 for k in zeroed}}

    if return_price:
        return budget, price
    return budget
