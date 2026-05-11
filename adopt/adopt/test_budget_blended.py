"""Step 3 tests: blended objective (efficiency_weight < 1).

Verifies that the closed-form nested-bisection path
(`_blended_bisection_budget` inside `proportional_opt_closed_form`) and the
CVXPY path (`proportional_opt_cvxpy`) agree on the blended objective

    L(m) = w · Σ_h (goal_h · sigma_h)² / m_h  +  (1 − w) / Σ_h m_h

under the budget constraint, and that both reduce to the pure-variance solution
as ``w → 1``. KKT-stationarity checks pin the bisection to the math note's
Eq. (eq:blended-mh): on unpinned strata,

    w · (goal_h · sigma_h)² / m_h²  +  (1 − w) / S²  =  λ · p_h

with a single λ (modulo numerical bisection tolerance).
"""

import numpy as np
import pytest

from adopt.budget import (
    OptimizationResult,
    proportional_opt_closed_form,
    proportional_opt_cvxpy,
)

from .test_budget_prod_regimes import KKT_CASES, PROD_CASES, ProdCase


BUDGET_BINDING_CASES = [c for c in PROD_CASES if c.budget is not None]
# KKT stationarity across unpinned strata needs ≥2 unpinned. Active-set
# membership is invariant in w on these prod cases (pinning is driven by
# tot vs. goal), so KKT_CASES from the prod-regimes module applies here too.
KKT_BUDGET_CASES = [c for c in KKT_CASES if c.budget is not None]
BLENDED_WEIGHTS = [0.25, 0.5, 0.75, 0.9, 0.99]


def _run(fn, case: ProdCase, w: float) -> OptimizationResult:
    return fn(
        goal=np.array(case.goal),
        tot=np.array(case.tot, dtype=float),
        price=np.array(case.price),
        budget=case.budget,
        max_recruits=case.max_recruits,
        efficiency_weight=w,
    )


@pytest.mark.parametrize("w", BLENDED_WEIGHTS)
@pytest.mark.parametrize(
    "case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES]
)
def test_cvxpy_matches_closed_form_blended(case: ProdCase, w: float):
    """Closed-form bisection ≡ CVXPY+ECOS on expected_recruits, elementwise."""
    cf = _run(proportional_opt_closed_form, case, w)
    cvx = _run(proportional_opt_cvxpy, case, w)

    # CVXPY at w<1 with rescaling is slightly less precise than the active-set
    # path at w=1; rtol=1e-4 is the empirical bound.
    np.testing.assert_allclose(
        cvx.expected_recruits,
        cf.expected_recruits,
        rtol=1e-4,
        atol=1e-6,
        err_msg=(
            f"{case.name} w={w}: CVXPY and closed-form disagree.\n"
            f"  closed_form: {cf.expected_recruits}\n"
            f"  cvxpy:       {cvx.expected_recruits}"
        ),
    )


@pytest.mark.parametrize(
    "case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES]
)
def test_blended_limit_w_to_one(case: ProdCase):
    """As w → 1, the blended solution approaches the pure-variance solution.

    The (1-w)/S² term in the KKT denominator vanishes, recovering Case A.
    """
    cf_pure = _run(proportional_opt_closed_form, case, 1.0)
    cf_blend = _run(proportional_opt_closed_form, case, 0.999999)

    np.testing.assert_allclose(
        cf_blend.expected_recruits,
        cf_pure.expected_recruits,
        rtol=1e-3,
        atol=1e-3,
        err_msg=(
            f"{case.name}: blended at w=0.999999 should approximate pure variance.\n"
            f"  pure:    {cf_pure.expected_recruits}\n"
            f"  blended: {cf_blend.expected_recruits}"
        ),
    )


@pytest.mark.parametrize("w", [0.25, 0.5, 0.75])
@pytest.mark.parametrize(
    "case", KKT_BUDGET_CASES, ids=[c.name for c in KKT_BUDGET_CASES]
)
def test_blended_kkt_stationarity(case: ProdCase, w: float):
    """Unpinned strata satisfy the blended KKT equation with a single λ.

    KKT (variance_extension.tex Eq. (eq:blended-mh)):
        w · (goal · sigma)² / m_h²  +  (1 − w) / S²  =  λ · p_h

    so the per-h quantity (LHS / p_h) should be constant across unpinned strata.
    Pinned strata (m_h == tot_h + n0) need not satisfy stationarity. Filtered to
    cases with ≥2 unpinned strata.
    """
    cf = _run(proportional_opt_closed_form, case, w)
    n0 = 1
    tot = np.array(case.tot, dtype=float)
    goal = np.array(case.goal)
    price = np.array(case.price)
    sigma = np.ones(len(goal))

    m = cf.expected_recruits + n0
    S = m.sum()
    unpinned = ~(cf.expected_recruits <= tot + 1e-9)

    lhs = w * (goal * sigma) ** 2 / m**2 + (1.0 - w) / S**2
    per_p = lhs[unpinned] / price[unpinned]
    rel_spread = (per_p.max() - per_p.min()) / max(per_p.mean(), 1e-300)
    assert rel_spread < 1e-4, (
        f"{case.name} w={w}: KKT stationarity violated.\n"
        f"  per_p (unpinned): {per_p}\n"
        f"  rel_spread: {rel_spread:.3e}"
    )


@pytest.mark.parametrize("w", BLENDED_WEIGHTS)
@pytest.mark.parametrize(
    "case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES]
)
def test_blended_budget_feasibility(case: ProdCase, w: float):
    """The closed-form blended allocation respects the budget constraint."""
    cf = _run(proportional_opt_closed_form, case, w)
    rel_overshoot = (cf.new_spend.sum() - case.budget) / max(case.budget, 1.0)
    assert rel_overshoot <= 1e-4, (
        f"{case.name} w={w}: spent {cf.new_spend.sum()} > budget {case.budget} "
        f"(rel overshoot {rel_overshoot:.2e})"
    )
    # Budget is binding: should be close to budget when there is any unpinned mass.
    tot = np.array(case.tot, dtype=float)
    if np.any(cf.expected_recruits > tot + 1):
        assert cf.new_spend.sum() >= case.budget * 0.999, (
            f"{case.name} w={w}: spent only {cf.new_spend.sum()} of budget {case.budget}"
        )


def test_blended_smoke_simple_h2():
    """Small hand-checkable case: H=2, equal goal/price, w=0.5.

    By symmetry, m_1 == m_2 at optimum. Then budget gives p · 2m = B' ⇒
    m = B' / (2p). Verify both solvers.
    """
    goal = np.array([0.5, 0.5])
    sigma = np.ones(2)
    tot = np.array([0.0, 0.0])
    price = np.array([1.0, 1.0])
    budget = 100.0
    n0 = 1
    B_prime = budget + price @ (tot + n0)  # = 102
    expected_m = B_prime / 2.0  # = 51 each
    expected_recruits = expected_m - n0  # = 50 each

    cf = proportional_opt_closed_form(
        goal, tot, price, budget, None, efficiency_weight=0.5
    )
    cvx = proportional_opt_cvxpy(
        goal, tot, price, budget, None, efficiency_weight=0.5
    )
    np.testing.assert_allclose(cf.expected_recruits, [expected_recruits, expected_recruits], rtol=1e-6)
    np.testing.assert_allclose(cvx.expected_recruits, [expected_recruits, expected_recruits], rtol=1e-4)
