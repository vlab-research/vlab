import logging
from math import ceil
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .clustering import _users_by_predicate, only_target_users
from .facebook.state import DateRange
from .study_conf import Budget, Stratum, StratumConf


def _filter_by_join_time(df: pd.DataFrame, pred: Callable[[pd.Series], bool]):
    initial_events = (
        df.groupby("user_id")
        .apply(lambda df: df.sort_values("timestamp").iloc[0])
        .reset_index(drop=True)
    )

    users = _users_by_predicate(initial_events, pred)

    return df[df.user_id.isin(users)].reset_index(drop=True)


def _users_per_cluster(df: pd.DataFrame) -> dict[str, int]:
    if df.shape[0] == 0:
        return {}

    x = (
        df.groupby("cluster", group_keys=False)
        .apply(lambda df: df.user_id.unique().shape[0])
        .to_dict()
    )

    return x


class AdDataError(BaseException):
    pass


def estimate_price(spend: float, found: int):
    # Estimates # people/dollar as Poisson with Gamma prior

    spend = round(spend)

    # TODO: add incentive to this somehow, think through formally
    # implies Gamma(1/2, 1) -> $2/person
    prior_k = 0.5
    prior_theta = 1

    prior_beta = 1 / prior_theta
    new_lambda = (prior_k + found) / (prior_beta + spend)

    # round to pretty price
    price = round(1 / new_lambda, 2)
    return price


def add_incentive(
    spend: dict[str, float], counts: dict[str, int], incentive_per_respondent: float
):
    added = {k: v * incentive_per_respondent for k, v in counts.items()}
    return {k: v + added[k] for k, v in spend.items()}


def calc_price(
    df: pd.DataFrame,
    window: DateRange,
    spend: dict[str, float],
    incentive_per_respondent: float,
):
    # filter by time
    def pred(st):
        return st.timestamp >= window.start_date and st.timestamp <= window.until_date

    windowed = _filter_by_join_time(df, pred)
    counts = _users_per_cluster(windowed)
    counts = {**{k: 0 for k in spend.keys()}, **counts}

    spend = add_incentive(spend, counts, incentive_per_respondent)

    price = {k: estimate_price(spend.get(k, 0), v) for k, v in counts.items()}

    return price


def prep_df_for_budget(df, strata):
    # get all unique target_question and response_surveys
    # so that you can add them all???
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [d.assign(cluster=s.id) for s, d in dfs if d is not None]

    if not dfs:
        return None

    return pd.concat(dfs).reset_index(drop=True)


def budget_opt(S, goal, tot, price, budget):
    C = 1 / price
    s = S / S.sum()
    new_spend = s * budget
    projection = C * new_spend + tot + 1
    loss = np.sum(goal**2 / projection)
    return loss * tot.sum()


def recruits_opt(S, goal, tot, price, num_recruits):
    s = S / S.sum()
    recruits_per_strata = s * num_recruits
    projection = recruits_per_strata + tot + 1
    loss = np.sum(goal**2 / projection)
    return loss * 100


def proportional_opt(goal, tot, price, budget=None, max_recruits=None, tol=0.01):
    if budget is None and max_recruits is None:
        raise Exception("Need either a max budget or max_recruits to optimize")

    def opt(fn, constraint):
        P = goal.shape[0]
        x0 = np.repeat(1, P)
        x0 = x0 / x0.sum()

        m = minimize(
            fn,
            x0=x0,
            args=(goal, tot, price, constraint),
            method="L-BFGS-B",
            bounds=[(0, None)] * P,
            options={"ftol": 1e-14, "gtol": 1e-10, "eps": 1e-12},
        )

        logging.info(f"Finished optimizing with loss: {m.fun}")

        if m.fun / P > tol:
            logging.warning(f"Optimization loss very high: {m.fun}")

        return m

    if budget is not None:
        m = opt(budget_opt, budget)
        new_spend = (m.x / m.x.sum()) * budget
        new_recruits = new_spend * 1 / price
        expected_recruits = tot + new_recruits
        budget_solution = (new_spend, expected_recruits)

    if max_recruits is None:
        return budget_solution

    num_recruits = max_recruits - tot.sum()

    m = opt(recruits_opt, num_recruits)
    new_recruits = (m.x / m.x.sum()) * num_recruits
    new_spend = new_recruits * price
    expected_recruits = tot + new_recruits
    recruit_solution = (new_spend, expected_recruits)

    if budget is None:
        return recruit_solution

    if new_spend.sum() > budget:
        return budget_solution

    return recruit_solution


# provide max
def proportional_budget(goal, spend, tot, price, budget=None, max_recruits=None):
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

    df["new_spend"], df["expected"] = proportional_opt(
        df.goal.values, df.respondents.values, df.price.values, budget, max_recruits
    )

    return df.new_spend.to_dict(), df.expected.to_dict()


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
    window: DateRange,
    spend: Dict[str, float],
    incentive_per_respondent: float,
):
    optimized_ids = {s.id for s in strata}

    spend = {k: v for k, v in spend.items() if k in optimized_ids}
    spend = {**{s.id: 0 for s in strata}, **spend}

    respondents = _users_per_cluster(df)
    respondents = {**{k: 0 for k in spend.keys()}, **respondents}

    price = calc_price(df, window, spend, incentive_per_respondent)

    return spend, respondents, price


def add_incentive_to_price():
    # add to each

    pass


# TODO: add frequency -- at least to report if nothing automated
# probably more elegant just to change "spend" to "insights"

# TODO: we need a more sophisticated process to estimate_ price.
# The "DateWindow" creates a problem here, it's too miopic
# If an adset has been turned off for a few days, we forget
# all information we have about price. Similarly, for very
# high priced strata, we chronically underestimate the price.
#
# Solution: We have insights data now. Use that timeseries to
# actually create a reasonable estimate of the price of each user
# (some sort of model that handles missing data well, handles
# time explicitly? Takes into account temp data? ) Then lose
# opt window.


def get_budget_lookup(
    df: Optional[pd.DataFrame],
    strata: Sequence[Union[Stratum, StratumConf]],
    max_budget: float,
    incentive_per_respondent: float,
    max_sample_size: int,
    window: DateRange,
    spend: Dict[str, float],
    lifetime_spend: Dict[str, float],
) -> Tuple[Optional[Budget], Optional[AdOptReport]]:
    df = prep_df_for_budget(df, strata) if df is not None else None

    if df is None:
        logging.info("Failed to calculate budget due to lack of response data")
        return None, None

    # TODO: fix total_spend and insights spend here
    total_spend = sum(lifetime_spend.values())
    to_spend = max_budget - total_spend

    try:
        spend, tot, price = get_stats(
            df, strata, window, spend, incentive_per_respondent
        )
    except AdDataError as e:
        logging.info(f"Failed to calculate budget due to the follow error: {e}")
        return None, None

    share = _normalize_values(tot)

    if to_spend <= 0:
        logging.info("No money left in the budget!")
        return _off_budget(strata), None

    goal = _normalize_values({s.id: s.quota for s in strata})
    budget, expected = proportional_budget(
        goal, spend, tot, price, to_spend, max_sample_size
    )

    report = make_report(
        [
            ("current_price_per_participant", price),
            ("total_spent", spend),
            ("lifetime_spent", lifetime_spend),
            ("desired_percentage", goal),
            ("current_participants", tot),
            ("current_percentage", share),
            ("current_budget", budget),
            ("expected_participants", expected),
            ("expected_percentage", _normalize_values(expected)),
        ]
    )
    return budget, report
