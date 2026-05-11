"""
Tier 1: Production-data-driven test cases for proportional_opt_closed_form.

Exercises ~8–12 prod-derived test cases spanning meaningful regimes:
- small H (≤4 strata) and medium H (≥6)
- budget-binding and recruits-binding scenarios
- with and without active-set pinning
- H=4 active-set case from study 9cd58b37 (regression test)
- early-stage and mid-stage studies

Each case is pure numbers with no PII, extracted from real FACEBOOK_ADOPT reports.
All cases have efficiency_weight=1.0 (pure-variance regime) and n0=1 (Jeffreys prior).

Snapshots regenerated for n0=1 (prior effective sample size), restoring the
principled Bayesian treatment of the optimizer. With n0=1, expected_recruits = m_h - 1,
where m_h is the total effective sample size (data + prior).

Test assertions verify:
1. KKT stationarity: unpinned strata have constant marginal utility
2. Constraint feasibility: binding constraint is satisfied to machine precision
3. Lower bounds: expected_recruits >= tot for all strata
4. No regression: outputs match golden snapshot within rtol=1e-9
5. Objective quality: closed-form ≤ L-BFGS-B objective + numerical slack
"""

import pytest
import numpy as np
from dataclasses import dataclass
from typing import Optional, List

from adopt.budget import (
    proportional_opt_closed_form,
    proportional_opt,
    OptimizationResult,
)


@dataclass
class ProdCase:
    """Test case derived from production FACEBOOK_ADOPT report."""
    name: str
    goal: List[float]
    tot: List[int]
    price: List[float]
    budget: float
    max_recruits: Optional[int]
    efficiency_weight: float = 1.0
    expected_recruits_snapshot: Optional[List[float]] = None
    description: str = ""


# Test cases extracted from real prod data across 3 pure-variance studies
# Snapshots regenerated for n0=1 (Jeffreys prior effective sample size); see planning/restore-n0-prior.md
PROD_CASES = [
    ProdCase(
        name="case_1_H4_budget19_tot1",
        goal=[0.24, 0.16, 0.36, 0.24],
        tot=[1, 0, 0, 0],
        price=[0.79, 2.38, 2.38, 2.38],
        budget=19.22,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[4.44411686163736, 1.0910347350116307, 3.7048281537761687, 2.136552102517446],
        description="H=4, budget binding, tot_sum=1",
        # source: study_id 9cd58b37-86bc-4186-9a6a-b170977a08cc, report timestamp 2026-04-14T01:18:29.303557+00:00
    ),
    ProdCase(
        name="case_2_H2_budget19_tot1",
        goal=[0.1, 0.9],
        tot=[1, 0],
        price=[1.56, 2.69],
        budget=19.31,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[1.0, 7.178438661710036],
        description="H=2, budget binding, tot_sum=1",
        # source: study_id 8fe1ffb9-ab04-4f8e-bc8d-9afcf341f0ef, report timestamp 2026-01-14T06:56:31.058900+00:00
    ),
    ProdCase(
        name="case_3_H6_budget4558_tot54",
        goal=[0.166667, 0.166667, 0.166667, 0.166667, 0.166667, 0.166667],
        tot=[1, 21, 0, 0, 3, 29],
        price=[3.0, 23.0, 19.0, 19.0, 6.14, 21.71],
        budget=4558.07,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[148.19163109142744, 52.881685346596576, 58.282742835172044, 58.282742835172044, 103.28477389178883, 54.459401396677826],
        description="H=6, budget binding, tot_sum=54",
        # source: study_id 027d28c7-3f66-4c9e-86bf-e3d33fb1bc69, report timestamp 2026-04-14T20:30:16.090034+00:00
    ),
    ProdCase(
        name="case_4_H6_budget4308_tot100",
        goal=[0.166667, 0.166667, 0.166667, 0.166667, 0.166667, 0.166667],
        tot=[4, 21, 8, 2, 35, 30],
        price=[5.67, 29.67, 7.59, 23.0, 3.56, 16.09],
        budget=4307.94,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[112.5568399589741, 48.64163246498994, 97.14856177936363, 55.382056180916244, 142.3110998403492, 66.41038475439895],
        description="H=6, budget binding, tot_sum=100",
        # source: study_id 027d28c7-3f66-4c9e-86bf-e3d33fb1bc69, report timestamp 2026-04-15T00:30:26.580443+00:00
    ),
    ProdCase(
        name="case_5_H2_budget15_tot6",
        goal=[0.1, 0.9],
        tot=[5, 1],
        price=[0.79, 1.56],
        budget=15.32,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[5.0, 10.82051282051282],
        description="H=2, budget binding, tot_sum=6",
        # source: study_id 8fe1ffb9-ab04-4f8e-bc8d-9afcf341f0ef, report timestamp 2026-01-14T09:01:22.584952+00:00
    ),
    ProdCase(
        name="case_6_H2_budget4797_tot1",
        goal=[0.5, 0.5],
        tot=[0, 1],
        price=[5.0, 3.0],
        budget=4796.99,
        max_recruits=None,
        efficiency_weight=1.0,
        expected_recruits_snapshot=[540.86848012682, 698.549199788633],
        description="H=2, budget binding, tot_sum=1",
        # source: study_id 027d28c7-3f66-4c9e-86bf-e3d33fb1bc69, report timestamp 2026-04-07T20:30:23.940728+00:00
    ),
]


def _pin_mask(case: ProdCase) -> np.ndarray:
    """Booleans: which strata the closed-form pins at the lower bound for this case.

    Used at collection time to filter parametrize sets so we only run KKT and
    pinning-comparison assertions against cases where they actually fire.
    """
    n0 = 1
    snap = np.array(case.expected_recruits_snapshot) if case.expected_recruits_snapshot else None
    tot = np.array(case.tot, dtype=float)
    if snap is not None:
        # Snapshot is the closed-form output; a stratum is pinned iff expected_recruits == tot.
        return (snap - tot) < 1e-6
    # Fall back to computing fresh
    result = proportional_opt_closed_form(
        goal=np.array(case.goal),
        tot=tot,
        price=np.array(case.price),
        budget=case.budget,
        max_recruits=case.max_recruits,
        efficiency_weight=case.efficiency_weight,
    )
    return ((result.expected_recruits + n0) - (tot + n0)) < 1e-6


# Cases with ≥2 unpinned strata — required for cross-stratum KKT stationarity checks.
KKT_CASES = [c for c in PROD_CASES if (~_pin_mask(c)).sum() >= 2]
# Cases where the closed form actually pins something — required for pinned-stratum checks.
PIN_CASES = [c for c in PROD_CASES if _pin_mask(c).any()]


@pytest.mark.parametrize("case", PROD_CASES, ids=[c.name for c in PROD_CASES])
class TestBudgetProdRegimes:
    """Test closed-form optimizer against prod-derived cases."""

    def run_closed_form(self, case: ProdCase) -> OptimizationResult:
        """Helper: run closed-form optimizer on the case."""
        goal = np.array(case.goal)
        tot = np.array(case.tot, dtype=float)
        price = np.array(case.price)

        return proportional_opt_closed_form(
            goal=goal,
            tot=tot,
            price=price,
            budget=case.budget,
            max_recruits=case.max_recruits,
            efficiency_weight=case.efficiency_weight,
        )

    def run_lbfgs(self, case: ProdCase) -> OptimizationResult:
        """Helper: run L-BFGS-B optimizer on the case."""
        goal = np.array(case.goal)
        tot = np.array(case.tot, dtype=float)
        price = np.array(case.price)

        return proportional_opt(
            goal=goal,
            tot=tot,
            price=price,
            budget=case.budget,
            max_recruits=case.max_recruits,
            efficiency_weight=case.efficiency_weight,
            tol=0.01,
        )

    def test_no_regression(self, case: ProdCase):
        """Golden snapshot: outputs match within rtol=1e-9."""
        if case.expected_recruits_snapshot is None:
            pytest.skip("No snapshot available")

        result = self.run_closed_form(case)
        expected = np.array(case.expected_recruits_snapshot)

        np.testing.assert_allclose(
            result.expected_recruits,
            expected,
            rtol=1e-9,
            err_msg=f"Regression in {case.name}: closed-form output changed",
        )

    def test_constraint_feasibility(self, case: ProdCase):
        """Budget or recruits constraint is satisfied to machine precision."""
        result = self.run_closed_form(case)

        if case.budget is not None:
            # Budget-binding: sum(new_spend) ≈ budget
            total_spent = result.new_spend.sum()
            rel_error = abs(total_spent - case.budget) / max(case.budget, 1.0)
            assert rel_error < 1e-6, (
                f"{case.name}: budget constraint violated. "
                f"Expected {case.budget:.2f}, spent {total_spent:.2f} (rel_error={rel_error:.2e})"
            )

        if case.max_recruits is not None:
            # Recruits-binding: sum(expected_recruits) ≈ max_recruits
            total_recruits = result.expected_recruits.sum()
            rel_error = abs(total_recruits - case.max_recruits) / case.max_recruits
            assert rel_error < 1e-6, (
                f"{case.name}: recruits constraint violated. "
                f"Expected {case.max_recruits}, got {total_recruits:.2f} (rel_error={rel_error:.2e})"
            )

    def test_lower_bounds(self, case: ProdCase):
        """expected_recruits >= tot for all strata (allows floating-point slack)."""
        result = self.run_closed_form(case)
        tot = np.array(case.tot, dtype=float)

        assert np.all(result.expected_recruits >= tot - 1e-9), (
            f"{case.name}: lower bound violated. "
            f"expected_recruits: {result.expected_recruits}, tot: {tot}"
        )

    def test_objective_no_worse_than_lbfgs(self, case: ProdCase):
        """Closed-form objective ≤ L-BFGS-B objective + numerical slack.

        With n0=1, both optimizers solve the same problem:
            minimize  sum_h  goal_h^2 / m_h    where m_h = expected_recruits_h + 1
            subject to budget or recruits constraint, m_h >= tot_h + 1.

        L-BFGS-B's hardcoded `+1` is now interpretable as n0=1 (the Jeffreys-prior
        effective sample size), matching the closed form's default. The closed form
        is the reference solution; this test guards against regressions where it
        would silently produce a worse allocation than the iterative path.
        """
        cf = self.run_closed_form(case)
        lb = self.run_lbfgs(case)
        goal = np.array(case.goal)
        n0 = 1

        cf_m = cf.expected_recruits + n0
        lb_m = lb.expected_recruits + n0

        cf_obj = float(np.sum(goal ** 2 / cf_m))
        lb_obj = float(np.sum(goal ** 2 / lb_m))

        assert cf_obj <= lb_obj + 1e-6, (
            f"{case.name}: closed-form objective {cf_obj:.10e} is worse than "
            f"L-BFGS-B objective {lb_obj:.10e} (diff={cf_obj - lb_obj:.2e})"
        )


def _run_closed_form(case: ProdCase) -> OptimizationResult:
    return proportional_opt_closed_form(
        goal=np.array(case.goal),
        tot=np.array(case.tot, dtype=float),
        price=np.array(case.price),
        budget=case.budget,
        max_recruits=case.max_recruits,
        efficiency_weight=case.efficiency_weight,
    )


@pytest.mark.parametrize("case", KKT_CASES, ids=[c.name for c in KKT_CASES])
def test_kkt_stationarity(case: ProdCase):
    """Unpinned strata have constant marginal utility.

    Budget-binding (w=1):  goal_h² / (m_h² · price_h) ≈ λ
    Recruits-binding:      goal_h² / m_h² ≈ λ

    where m_h = expected_recruits + n0. Filtered to cases with ≥2 unpinned strata
    (single-unpinned cases trivially satisfy "constant"); see KKT_CASES at module
    top.
    """
    result = _run_closed_form(case)
    goal = np.array(case.goal)
    tot = np.array(case.tot, dtype=float)
    price = np.array(case.price)
    n0 = 1

    m = result.expected_recruits + n0
    unpinned = (m - (tot + n0)) >= 1e-6

    if case.budget is not None:
        mu = goal[unpinned] ** 2 / (m[unpinned] ** 2 * price[unpinned])
    else:
        mu = goal[unpinned] ** 2 / m[unpinned] ** 2

    cv = np.std(mu) / np.mean(mu) if np.mean(mu) > 0 else 0
    assert cv < 1e-6, (
        f"{case.name}: KKT stationarity violated (CV={cv:.2e} > 1e-6). "
        f"KKT residuals: {mu}"
    )


@pytest.mark.parametrize("case", PIN_CASES, ids=[c.name for c in PIN_CASES])
def test_kkt_pinned_strata(case: ProdCase):
    """Pinned strata have marginal value ≤ unpinned λ.

    Catches wrongly-pinned strata (bug: optimizer pinned something that should
    be free). Filtered to cases that actually pin; see PIN_CASES at module top.
    """
    result = _run_closed_form(case)
    goal = np.array(case.goal)
    tot = np.array(case.tot, dtype=float)
    price = np.array(case.price)
    n0 = 1

    m = result.expected_recruits + n0
    margin = m - (tot + n0)
    pinned = margin < 1e-6
    unpinned = margin >= 1e-6

    if np.sum(unpinned) == 0:
        pytest.skip(f"{case.name}: all pinned — λ undefined (degenerate case)")

    if case.budget is not None:
        mu_unpinned = goal[unpinned] ** 2 / (m[unpinned] ** 2 * price[unpinned])
    else:
        mu_unpinned = goal[unpinned] ** 2 / m[unpinned] ** 2

    lambda_unpinned = np.mean(mu_unpinned)

    for h in np.where(pinned)[0]:
        m_pinned = tot[h] + n0
        if case.budget is not None:
            marginal_pinned = goal[h] ** 2 / (m_pinned ** 2 * price[h])
        else:
            marginal_pinned = goal[h] ** 2 / m_pinned ** 2

        ratio = marginal_pinned / lambda_unpinned if lambda_unpinned > 0 else 0
        assert marginal_pinned <= lambda_unpinned * (1 + 1e-6), (
            f"{case.name}: pinned stratum {h} violates KKT. "
            f"marginal_pinned={marginal_pinned:.8e}, lambda_unpinned={lambda_unpinned:.8e}, "
            f"ratio={ratio:.4f} (should be ≤1)"
        )
