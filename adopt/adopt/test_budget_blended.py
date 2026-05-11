"""Blended objective (efficiency_weight < 1) tests for CVXPY and L-BFGS-B.

Closed-form (`proportional_opt_closed_form`) is the pure-variance path only —
it raises `NotImplementedError` for `w < 1`. The blended objective

    L(m) = w · Σ_h (goal_h · sigma_h)² / m_h  +  (1 − w) / Σ_h m_h

is supported by `proportional_opt_cvxpy` (interior point) and the legacy
`proportional_opt` (L-BFGS-B). These tests pin CVXPY to the blended-KKT math
note (Eq. eq:blended-mh):

    w · (goal_h · sigma_h)² / m_h²  +  (1 − w) / S²  =  λ · p_h

on unpinned strata, and cross-check CVXPY against L-BFGS-B on every prod
budget-binding case.
"""

import numpy as np
import pytest

from adopt.budget import (
    OptimizationResult,
    proportional_opt,
    proportional_opt_closed_form,
    proportional_opt_cvxpy,
)

from .test_budget_prod_regimes import KKT_CASES, PROD_CASES, ProdCase


BUDGET_BINDING_CASES = [c for c in PROD_CASES if c.budget is not None]
# KKT stationarity across unpinned strata needs ≥2 unpinned. Active-set
# membership is invariant in w on these prod cases (pinning is driven by tot
# vs. goal), so KKT_CASES from the prod-regimes module applies here too.
KKT_BUDGET_CASES = [c for c in KKT_CASES if c.budget is not None]
BLENDED_WEIGHTS = [0.25, 0.5, 0.75, 0.9, 0.99]


def _run(fn, case: ProdCase, w: float, **extra) -> OptimizationResult:
    return fn(
        goal=np.array(case.goal),
        tot=np.array(case.tot, dtype=float),
        price=np.array(case.price),
        budget=case.budget,
        max_recruits=case.max_recruits,
        efficiency_weight=w,
        **extra,
    )


def test_closed_form_rejects_blended():
    """Closed-form raises NotImplementedError for w < 1."""
    goal = np.array([0.5, 0.5])
    tot = np.array([0.0, 0.0])
    price = np.array([1.0, 1.0])
    with pytest.raises(NotImplementedError, match="efficiency_weight=1.0"):
        proportional_opt_closed_form(
            goal, tot, price, 100.0, None, efficiency_weight=0.5
        )


@pytest.mark.parametrize("w", BLENDED_WEIGHTS)
@pytest.mark.parametrize(
    "case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES]
)
def test_cvxpy_matches_lbfgs_blended(case: ProdCase, w: float):
    """CVXPY and L-BFGS-B reach the same blended optimum.

    L-BFGS-B has a ~1e-4 noise floor on the allocation (set by its
    `ftol=1e-14, gtol=1e-10, eps=1e-12` and the degenerate `s = S / S.sum()`
    parameterization). Use rtol=1e-3 to leave headroom on both ends.
    """
    cvx = _run(proportional_opt_cvxpy, case, w)
    lb = _run(proportional_opt, case, w, tol=0.01)
    np.testing.assert_allclose(
        cvx.expected_recruits,
        lb.expected_recruits,
        rtol=1e-3,
        atol=1e-3,
        err_msg=(
            f"{case.name} w={w}: CVXPY and L-BFGS-B disagree.\n"
            f"  cvxpy:   {cvx.expected_recruits}\n"
            f"  lbfgs:   {lb.expected_recruits}"
        ),
    )


@pytest.mark.parametrize("w", [0.25, 0.5, 0.75])
@pytest.mark.parametrize(
    "case", KKT_BUDGET_CASES, ids=[c.name for c in KKT_BUDGET_CASES]
)
def test_cvxpy_blended_kkt_stationarity(case: ProdCase, w: float):
    """CVXPY blended solution satisfies the blended KKT equation.

    On unpinned strata:
        w · (goal · sigma)² / m_h²  +  (1 − w) / S²  =  λ · p_h

    so the per-h quantity (LHS / p_h) is constant. Filtered to cases with ≥2
    unpinned strata.
    """
    cvx = _run(proportional_opt_cvxpy, case, w)
    n0 = 1
    tot = np.array(case.tot, dtype=float)
    goal = np.array(case.goal)
    price = np.array(case.price)
    sigma = np.ones(len(goal))

    m = cvx.expected_recruits + n0
    S = m.sum()
    unpinned = ~(cvx.expected_recruits <= tot + 1e-6)

    lhs = w * (goal * sigma) ** 2 / m**2 + (1.0 - w) / S**2
    per_p = lhs[unpinned] / price[unpinned]
    rel_spread = (per_p.max() - per_p.min()) / max(per_p.mean(), 1e-300)
    # CVXPY interior-point tolerance is looser than analytic active-set.
    assert rel_spread < 1e-3, (
        f"{case.name} w={w}: KKT stationarity violated.\n"
        f"  per_p (unpinned): {per_p}\n"
        f"  rel_spread: {rel_spread:.3e}"
    )


@pytest.mark.parametrize("w", BLENDED_WEIGHTS)
@pytest.mark.parametrize(
    "case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES]
)
def test_cvxpy_blended_budget_feasibility(case: ProdCase, w: float):
    """CVXPY blended allocation respects the budget constraint."""
    cvx = _run(proportional_opt_cvxpy, case, w)
    rel_overshoot = (cvx.new_spend.sum() - case.budget) / max(case.budget, 1.0)
    assert rel_overshoot <= 1e-4, (
        f"{case.name} w={w}: spent {cvx.new_spend.sum()} > budget {case.budget} "
        f"(rel overshoot {rel_overshoot:.2e})"
    )
    tot = np.array(case.tot, dtype=float)
    if np.any(cvx.expected_recruits > tot + 1):
        assert cvx.new_spend.sum() >= case.budget * 0.999, (
            f"{case.name} w={w}: spent only {cvx.new_spend.sum()} of budget {case.budget}"
        )


def test_cvxpy_blended_w_to_one_limit():
    """As w → 1, CVXPY blended approaches CVXPY pure variance."""
    case = next(c for c in BUDGET_BINDING_CASES if "case_3" in c.name)
    pure = _run(proportional_opt_cvxpy, case, 1.0)
    blend = _run(proportional_opt_cvxpy, case, 0.9999)
    np.testing.assert_allclose(
        blend.expected_recruits, pure.expected_recruits, rtol=1e-3, atol=1e-3,
    )


def test_cvxpy_blended_smoke_simple_h2():
    """H=2 symmetric case: m_1 == m_2, easily hand-checked.

    Equal goal, equal price, w=0.5 ⇒ symmetry ⇒ m_1 = m_2 = B'/(2p). With
    budget=100, p=1, n0=1: B' = 100 + 2·1 = 102, m = 51, expected_recruits = 50.
    """
    goal = np.array([0.5, 0.5])
    tot = np.array([0.0, 0.0])
    price = np.array([1.0, 1.0])
    cvx = proportional_opt_cvxpy(
        goal, tot, price, 100.0, None, efficiency_weight=0.5
    )
    np.testing.assert_allclose(cvx.expected_recruits, [50.0, 50.0], rtol=1e-4)
