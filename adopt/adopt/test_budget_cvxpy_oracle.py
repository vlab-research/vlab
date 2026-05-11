"""Oracle tests: closed-form ≡ CVXPY on prod cases.

Cross-checks `proportional_opt_closed_form` against `proportional_opt_cvxpy` (ECOS
interior-point) on every budget-binding ProdCase. Provides a tighter regression
bound (≤ 1e-6 rel diff) than the L-BFGS-B comparison in test_budget_prod_regimes.

See planning/cvxpy-test-oracle.md.
"""

import numpy as np
import pytest

from adopt.budget import (
    OptimizationResult,
    proportional_opt_closed_form,
    proportional_opt_cvxpy,
)

from .test_budget_prod_regimes import PROD_CASES, PIN_CASES, ProdCase


BUDGET_BINDING_CASES = [c for c in PROD_CASES if c.budget is not None]
# Pin comparison only meaningful when the closed-form actually pins. Intersect
# with budget-binding (recruits-binding uses a different pin code path).
PINNING_BUDGET_CASES = [c for c in PIN_CASES if c.budget is not None]


def _run(fn, case: ProdCase) -> OptimizationResult:
    return fn(
        goal=np.array(case.goal),
        tot=np.array(case.tot, dtype=float),
        price=np.array(case.price),
        budget=case.budget,
        max_recruits=case.max_recruits,
        efficiency_weight=case.efficiency_weight,
    )


@pytest.mark.parametrize("case", BUDGET_BINDING_CASES, ids=[c.name for c in BUDGET_BINDING_CASES])
def test_cvxpy_matches_closed_form_budget_binding(case: ProdCase):
    """Closed-form ≡ CVXPY+ECOS on expected_recruits, elementwise."""
    cf = _run(proportional_opt_closed_form, case)
    cvx = _run(proportional_opt_cvxpy, case)

    np.testing.assert_allclose(
        cvx.expected_recruits,
        cf.expected_recruits,
        rtol=1e-6,
        atol=1e-9,
        err_msg=(
            f"{case.name}: CVXPY and closed-form disagree.\n"
            f"  closed_form: {cf.expected_recruits}\n"
            f"  cvxpy:       {cvx.expected_recruits}"
        ),
    )


@pytest.mark.parametrize("case", PINNING_BUDGET_CASES, ids=[c.name for c in PINNING_BUDGET_CASES])
def test_cvxpy_matches_closed_form_pinned_strata(case: ProdCase):
    """If closed-form pins a stratum at its lower bound, CVXPY pins it too.

    Specifically catches active-set bugs: the closed-form active-set algorithm
    decides which strata to pin combinatorially, and the CVXPY interior-point
    solution provides an independent verification.

    Filtered to cases that actually pin; see PIN_CASES in test_budget_prod_regimes.
    """
    cf = _run(proportional_opt_closed_form, case)
    cvx = _run(proportional_opt_cvxpy, case)

    tot = np.array(case.tot, dtype=float)
    cf_pinned = cf.expected_recruits <= tot + 1e-9

    for h in np.where(cf_pinned)[0]:
        tol = 1e-6 * max(tot[h], 1.0) + 1e-9
        assert cvx.expected_recruits[h] <= tot[h] + tol, (
            f"{case.name}: closed-form pinned stratum {h} (expected_recruits={cf.expected_recruits[h]:.6e}, "
            f"tot={tot[h]:.6e}) but CVXPY did not "
            f"(cvxpy expected_recruits={cvx.expected_recruits[h]:.6e})"
        )
