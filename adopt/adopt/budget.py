import logging
import os
import time
from dataclasses import dataclass
from math import ceil
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
from datetime import datetime

import cvxpy as cp
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .clustering import _users_by_predicate, only_target_users
from .facebook.state import DateRange
from .study_conf import Budget, Stratum, StratumConf
from .recruitment_data import (
    calculate_stat_sql,
    AdPlatformRecruitmentStats,
    RecruitmentStats,
)
from .campaign_queries import DBConf, AdOptReport


@dataclass
class OptimizationResult:
    """Result of budget optimization with optional counterfactual analysis.

    Attributes:
        new_spend: Optimal spend allocation (numpy array)
        expected_recruits: Expected recruit counts from optimal spend (numpy array)
        counterfactual_spend: Cost to fill sample when budget constraint binds (numpy array, optional)
        counterfactual_recruits: Recruits with full budget when respondents bind (numpy array, optional)
    """
    new_spend: np.ndarray
    expected_recruits: np.ndarray
    counterfactual_spend: Optional[np.ndarray] = None
    counterfactual_recruits: Optional[np.ndarray] = None


def _filter_by_join_time(df: pd.DataFrame, pred: Callable[[pd.Series], bool]):
    initial_events = (
        df.groupby("user_id")
        .apply(lambda df: df.sort_values("timestamp").iloc[0])
        .reset_index(drop=True)
    )

    users = _users_by_predicate(initial_events, pred)

    return df[df.user_id.isin(users)].reset_index(drop=True)


def _users_per_cluster(df: Optional[pd.DataFrame]) -> dict[str, int]:
    if df is None or df.shape[0] == 0:
        return {}

    x = (
        df.groupby("cluster", group_keys=False)
        .apply(lambda df: df.user_id.unique().shape[0])
        .to_dict()
    )

    return x


class AdDataError(BaseException):
    pass


def estimate_price(spend: float, found: int, prior_price: float = 2.0):
    # Estimates # people/dollar as Poisson with Gamma prior
    # prior_price: Expected price per person in dollars (default: $2/person)

    spend = round(spend)

    # Convert prior_price to Gamma parameters
    # For Gamma(k, theta), mean = k*theta
    # We want mean = 1/prior_price (people per dollar)
    # We'll keep k=0.5 as it gives a reasonable shape
    prior_k = 0.5
    prior_theta = 1 / (prior_price * prior_k)

    prior_beta = 1 / prior_theta
    new_lambda = (prior_k + found) / (prior_beta + spend)

    # round to pretty price
    price = round(1 / new_lambda, 2)
    return price


def estimate_variance(n: int, s: int, prior: tuple = (0.5, 0.5)) -> float:
    """Posterior mean of Bernoulli variance π(1-π) under Beta(α, β) prior.

    Given n trials and s successes, posterior is Beta(α + s, β + n - s). The mean of
    π(1-π) under Beta(a, b) is a*b / ((a+b)(a+b+1)).

    Default prior (0.5, 0.5) is Jeffreys, recommended in
    paper/variance_extension.tex §5.1. Effective prior sample size is α + β; pass
    that as n0 to proportional_opt_closed_form to keep the optimizer and estimator
    internally consistent.

    Used by Step 5 (heterogeneous-variance allocation). Not yet wired into
    get_budget_lookup; aggregation across multiple outcomes per stratum and
    plumbing through StudyConf are deferred to a follow-on plan.

    Args:
        n: Number of trials (int)
        s: Number of successes (int)
        prior: Tuple (α, β) for Beta prior (default: (0.5, 0.5) = Jeffreys)

    Returns:
        Posterior mean of Bernoulli variance π(1-π)
    """
    α, β = prior
    a = α + s
    b = β + n - s
    return (a * b) / ((a + b) * (a + b + 1))


def add_incentive(
    spend: dict[str, float], counts: dict[str, int], incentive_per_respondent: float
):
    added = {k: v * incentive_per_respondent for k, v in counts.items()}
    return {k: v + added[k] for k, v in spend.items()}


def _get_counts(
    df: Optional[pd.DataFrame], window: DateRange, spend: dict[str, float]
) -> dict[str, int]:
    """Get counts of users per stratum, handling None df case."""
    if df is None:
        return {k: 0 for k in spend.keys()}

    def pred(st):
        return st.timestamp >= window.start_date and st.timestamp <= window.until_date

    windowed = _filter_by_join_time(df, pred)
    counts = _users_per_cluster(windowed)
    return {**{k: 0 for k in spend.keys()}, **counts}


def _calc_price(counts, spend, incentive_per_respondent):
    spend = add_incentive(spend, counts, incentive_per_respondent)
    prior = 2 + incentive_per_respondent
    return {k: estimate_price(spend.get(k, 0), v, prior) for k, v in counts.items()}


def calc_price(
    df: Optional[pd.DataFrame],
    window: DateRange,
    spend: dict[str, float],
    incentive_per_respondent: float,
):
    counts = _get_counts(df, window, spend)
    return _calc_price(counts, spend, incentive_per_respondent)


def prep_df_for_budget(df, strata):
    # get all unique target_question and response_surveys
    # so that you can add them all???
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [d.assign(cluster=s.id) for s, d in dfs if d is not None]

    if not dfs:
        return None

    return pd.concat(dfs).reset_index(drop=True)


def budget_opt(S, goal, tot, price, budget, efficiency_weight: float):
    C = 1 / price
    s = S / S.sum()
    new_spend = s * budget
    projection = C * new_spend + tot + 1

    # Weighted variance loss (current behavior - optimizes distribution)
    variance_loss = np.sum(goal**2 / projection)

    # Efficiency loss (maximize total N - cost efficient)
    efficiency_loss = 1 / np.sum(projection)

    # Blended loss
    loss = efficiency_weight * variance_loss + (1 - efficiency_weight) * efficiency_loss
    return loss * tot.sum()


def recruits_opt(S, goal, tot, price, num_recruits, efficiency_weight: float):
    s = S / S.sum()
    recruits_per_strata = s * num_recruits
    projection = recruits_per_strata + tot + 1

    # Weighted variance loss (current behavior - optimizes distribution)
    variance_loss = np.sum(goal**2 / projection)

    # Efficiency loss (maximize total N - cost efficient)
    efficiency_loss = 1 / np.sum(projection)

    # Blended loss
    loss = efficiency_weight * variance_loss + (1 - efficiency_weight) * efficiency_loss
    return loss * 100


def proportional_opt_closed_form(
    goal, tot, price, budget, max_recruits, efficiency_weight: float = 1.0, sigma: Optional[np.ndarray] = None, n0: float = 1
) -> OptimizationResult:
    """Closed-form optimizer for the pure-variance objective.

    Supports only ``efficiency_weight == 1.0`` (pure variance, Case A in
    paper/variance_extension.tex §9): analytic active-set algorithm with
    allocation rule ``m_h* ∝ goal_h · sigma_h / sqrt(p_h)`` on shifted budget
    ``B' = B + Σ p_h(tot_h + n0)``. This is what closed-form is actually good
    at — exact, microseconds, inspectable.

    For ``efficiency_weight < 1`` (blended), use ``proportional_opt_cvxpy`` or
    the legacy ``proportional_opt``. We had a nested-bisection closed-form for
    the blended case but retired it: it was numerical (not analytic), slower
    than CVXPY (~80 ms vs ~15 ms), and ~150 lines of bespoke convergence logic
    with no clear advantage over CVXPY. See
    adopt/docs/optimizer-validation.md for the decision record.

    n0: prior effective sample size (default 1, matching the Jeffreys prior
        Beta(0.5, 0.5) with α + β = 1). ``m_h = tot_h + new_recruits_h + n0`` is the
        total effective sample size (data + prior). When the caller fills `sigma`
        from `estimate_variance(n, s, prior=(α, β))`, pass ``n0 = α + β`` from the
        same prior to keep the optimizer and estimator internally consistent.

    Args:
        goal: Target allocation proportions (numpy array)
        tot: Current respondent counts per stratum (numpy array)
        price: Cost per respondent per stratum (numpy array)
        budget: Maximum budget available (float or None)
        max_recruits: Maximum total respondents wanted (int or None)
        efficiency_weight: Must be 1.0 (pure variance). Other values raise.
        sigma: Per-stratum variance (default: ones for equal variance)
        n0: Prior effective sample size (default 1 = Jeffreys prior)

    Returns:
        OptimizationResult with new_spend, expected_recruits, and counterfactuals
    """
    if budget is None and max_recruits is None:
        raise Exception("Need either a max budget or max_recruits to optimize")

    if efficiency_weight != 1.0:
        raise NotImplementedError(
            "proportional_opt_closed_form supports only efficiency_weight=1.0 "
            f"(pure variance); got {efficiency_weight}. Use proportional_opt_cvxpy "
            "or the legacy proportional_opt for blended (w < 1) objectives."
        )

    if sigma is None:
        sigma = np.ones(len(goal))

    H = len(goal)

    # Budget-binding case
    if budget is not None:
        # Compute shifted budget B' = B + sum(p_h * (tot_h + n0))
        B_prime = budget + np.sum(price * (tot + n0))

        # Pure variance: closed-form active-set allocation
        m_opt = _active_set_allocate(goal, sigma, price, tot, B_prime, n0=n0)

        # expected_recruits_h = m_h* - n0 (prior + data back to data only)
        expected_recruits = m_opt - n0
        new_recruits = np.maximum(0, expected_recruits - tot)
        new_spend = new_recruits * price
        budget_solution = (new_spend, expected_recruits)

    if max_recruits is None:
        # Only budget constraint - no counterfactuals
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    # Cap-binding case: allocate new_recruits to reach max_recruits
    num_recruits = max_recruits - tot.sum()

    # For recruits binding, if we already exceed max_recruits, don't allocate more
    if num_recruits <= 0:
        new_recruits = np.zeros_like(tot, dtype=float)
        new_spend = np.zeros_like(price, dtype=float)
        expected_recruits = tot.copy().astype(float)
        recruit_solution = (new_spend, expected_recruits)
    else:
        # Recruits-binding: m_h* ∝ goal_h * sigma_h, sum(m_h) = max_recruits + H*n0.
        # Active-set iteration pins strata where m_h* < tot_h + n0 at their lower
        # bound and redistributes the surplus across remaining active strata.
        M_prime = max_recruits + H * n0
        m_recruit_opt = _active_set_allocate_recruits(goal, sigma, tot, M_prime, n0=n0)

        expected_recruits = m_recruit_opt - n0
        new_recruits = np.maximum(0, expected_recruits - tot)
        new_spend = new_recruits * price
        recruit_solution = (new_spend, expected_recruits)

    if budget is None:
        # Only respondents constraint - no counterfactuals
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    # Both constraints present - determine which binds
    if new_spend.sum() > budget:
        # Budget constraint binds - include counterfactual cost to fill sample
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=recruit_solution[0],  # Cost without budget constraint
            counterfactual_recruits=None,
        )
    else:
        # Respondents constraint binds - include counterfactual recruits with unlimited budget
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=budget_solution[1],  # Recruits without respondent constraint
        )


def _active_set_allocate(goal: np.ndarray, sigma: np.ndarray, price: np.ndarray,
                         tot: np.ndarray, B_prime: float, n0: float = 1) -> np.ndarray:
    """Active-set algorithm for closed-form budget allocation.

    Iteratively pins strata whose unconstrained allocation m_h* < tot_h + n0 at the lower bound,
    and recomputes the allocation on the remaining free strata.

    Args:
        goal: Target allocation proportions
        sigma: Per-stratum variance
        price: Cost per recruit per stratum
        tot: Current recruit counts
        B_prime: Shifted budget B' = B + sum(p_h * (tot_h + n0))
        n0: Prior effective sample size (default 1)

    Returns:
        Optimal allocation m_h* for all strata (includes n0 component)
    """
    H = len(goal)
    active = np.arange(H)  # Initially all strata active
    lower_bound = tot + n0  # m_h >= tot_h + n0
    m = lower_bound.copy().astype(float)

    for iteration in range(H):
        # Compute the weights for the unconstrained allocation
        # m_h* ∝ goal_h * sigma_h / sqrt(p_h) (per math note Sec 9 Case A)
        active_idx = active
        if len(active_idx) == 0:
            break

        # BUG FIX: weight is goal_h, not goal_h^2. The unconstrained optimum
        # allocation for the pure-variance problem is m_h* ∝ goal_h * sigma_h / sqrt(p_h),
        # not (goal_h^2 * sigma_h / sqrt(p_h)). Using goal_h^2 caused massive over-pinning
        # of strata at their lower bounds, violating KKT stationarity.
        W = goal[active_idx]  # FIX: was goal[active_idx] ** 2
        sigma_a = sigma[active_idx]
        price_a = price[active_idx]

        # Allocation on active strata: m_h ∝ goal_h * sigma_h / sqrt(p_h)
        weights = W * sigma_a / np.sqrt(price_a)

        # Normalize so sum(price_h * m_h) = B_prime for active strata
        # sum(price_h * weights_h * scale) = B_prime
        # scale = B_prime / sum(price_h * weights_h)
        total_price_weight = np.sum(price_a * weights)
        if total_price_weight <= 0:
            # Degenerate case: use uniform allocation
            scale = B_prime / np.sum(price_a)
            m_active = np.full(len(active_idx), scale)
        else:
            scale = B_prime / total_price_weight
            m_active = weights * scale

        # Update allocation for active strata
        m[active_idx] = m_active

        # Pin any stratum that hit its lower bound
        pinned = m_active < lower_bound[active_idx]
        if not np.any(pinned):
            # No more strata to pin; converged
            break

        # Remove pinned strata from active set and adjust budget
        pinned_idx = active_idx[pinned]
        active = np.setdiff1d(active, pinned_idx)

        # Recompute B_prime by subtracting the cost of pinned strata
        B_prime = B_prime - np.sum(price[pinned_idx] * lower_bound[pinned_idx])
        m[pinned_idx] = lower_bound[pinned_idx]

    return m


def _active_set_allocate_recruits(goal: np.ndarray, sigma: np.ndarray,
                                  tot: np.ndarray, M_prime: float,
                                  n0: float = 1) -> np.ndarray:
    """Active-set algorithm for closed-form recruits-binding allocation.

    Minimizes sum(goal_h^2 * sigma_h^2 / m_h) subject to sum(m_h) = M_prime and
    m_h >= tot_h + n0, where m_h = expected_recruits_h + n0 and M_prime =
    max_recruits + H * n0.

    Mirrors _active_set_allocate's iterate-and-pin logic, but the constraint is on
    sum(m_h) (recruits-binding) rather than sum(p_h * m_h) (budget-binding), so
    price drops out of both the allocation rule and the lower-bound bookkeeping.
    Iteration is required because the lower bound m_h >= tot_h + n0 can bind on
    multiple strata in different rounds (e.g., one stratum over target, another
    pushed below its bound by reallocation of the surplus).
    """
    H = len(goal)
    active = np.arange(H)
    lower_bound = tot + n0
    m = lower_bound.copy().astype(float)

    for _ in range(H):
        if len(active) == 0:
            break
        weights = goal[active] * sigma[active]
        total_weight = weights.sum()
        if total_weight <= 0:
            scale = M_prime / len(active)
            m_active = np.full(len(active), scale)
        else:
            scale = M_prime / total_weight
            m_active = weights * scale
        m[active] = m_active

        pinned = m_active < lower_bound[active]
        if not np.any(pinned):
            break
        pinned_idx = active[pinned]
        active = np.setdiff1d(active, pinned_idx)
        M_prime = M_prime - np.sum(lower_bound[pinned_idx])
        m[pinned_idx] = lower_bound[pinned_idx]

    return m


def _solve_cvxpy_budget_binding(
    goal: np.ndarray,
    tot: np.ndarray,
    price: np.ndarray,
    budget: float,
    sigma: np.ndarray,
    n0: float = 1,
    efficiency_weight: float = 1.0,
) -> np.ndarray:
    """Solve the budget-binding subproblem via CVXPY+ECOS, with CLARABEL fallback.

    Minimizes ``w · Σ (goal_h · sigma_h)² / m_h + (1 − w) / Σ m_h`` subject to
    ``p^T m == B'`` and ``m ≥ tot + n0``, where ``w = efficiency_weight`` and
    ``B' = B + p^T (tot + n0)``. With ``w = 1`` the blend reduces to the
    pure-variance objective (Case A in paper/variance_extension.tex §9). Returns
    m (the effective sample sizes).
    """
    H = len(goal)
    lower_bound = tot + n0
    B_prime = budget + float(np.dot(price, lower_bound))

    # Rescale m so the variable is O(1): m = M * m_tilde where M = B'/sum(price)
    # is the average per-stratum allocation. Without this, ECOS/CLARABEL lose
    # precision on the prod cases where m ~ 100s and the inv_pos objective ~ 1e-4.
    # The blend preserves the rescaling: both terms inherit a 1/M factor, so the
    # weights w and (1-w) act on the same scale as before.
    M = B_prime / float(np.sum(price))
    coeffs = (goal * sigma) ** 2
    w = float(efficiency_weight)

    solver_opts = {
        cp.ECOS: {"abstol": 1e-12, "reltol": 1e-12, "feastol": 1e-12, "max_iters": 400},
        cp.CLARABEL: {
            "tol_gap_abs": 1e-12,
            "tol_gap_rel": 1e-12,
            "tol_feas": 1e-12,
            "max_iter": 5000,
        },
    }

    def _solve(solver):
        m_tilde = cp.Variable(H, nonneg=True)
        variance_term = cp.sum(cp.multiply(coeffs, cp.inv_pos(m_tilde)))
        if w >= 1.0:
            obj = variance_term
        else:
            efficiency_term = cp.inv_pos(cp.sum(m_tilde))
            obj = w * variance_term + (1.0 - w) * efficiency_term
        constraints = [price @ m_tilde == B_prime / M, m_tilde >= lower_bound / M]
        problem = cp.Problem(cp.Minimize(obj), constraints)
        try:
            problem.solve(solver=solver, **solver_opts[solver])
        except cp.error.SolverError as e:
            return problem, m_tilde, str(e)
        return problem, m_tilde, None

    # ECOS first (faster, more accurate when it converges); accept OPTIMAL only —
    # ECOS's "optimal_inaccurate" can be off by ~1e-3 on these problems.
    # Fall back to CLARABEL, which produces tight solutions (~1e-7) even when
    # it returns "optimal_inaccurate", so accept either status from it.
    problem, m_var, err = _solve(cp.ECOS)
    if err is not None or problem.status != cp.OPTIMAL:
        problem, m_var, err = _solve(cp.CLARABEL)
        if err is not None or problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            raise RuntimeError(
                f"CVXPY failed to solve budget-binding problem: "
                f"status={problem.status!r}, error={err!r}, "
                f"goal={goal.tolist()}, tot={tot.tolist()}, price={price.tolist()}, "
                f"budget={budget}, n0={n0}"
            )

    return np.asarray(m_var.value, dtype=float) * M


def proportional_opt_cvxpy(
    goal, tot, price, budget, max_recruits, efficiency_weight: float = 1.0,
    sigma: Optional[np.ndarray] = None, n0: float = 1,
) -> OptimizationResult:
    """CVXPY+ECOS optimizer for the variance / blended objective.

    Same problem and signature as proportional_opt_closed_form; uses an interior-point
    solver instead of the closed-form active-set / bisection algorithm. Provides a
    tight (≤ 1e-6) cross-check oracle and the landing pad for future objective
    extensions (regularization, correlated outcomes) that break closed form.

    Supports any ``efficiency_weight ∈ [0, 1]``: with ``w < 1`` the objective gains
    a ``(1 − w) · cp.inv_pos(cp.sum(m))`` term — convex by composition.

    The recruits-binding branch (Σ m = M_prime) is unaffected by ``w`` because the
    efficiency term ``(1 − w) / Σ m`` is constant on the feasible set, so the
    blended objective reduces to pure variance there. It uses a direct
    proportional split — no convex program is needed.
    """
    if budget is None and max_recruits is None:
        raise Exception("Need either a max budget or max_recruits to optimize")

    if not (0.0 <= efficiency_weight <= 1.0):
        raise ValueError(
            f"efficiency_weight must be in [0, 1]; got {efficiency_weight}"
        )

    if sigma is None:
        sigma = np.ones(len(goal))

    tot = np.asarray(tot, dtype=float)
    price = np.asarray(price, dtype=float)
    goal = np.asarray(goal, dtype=float)

    # Budget-binding case via CVXPY
    if budget is not None:
        m_opt = _solve_cvxpy_budget_binding(
            goal, tot, price, budget, sigma, n0=n0,
            efficiency_weight=efficiency_weight,
        )
        expected_recruits = m_opt - n0
        new_recruits = np.maximum(0, expected_recruits - tot)
        new_spend = new_recruits * price
        budget_solution = (new_spend, expected_recruits)

    if max_recruits is None:
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    # Recruits-binding branch — direct proportional split, no convex program needed.
    num_recruits = max_recruits - tot.sum()
    if num_recruits <= 0:
        new_recruits = np.zeros_like(tot, dtype=float)
        new_spend = np.zeros_like(price, dtype=float)
        expected_recruits = tot.copy().astype(float)
        recruit_solution = (new_spend, expected_recruits)
    else:
        total_m = (goal * sigma).sum()
        m_recruit_opt = (goal * sigma / total_m) * max_recruits
        new_recruits = np.maximum(0, m_recruit_opt - tot)
        new_spend = new_recruits * price
        expected_recruits = m_recruit_opt
        recruit_solution = (new_spend, expected_recruits)

    if budget is None:
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    # Both constraints — same dispatch logic as proportional_opt_closed_form
    if new_spend.sum() > budget:
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=recruit_solution[0],
            counterfactual_recruits=None,
        )
    else:
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=budget_solution[1],
        )


def proportional_opt(
    goal, tot, price, budget, max_recruits, efficiency_weight: float, tol=0.01
) -> OptimizationResult:
    """Optimize budget allocation with counterfactual analysis.

    When both budget and respondent constraints are provided, determines which constraint
    binds and includes the counterfactual solution (what would happen without the binding constraint).

    Args:
        goal: Target allocation proportions (numpy array)
        tot: Current respondent counts per stratum (numpy array)
        price: Cost per respondent per stratum (numpy array)
        budget: Maximum budget available (float or None)
        max_recruits: Maximum total respondents wanted (int or None)
        efficiency_weight: Weight for variance optimization (1.0=variance, 0.0=cost efficiency)
        tol: Tolerance for optimization loss warnings

    Returns:
        OptimizationResult with:
        - new_spend: Optimal spend allocation
        - expected_recruits: Expected total recruits from optimal spend
        - counterfactual_spend: If budget binds, the cost to fill sample without budget constraint
        - counterfactual_recruits: If respondents bind, recruits possible with unlimited budget
    """
    if budget is None and max_recruits is None:
        raise Exception("Need either a max budget or max_recruits to optimize")

    def opt(fn, constraint):
        P = goal.shape[0]
        x0 = np.repeat(1, P)
        x0 = x0 / x0.sum()

        m = minimize(
            fn,
            x0=x0,
            args=(goal, tot, price, constraint, efficiency_weight),
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
        # Only budget constraint - no counterfactuals
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    num_recruits = max_recruits - tot.sum()

    m = opt(recruits_opt, num_recruits)
    new_recruits = (m.x / m.x.sum()) * num_recruits
    new_spend = new_recruits * price
    expected_recruits = tot + new_recruits
    recruit_solution = (new_spend, expected_recruits)

    if budget is None:
        # Only respondents constraint - no counterfactuals
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=None,
        )

    # Both constraints present - determine which binds
    if new_spend.sum() > budget:
        # Budget constraint binds - include counterfactual cost to fill sample
        return OptimizationResult(
            new_spend=budget_solution[0],
            expected_recruits=budget_solution[1],
            counterfactual_spend=recruit_solution[0],  # Cost without budget constraint
            counterfactual_recruits=None,
        )
    else:
        # Respondents constraint binds - include counterfactual recruits with unlimited budget
        return OptimizationResult(
            new_spend=recruit_solution[0],
            expected_recruits=recruit_solution[1],
            counterfactual_spend=None,
            counterfactual_recruits=budget_solution[1],  # Recruits without respondent constraint
        )


def _pick_optimizer(efficiency_weight: float) -> Tuple[Callable, str]:
    """Return (optimizer_callable, version_label).

    Soak-deployment dispatch (planning/soak-deployment.md):
      - env ADOPT_OPTIMIZER_DEFAULT=lbfgs forces the legacy L-BFGS-B path for
        global rollback without redeploying app code.
      - Otherwise: closed_form for w==1 (microsecond analytic active-set),
        cvxpy for w<1 (handles the blended objective).
    """
    if os.environ.get("ADOPT_OPTIMIZER_DEFAULT", "").lower() == "lbfgs":
        return proportional_opt, "lbfgs"
    if efficiency_weight >= 1.0:
        return proportional_opt_closed_form, "closed_form"
    return proportional_opt_cvxpy, "cvxpy"


# provide max
def proportional_budget(
    goal, spend, tot, price, budget, max_recruits, efficiency_weight: float,
    optimizer=None,
) -> Tuple[Dict, Dict, Optional[Dict], Optional[Dict]]:
    """Optimize budget allocation and return results with optional counterfactuals.

    Args:
        goal: Target allocation proportions per stratum (dict)
        spend: Current spend per stratum (dict)
        tot: Current respondent counts per stratum (dict)
        price: Cost per respondent per stratum (dict)
        budget: Maximum budget available (float or None)
        max_recruits: Maximum total respondents wanted (int or None)
        efficiency_weight: Weight for variance optimization (1.0=variance, 0.0=cost efficiency)
        optimizer: Solver callable matching proportional_opt's signature. Defaults to
            proportional_opt (L-BFGS-B). Pass proportional_opt_closed_form to exercise
            the closed-form path through the same system-level entry point.

    Returns:
        Tuple of (new_spend_dict, expected_dict, counterfactual_spend_dict_or_None, counterfactual_recruits_dict_or_None)
    """
    if not np.isclose(sum(goal.values()), 1.0, 0.01):
        raise Exception(
            f"proportional_budget needs a goal that sums to one. was given: {goal}"
        )

    if optimizer is None:
        optimizer = proportional_opt

    df = pd.DataFrame(
        {
            "goal": goal,
            "spend": spend,
            "respondents": tot,
            "price": price,
        }
    )

    result = optimizer(
        df.goal.values,
        df.respondents.values,
        df.price.values,
        budget,
        max_recruits,
        efficiency_weight=efficiency_weight,
    )

    # Convert arrays to dicts using the original index
    df["new_spend"] = result.new_spend
    df["expected"] = result.expected_recruits

    new_spend_dict = df.new_spend.to_dict()
    expected_dict = df.expected.to_dict()

    # Convert counterfactuals to dicts if present
    counterfactual_spend_dict = None
    if result.counterfactual_spend is not None:
        df["counterfactual_spend"] = result.counterfactual_spend
        counterfactual_spend_dict = df.counterfactual_spend.to_dict()

    counterfactual_recruits_dict = None
    if result.counterfactual_recruits is not None:
        df["counterfactual_recruits"] = result.counterfactual_recruits
        counterfactual_recruits_dict = df.counterfactual_recruits.to_dict()

    return new_spend_dict, expected_dict, counterfactual_spend_dict, counterfactual_recruits_dict


def _off_budget(strata):
    return {s.id: 0 for s in strata}


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


def get_budget_lookup(
    df: Optional[pd.DataFrame],
    strata: Sequence[Union[Stratum, StratumConf]],
    max_budget: float,
    incentive_per_respondent: float,
    max_sample_size: int,
    window: DateRange,
    spend: Dict[str, float],
    lifetime_spend: Dict[str, float],
    efficiency_weight: float,
    study_id: Optional[str] = None,
) -> Tuple[Optional[Budget], Optional[AdOptReport]]:
    df = prep_df_for_budget(df, strata) if df is not None else None

    if df is None:
        logging.info("Failed to calculate budget due to lack of response data")
        return None, None

    try:
        spend, tot, price = get_stats(
            df, strata, window, spend, incentive_per_respondent
        )
    except AdDataError as e:
        logging.info(f"Failed to calculate budget due to the follow error: {e}")
        return None, None

    # Add total incentive costs to total spend
    total_spend = sum(lifetime_spend.values()) + (
        sum(tot.values()) * incentive_per_respondent
    )
    to_spend = max_budget - total_spend

    share = _normalize_values(tot)

    if to_spend <= 0:
        logging.info("No money left in the budget!")
        return _off_budget(strata), None

    goal = _normalize_values({s.id: s.quota for s in strata})

    # Phase 1 (shadow): real allocation served by legacy L-BFGS-B, new optimizer
    # runs in parallel for comparison. See planning/soak-deployment.md.
    # Fail-loud: no try/except around shadow run — if it throws we want to see
    # it in error logs, not swallow it.
    t0 = time.perf_counter()
    budget, expected, counterfactual_spend, counterfactual_recruits = proportional_budget(
        goal, spend, tot, price, to_spend, max_sample_size, efficiency_weight,
        optimizer=proportional_opt,
    )
    lbfgs_time_ms = (time.perf_counter() - t0) * 1000.0

    shadow_optimizer, shadow_version = _pick_optimizer(efficiency_weight)
    t0 = time.perf_counter()
    shadow_budget, shadow_expected, _, _ = proportional_budget(
        goal, spend, tot, price, to_spend, max_sample_size, efficiency_weight,
        optimizer=shadow_optimizer,
    )
    shadow_time_ms = (time.perf_counter() - t0) * 1000.0

    # max relative diff between served (lbfgs) and shadow allocations
    served_arr = np.array([budget[k] for k in budget.keys()], dtype=float)
    shadow_arr = np.array([shadow_budget[k] for k in budget.keys()], dtype=float)
    denom = np.maximum(np.abs(served_arr), 1e-9)
    max_rel_diff = float(np.max(np.abs(served_arr - shadow_arr) / denom))
    budget_residual = abs(sum(shadow_budget.values()) - to_spend) / max(to_spend, 1.0)
    any_negative = bool(np.any(shadow_arr < 0))

    logging.info(
        "optimizer_shadow",
        extra={
            "study_id": study_id,
            "H": len(strata),
            "efficiency_weight": efficiency_weight,
            "optimizer_version": shadow_version,
            "lbfgs_time_ms": lbfgs_time_ms,
            "shadow_time_ms": shadow_time_ms,
            "max_abs_relative_diff_vs_lbfgs": max_rel_diff,
            "budget_residual": budget_residual,
            "any_negative_spend": any_negative,
        },
    )

    # Include efficiency_weight in report (same value for all strata)
    efficiency_weight_dict = {s.id: efficiency_weight for s in strata}

    # Build report facts list, adding counterfactuals only if they exist
    report_facts = [
        ("current_price_per_participant", price),
        ("total_spent", spend),
        ("lifetime_spent", lifetime_spend),
        ("desired_percentage", goal),
        ("current_participants", tot),
        ("current_percentage", share),
        ("current_budget", budget),
        ("expected_participants", expected),
        ("expected_percentage", _normalize_values(expected)),
        ("efficiency_weight", efficiency_weight_dict),
    ]

    # Add counterfactuals if present (budget binds case)
    if counterfactual_spend is not None:
        report_facts.append(("counterfactual_spend_to_fill_sample", counterfactual_spend))

    # Add counterfactuals if present (respondents bind case)
    if counterfactual_recruits is not None:
        report_facts.append(("counterfactual_participants_with_unlimited_budget", counterfactual_recruits))

    report = make_report(report_facts)
    return budget, report


def calculate_strata_stats(
    respondents_dict: Optional[Dict[str, int]],
    strata: Sequence[Union[Stratum, StratumConf]],
    recruitment_stats: Dict[str, AdPlatformRecruitmentStats],
    incentive_per_respondent: float,
) -> Dict[str, RecruitmentStats]:
    """
    Calculate all statistics for each stratum in one place, with proper cleanup and initialization.
    Args:
        respondents_dict: Dictionary mapping stratum IDs to number of respondents, or None
        strata: List of strata being recruited for
        recruitment_stats: Dictionary of recruitment statistics from calculate_stat_sql
        incentive_per_respondent: Incentive amount per respondent
    Returns:
        Dictionary mapping stratum IDs to their complete RecruitmentStats
    """
    # Initialize with zeros for all strata
    stats = {
        s.id: {
            "spend": 0.0,
            "frequency": 0.0,
            "reach": 0,
            "cpm": 0.0,
            "unique_clicks": 0,
            "unique_ctr": 0.0,
            "impressions": 0,
            "respondents": 0,
            "price_per_respondent": 0.0,
            "incentive_cost": 0.0,
            "total_cost": 0.0,
            "conversion_rate": 0.0,
            **recruitment_stats.get(s.id, AdPlatformRecruitmentStats()).model_dump(),
        }
        for s in strata
    }

    # Set respondent counts from the provided dictionary if available
    if respondents_dict is not None:
        for stratum_id, count in respondents_dict.items():
            if stratum_id not in stats:
                logging.warning(f"Stratum {stratum_id} not found in stats, skipping")
                continue
            stats[stratum_id]["respondents"] = count

    # Calculate prices using calc_price
    spend = {k: v["spend"] for k, v in stats.items()}
    respondents = {k: v["respondents"] for k, v in stats.items()}

    prices = _calc_price(
        respondents,
        spend,
        incentive_per_respondent,
    )

    # Calculate derived stats for each stratum
    for stratum_id, stratum_stats in stats.items():
        spend = stratum_stats["spend"]
        respondents = stratum_stats["respondents"]
        unique_clicks = stratum_stats["unique_clicks"]
        price_per_respondent = prices.get(stratum_id, 0)
        incentive_cost = respondents * incentive_per_respondent
        total_cost = spend + incentive_cost
        conversion_rate = respondents / unique_clicks if unique_clicks > 0 else 0
        stratum_stats.update(
            {
                "price_per_respondent": price_per_respondent,
                "incentive_cost": incentive_cost,
                "total_cost": total_cost,
                "conversion_rate": conversion_rate,
            }
        )

    # Convert the stats dictionary to use RecruitmentStats objects
    return {
        stratum_id: RecruitmentStats(**stratum_stats)
        for stratum_id, stratum_stats in stats.items()
    }


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


def get_budget_lookup_with_db(
    df: Optional[pd.DataFrame],
    strata: Sequence[Union[Stratum, StratumConf]],
    max_budget: float,
    incentive_per_respondent: float,
    max_sample_size: int,
    window: DateRange,
    db_conf: DBConf,
    study_id: str,
    efficiency_weight: float,
) -> Tuple[Optional[Budget], Optional[AdOptReport]]:
    """
    Wrapper around get_budget_lookup that calculates spend statistics from recruitment data.

    Args:
        df: DataFrame containing user response data
        strata: List of strata being recruited for
        max_budget: Maximum budget for the study
        incentive_per_respondent: Incentive amount per respondent
        max_sample_size: Maximum sample size for the study
        window: DateRange to analyze statistics within
        db_conf: Database configuration
        study_id: ID of the study
        efficiency_weight: Weight for variance optimization (1.0=variance, 0.0=cost efficiency)

    Returns:
        Tuple of (budget_lookup, report) as returned by get_budget_lookup
    """

    # Process DataFrame to get respondents per stratum if available
    df = prep_df_for_budget(df, strata) if df is not None else None
    if df is None:
        logging.info("Failed to calculate budget due to lack of response data")
        return None, None

    windowed_stats = calculate_stat_sql(db_conf, window, study_id)
    windowed_spend = {k: v.spend for k, v in windowed_stats.items()}

    # Calculate lifetime spend (no window parameter means all time)
    lifetime_stats = calculate_stat_sql(db_conf, None, study_id)
    lifetime_spend = {k: v.spend for k, v in lifetime_stats.items()}

    return get_budget_lookup(
        df,
        strata,
        max_budget,
        incentive_per_respondent,
        max_sample_size,
        window,
        windowed_spend,
        lifetime_spend,
        efficiency_weight,
        study_id=study_id,
    )
