import logging
from functools import reduce
from math import floor
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, minimize

from .facebook.state import BudgetWindow
from .forms import TranslationError
from .marketing import (AudienceConf, QuestionTargeting, Stratum, StratumConf,
                        TargetVar)


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


def _latest_survey(df):
    return df[df.surveyid == df.sort_values("timestamp").surveyid.unique()[-1]]


def only_latest_survey(df):

    # Clean anyone who answered multiple surveys in this group of shortcodes
    # in theory should only be testers.
    # Keep the lastest survey they took.
    # return df.sort_values("timestamp").drop_duplicates(["userid"], keep="last")
    return (
        df.groupby(["shortcode", "userid"]).apply(_latest_survey).reset_index(drop=True)
    )


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


def get_var(v: Union[TargetVar, QuestionTargeting], d: Dict[str, Any]):
    if isinstance(v, QuestionTargeting):
        return make_pred(v)(d)

    if not isinstance(v, TargetVar):
        raise Exception(
            f"get_var must be passed TargetVar or QuestionTargeting. Was passed: {v}"
        )

    type_, value = v

    if type_ == "constant":
        return value

    if type_ in {"response", "translated_response"}:

        try:
            ans = d[type_][value]
            return ans
        except KeyError:
            return None

    raise Exception(f"Target Question Type not valid: {type_}")


def wrap(fn):
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TypeError:
            return False
        except ValueError:
            return False

    return _wrapped


def make_pred(q: Optional[QuestionTargeting]) -> Callable[[pd.DataFrame], bool]:
    if q is None:
        return lambda _: True

    fns = {
        "and": lambda a, b: a and b,
        "or": lambda a, b: a or b,
        "answered": lambda a, _: pd.notna(a),
        "not_equal": lambda a, b: pd.notna(a) and pd.notna(b) and a != b,
        "equal": lambda a, b: a == b,
        "greater_than": lambda a, b: float(a) > float(b),
        "less_than": lambda a, b: float(a) < float(b),
    }

    try:
        fn = fns[q.op]
        fn = wrap(fn)

    except KeyError as e:
        raise TypeError(f"op function: {q.op} is not supported!") from e

    if len(q.vars) == 1:
        v = q.vars[0]
        return lambda df: fn(get_var(v, df), None)

    vars_ = q.vars
    return lambda d: reduce(fn, [get_var(var, d) for var in vars_])


def users_fulfilling(pred, df):
    dis = [
        (u, df.to_dict()) for u, df in df.set_index("question_ref").groupby("userid")
    ]
    users = {u for u, d in dis if pred(d)}
    return df[df.userid.isin(users)]


def only_target_users(
    df, stratum: Union[Stratum, StratumConf, AudienceConf], fn=users_fulfilling
):

    pred = make_pred(stratum.question_targeting)
    df = df[df.shortcode.isin(stratum.shortcodes)]
    if df.shape[0] == 0:
        return None

    filtered = fn(pred, df)

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


class AdDataError(BaseException):
    pass


def calc_price(df, window, spend):
    # filter by time
    def pred(st):
        return st.response >= window.start_unix and st.response <= window.until_unix

    windowed = _filter_by_response(df, "md:startTime", pred)

    counts = _users_per_cluster(windowed)
    counts = {**{k: 0.5 for k in spend.keys()}, **counts}
    price = {k: spend[k] / v for k, v in counts.items() if k in spend}

    # set to mean if we don't have info on the price
    non_zeros = [p for p in price.values() if p != 0]
    if not non_zeros:
        raise AdDataError(
            f"Could not calculate the price of any adset "
            f"between {window.start} and {window.until}"
        )
    m = mean(non_zeros)
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


def constrained_opt(S, goal, tot, price, budget):
    C = 1 / price
    s = S / S.sum()
    new_spend = s * budget
    projection = C * new_spend + tot
    loss = np.sum(goal ** 2 / projection)
    return loss*100


def proportional_opt(goal, tot, price, budget, tol=0.01):
    P = goal.shape[0]
    x0 = np.repeat(1, P)
    x0 = x0 / x0.sum()

    m = minimize(
        constrained_opt,
        x0=x0,
        args=(goal, tot, price, budget),
        method="L-BFGS-B",
        bounds=[(0, None)] * P,
        options={'ftol': 1e-14, 'gtol': 1e-10, 'eps': 1e-12}
    )

    logging.info(f"Finished optimizing with loss: {m.fun}")

    if m.fun / P > tol:
        logging.warning(f"Optimization loss very high: {m.fun}")

    new_spend = (m.x / m.x.sum()) * budget

    return new_spend


def proportional_budget(
    goal,
    spend,
    tot,
    price,
    budget,
    min_budget,
    days_left,
):

    if not np.isclose(sum(goal.values()), 1.0, 0.01):
        raise Exception(
            f"proportional_budget needs a goal that sums to one. was given: {goal}"
        )

    df = pd.DataFrame(
        {
            "goal": goal,
            "spend": spend,
            "respondents": tot,
            "price": price,
        }
    )

    new_spend = proportional_opt(
        df.goal.values, df.respondents.values, df.price.values, budget
    )

    new_spend /= days_left

    new_spend = [floor(s) for s in new_spend]
    df["new_spend"] = [min_budget if s > 0 and s < min_budget else s for s in new_spend]

    df["expected"] = df.respondents + ((df.new_spend / df.price) * days_left)

    return df.new_spend.to_dict(), df.expected.to_dict()


def _base_budget(strata, max_budget, min_budget):
    budget = {s.id: min_budget for s in strata}
    return budget


def _off_budget(strata):
    return {s.id: 0 for s in strata}


AdOptReport = Dict[str, Dict[str, Union[int, float]]]


def make_report(facts: List[Tuple[str, Dict[str, Any]]]) -> AdOptReport:

    d: AdOptReport = {}

    for k, fact in facts:
        for i, f in fact.items():
            try:
                d[i][k] = f
            except KeyError:
                d[i] = {k: f}

    return d


def _normalize_values(di):
    t = sum(di.values())
    return {k: v / t for k, v in di.items()}


def normalize_goal(strata):
    goal = {s.id: s.quota for s in strata}
    t = sum([gg for _, gg in goal.items()])
    return {k: v / t for k, v in goal.items()}


def get_stats(
    df: Optional[pd.DataFrame],
    strata: Sequence[Union[Stratum, StratumConf]],
    window: BudgetWindow,
    spend: Dict[str, float],
):

    optimized_ids = {s.id for s in strata}

    spend = {k: v for k, v in spend.items() if k in optimized_ids}
    spend = {**{s.id: 0 for s in strata}, **spend}

    respondents = _users_per_cluster(df)
    respondents = {**{k: 0 for k in spend.keys()}, **respondents}

    price = calc_price(df, window, spend)

    return spend, respondents, price


# TODO: add frequency -- at least to report if nothing automated
# probably more elegant just to change "spend" to "insights"

# TODO: we need a more sophisticated process to estimate price.
# The "BudgetWindow" creates a problem here, it's too miopic
# If an adset has been turned off for a few days, we forget
# all information we have about price. Similarly, for very
# high priced strata, we chronically underestimate the price.
#
# Solution: Create a separate job that collects insights data,
# for each single day, for all active campaigns, and stores
# them in your database. Then use that timeseries to actually
# create a reasonable estimate of the price of each user.
def get_budget_lookup(
    df: Optional[pd.DataFrame],
    strata: Sequence[Union[Stratum, StratumConf]],
    max_budget: float,
    min_budget: float,
    window: BudgetWindow,
    spend: Dict[str, float],
    total_spend: float,
    days_left: int,
    proportional: bool = False,
) -> Tuple[Dict[str, float], Optional[AdOptReport]]:

    # TODO: fix total_spend and insights spend here
    total_spend = total_spend * 100

    if days_left == 0:
        return _off_budget(strata), None

    df = prep_df_for_budget(df, strata) if df is not None else None

    if df is None:
        logging.info("Falling back to base budget due to lack of response data")
        return _base_budget(strata, max_budget, min_budget), None

    try:
        spend, tot, price = get_stats(df, strata, window, spend)
    except AdDataError as e:
        logging.info(f"Falling back to base budget due to the follow error: {e}")
        return _base_budget(strata, max_budget, min_budget), None

    share = _normalize_values(tot)

    if proportional:
        to_spend = max_budget - total_spend

        if to_spend <= 0:
            logging.info("No money left in the budget!")
            return _off_budget(strata), None

        goal = _normalize_values({s.id: s.quota for s in strata})
        budget, expected = proportional_budget(
            goal,
            spend,
            tot,
            price,
            to_spend,
            min_budget,
            days_left,
        )

        report = make_report(
            [
                ("price", price),
                ("spend", spend),
                ("goal", goal),
                ("respondents", tot),
                ("respondent_share", share),
                ("budget", budget),
                ("expected", expected),
                ("expected_share", _normalize_values(expected)),
            ]
        )
        return budget, report

    goal_lookup = {s.id: s.quota for s in strata}
    remain = {k: goal_lookup[k] - v for k, v in tot.items()}
    saturated = {k for k, v in remain.items() if v <= 0}

    budget = {k: v * remain[k] / days_left for k, v in price.items()}
    budget = {k: floor(v) for k, v in budget.items()}
    budget = {**budget, **{k: 0 for k in saturated}}

    zeroed = {k for k, v in budget.items() if v == 0.0}
    budget = {k: v for k, v in budget.items() if k not in zeroed}

    budget = budget_trimming(budget, max_budget, min_budget)

    # add zero spend strata back in!
    budget = {**budget, **{k: 0 for k in zeroed}}

    report = make_report(
        [
            ("price", price),
            ("spend", spend),
            ("goal", goal_lookup),
            ("remaining", remain),
            ("respondents", tot),
            ("budget", budget),
        ]
    )

    return budget, report
