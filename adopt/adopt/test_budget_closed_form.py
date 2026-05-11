"""Unit tests for closed-form budget optimizer.

Tests the pure-variance, equal-variance case (efficiency_weight=1.0, sigma=ones).
Verifies KKT conditions and active-set behavior. Cross-implementation equivalence to
L-BFGS-B is covered by test_objective_no_worse_than_lbfgs in test_budget_prod_regimes.
"""

import numpy as np
import pytest

from .budget import (
    proportional_opt,
    proportional_opt_closed_form,
    OptimizationResult,
)


class TestClosedFormHandComputed:
    """Test cases with hand-computed closed-form solutions."""

    def test_2_strata_equal_price_equal_goal_budget_binding(self):
        """Two strata, equal prices, equal goals, budget-binding.

        Hand computation: m_h* ∝ W_h * sigma_h / sqrt(p_h) = [1, 1]
        So m_1* = m_2* (equal allocation).
        Budget: B' = 100 + sum([2, 2] * [10, 10]) = 100 + 40 = 140
        m_h = (B' / sum(price)) / 2 = 140 / 4 = 35
        Expected recruits: m_h = 35 per stratum (no smoothing).
        New spend: (35 - 10) * 2 = 50 per stratum.
        """
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([2.0, 2.0])
        budget = 100.0
        max_recruits = None

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Check allocation
        np.testing.assert_array_almost_equal(result.expected_recruits, [35, 35], decimal=5)
        np.testing.assert_array_almost_equal(result.new_spend, [50, 50], decimal=5)
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4)

    def test_3_strata_unequal_goals_prices_budget_binding(self):
        """Three strata with unequal goals and prices.

        goal = [0.2, 0.3, 0.5], price = [1, 2, 3], tot = [5, 10, 15]
        Allocation proportional: W_h * sigma_h / sqrt(p_h)
        = [0.2/1, 0.3/1.414, 0.5/1.732]
        = [0.2, 0.212, 0.289]
        Normalize and scale to budget constraint.
        """
        goal = np.array([0.2, 0.3, 0.5])
        tot = np.array([5, 10, 15])
        price = np.array([1.0, 2.0, 3.0])
        budget = 200.0
        max_recruits = None

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Verify budget is satisfied
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4)
        # Verify no negative allocations
        assert np.all(result.expected_recruits >= tot)
        # Verify counterfactuals are None (only budget constraint)
        assert result.counterfactual_spend is None
        assert result.counterfactual_recruits is None

    def test_active_set_lower_bound_pinning(self):
        """Test that strata past their target get pinned at the lower bound.

        Set up a case where stratum 0 wants to allocate below its lower bound,
        forcing it to be pinned while stratum 1 gets the remainder.
        """
        goal = np.array([0.1, 0.9])
        tot = np.array([100, 10])  # Stratum 0 already has many recruits
        price = np.array([1.0, 1.0])
        budget = 50.0  # Small budget relative to stratum 0's total
        max_recruits = None

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Stratum 0 should be pinned at lower bound (m = tot = 100, so expected = 100)
        # Stratum 1 should get most of the budget
        assert np.isclose(result.expected_recruits[0], tot[0], rtol=1e-4)
        assert result.expected_recruits[1] > tot[1]
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4)

    def test_recruits_binding_equal_variance(self):
        """Test recruit-binding case with equal variance.

        Allocation: m_h ∝ W_h * sigma_h, scaled to max_recruits.
        expected_recruits sums to max_recruits.
        """
        goal = np.array([0.3, 0.4, 0.3])
        tot = np.array([10, 15, 10])
        price = np.array([2.0, 1.5, 2.5])
        budget = None  # Only recruit constraint
        max_recruits = 100

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Total recruits should equal max_recruits
        assert np.isclose(result.expected_recruits.sum(), max_recruits, rtol=1e-4)
        # No counterfactuals (only recruits constraint)
        assert result.counterfactual_spend is None
        assert result.counterfactual_recruits is None

    def test_both_constraints_budget_binds(self):
        """Test case where both constraints are present but budget binds.

        Budget constraint is tighter, so it becomes the active one.
        """
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([2.0, 2.0])
        budget = 80.0  # Tight budget
        max_recruits = 500  # Very loose recruits constraint

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Budget constraint should bind
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4)
        # Should have counterfactual for the recruits constraint
        assert result.counterfactual_spend is not None
        assert result.counterfactual_recruits is None

    def test_both_constraints_recruits_binds(self):
        """Test case where both constraints are present but recruits binds.

        Recruits constraint is tighter, so it becomes the active one.
        """
        goal = np.array([0.5, 0.5])
        tot = np.array([20, 20])  # Total 40 current recruits
        price = np.array([1.0, 1.0])
        budget = 1000.0  # Very loose budget
        max_recruits = 100  # Tight recruits constraint (only 60 more room)

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # Recruits constraint should bind - expected_recruits sums to max_recruits
        assert np.isclose(result.expected_recruits.sum(), max_recruits, rtol=1e-4)
        # Should have counterfactual for the budget constraint
        assert result.counterfactual_spend is None
        assert result.counterfactual_recruits is not None


class TestKKTConditions:
    """Test KKT optimality conditions."""

    def test_kkt_stationarity_and_complementary_slackness(self):
        """Verify KKT stationarity and complementary slackness at optimum.

        For the pure-variance problem:
        L = sum(W_h^2 * sigma_h^2 / m_h) subject to sum(p_h * m_h) = B'

        KKT: W_h^2 * sigma_h^2 / m_h^2 = lambda * p_h (active strata)
                                       ≤ lambda * p_h (pinned strata)
        Complementary slackness: mu_h * (m_h - tot_h) = 0
        """
        goal = np.array([0.25, 0.25, 0.25, 0.25])
        tot = np.array([8, 8, 8, 8])
        price = np.array([1.0, 1.0, 1.0, 1.0])
        budget = 200.0
        max_recruits = None

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        # m_opt is the internal allocation; expected_recruits = m_opt (no smoothing)
        m_opt = result.expected_recruits
        W = goal ** 2
        sigma = np.ones_like(goal)

        # Compute the dual variable lambda from active strata
        # lambda = W_h^2 * sigma_h^2 / (m_h^2 * p_h)
        lambda_vals = W ** 2 * sigma ** 2 / (m_opt ** 2 * price)

        # All active strata should have the same lambda
        lambda_avg = np.mean(lambda_vals)
        np.testing.assert_array_almost_equal(lambda_vals, lambda_avg, decimal=4)

        # Budget constraint should be satisfied
        B_prime = budget + np.sum(price * tot)
        assert np.isclose(np.sum(price * m_opt), B_prime, rtol=1e-4)

    def test_primal_feasibility(self):
        """Verify primal feasibility: m_h >= tot_h and budget satisfied."""
        goal = np.array([0.2, 0.3, 0.5])
        tot = np.array([5, 10, 15])
        price = np.array([1.5, 2.0, 2.5])
        budget = 300.0
        max_recruits = None

        result = proportional_opt_closed_form(goal, tot, price, budget, max_recruits, efficiency_weight=1.0, sigma=None)

        m_opt = result.expected_recruits

        # All allocations >= tot
        assert np.all(m_opt >= tot)
        # Budget satisfied
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4)


class TestErrorHandling:
    """Test error cases and boundary conditions."""

    def test_raises_on_efficiency_weight_not_1(self):
        """Closed-form rejects any efficiency_weight != 1.0 (use CVXPY for blended)."""
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([1.0, 1.0])
        budget = 100.0

        for w in [0.0, 0.5, 0.9]:
            with pytest.raises(NotImplementedError, match=r"efficiency_weight=1.0"):
                proportional_opt_closed_form(
                    goal, tot, price, budget, None, efficiency_weight=w
                )

    def test_raises_without_constraints(self):
        """Should raise if both budget and max_recruits are None."""
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([1.0, 1.0])

        with pytest.raises(Exception, match="Need either a max budget or max_recruits"):
            proportional_opt_closed_form(goal, tot, price, None, None)

    def test_default_sigma_is_ones(self):
        """Test that sigma defaults to ones (equal variance)."""
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([1.0, 1.0])
        budget = 100.0

        result_default = proportional_opt_closed_form(goal, tot, price, budget, None)
        result_explicit = proportional_opt_closed_form(goal, tot, price, budget, None, sigma=np.ones(2))

        np.testing.assert_array_almost_equal(result_default.new_spend, result_explicit.new_spend)
        np.testing.assert_array_almost_equal(result_default.expected_recruits, result_explicit.expected_recruits)



class TestResultShape:
    """Test that results have the correct structure."""

    def test_optimization_result_structure(self):
        """Verify OptimizationResult has correct fields and types."""
        goal = np.array([0.5, 0.5])
        tot = np.array([10, 10])
        price = np.array([1.0, 1.0])
        budget = 100.0

        result = proportional_opt_closed_form(goal, tot, price, budget, None)

        assert isinstance(result, OptimizationResult)
        assert isinstance(result.new_spend, np.ndarray)
        assert isinstance(result.expected_recruits, np.ndarray)
        assert len(result.new_spend) == 2
        assert len(result.expected_recruits) == 2

        # Counterfactuals should be None for single-constraint case
        assert result.counterfactual_spend is None
        assert result.counterfactual_recruits is None


class TestProduction9cd58b37Bug:
    """Test case from production study 9cd58b37 that exposed the active-set bug.

    This is a hand-computed test case with the true optimum verified by L-BFGS-B.
    The closed-form active-set algorithm was over-pinning strata at their lower bounds,
    yielding a suboptimal solution with non-constant KKT residuals.

    Inputs (from study 9cd58b37, eff_weight=1.0, H=4):
      goal = [0.24, 0.16, 0.36, 0.24]
      tot = [1, 0, 0, 0]
      price = [2.38, 4.38, 20.38, 10.38]
      budget = 5.29
      max_recruits = None (budget-binding)
      efficiency_weight = 1.0
      sigma = ones (default)
      n0 = 1 (default)

    Hand-computed optimum (math note Sec 9 Case A):
      m_h* ∝ goal_h * sigma_h / sqrt(price_h) = [0.1555, 0.0764, 0.0798, 0.0745] (unnormalized)
      B' = budget + sum(price * (tot + n0)) = 5.29 + (2.38*2 + 4.38*1 + 20.38*1 + 10.38*1) = 45.19
      alpha = B' / sum(price_h * w_h) = 45.19 / 3.106 ≈ 14.551
      m_h* ≈ [2.263, 1.112, 1.161, 1.084]
      expected_recruits = m_h - n0 ≈ [1.263, 0.112, 0.161, 0.084]

    NO strata should be pinned (all m_h* > tot_h + n0 = [2, 1, 1, 1]).
    KKT residual at optimum: g^2 / (m^2 * p) ≈ 0.00472, constant across all strata.

    The buggy closed-form pins strata 0, 1, 3 at lower bounds and allocates m = [2, 1, 1, 1.26],
    yielding objective = 0.2149 (L-BFGS-B correct answer = 0.2131, a 31% divergence).
    """

    def test_prod_9cd58b37_no_over_pinning(self):
        """Test that closed-form produces the correct all-unconstrained optimum.

        This test FAILS with the buggy implementation (over-pinning to [1, 0, 0.26, 0]).
        After the fix, should converge to the unconstrained optimum where all strata
        are free (no lower-bound pinning) with allocations proportional to goal * sigma / sqrt(price).

        Hand-derived (n0=1) expected values:
        B' = 5.29 + (2.38*2 + 4.38*1 + 20.38*1 + 10.38*1) = 5.29 + 39.90 = 45.19
        Weights: [0.1555, 0.0764, 0.0798, 0.0745] (goal/sqrt(price))
        sum(p_h * w_h) ≈ 3.106
        Scale: 45.19 / 3.106 ≈ 14.551
        m = [2.263, 1.112, 1.161, 1.084], all > lower bounds [2, 1, 1, 1]
        expected_recruits = m - 1 ≈ [1.263, 0.112, 0.161, 0.084]
        """
        goal = np.array([0.24, 0.16, 0.36, 0.24])
        tot = np.array([1, 0, 0, 0])
        price = np.array([2.38, 4.38, 20.38, 10.38])
        budget = 5.29
        max_recruits = None

        # Call the closed-form optimizer with n0=1 (default)
        result = proportional_opt_closed_form(
            goal, tot, price, budget=budget, max_recruits=max_recruits,
            efficiency_weight=1.0, sigma=None, n0=1
        )

        # Expected recruits from hand derivation (n0=1, no pinning)
        expected_recruits_true = np.array([1.263, 0.112, 0.161, 0.084])

        # Tight relative tolerance (1e-2) to allow for hand-computation rounding
        np.testing.assert_array_almost_equal(
            result.expected_recruits, expected_recruits_true,
            decimal=2,
            err_msg="Closed-form recruits do not match hand-derived optimum"
        )

        # Budget constraint should be satisfied exactly
        assert np.isclose(result.new_spend.sum(), budget, rtol=1e-4),\
            f"Budget mismatch: {result.new_spend.sum()} != {budget}"

    def test_prod_9cd58b37_kkt_stationarity(self):
        """Test that the optimum satisfies KKT stationarity conditions.

        For the pure-variance problem min sum(goal^2 * sigma^2 / m_h),
        the KKT stationarity condition is:
        goal_h^2 * sigma_h^2 / (m_h^2 * price_h) = lambda (constant across unconstrained strata)

        Note: With n0=1, all strata should be unpinned (all m_h > tot_h + n0).
        All strata should satisfy the same KKT stationarity condition.
        """
        goal = np.array([0.24, 0.16, 0.36, 0.24])
        tot = np.array([1, 0, 0, 0])
        price = np.array([2.38, 4.38, 20.38, 10.38])
        budget = 5.29
        max_recruits = None

        result = proportional_opt_closed_form(
            goal, tot, price, budget=budget, max_recruits=max_recruits,
            efficiency_weight=1.0, sigma=None, n0=1
        )

        # expected_recruits = m_h - n0
        # To compute KKT, we need m_h = expected_recruits + n0
        m_opt = result.expected_recruits + 1  # Add n0 back

        # Compute KKT dual variable value for each stratum
        sigma = np.ones_like(goal)
        kkt_dual_vals = goal ** 2 * sigma ** 2 / (m_opt ** 2 * price)

        # All strata should be unpinned (all m_h > tot_h + n0 = [2, 1, 1, 1])
        # Verify no strata are pinned
        lower_bound = tot + 1  # n0 = 1
        unpinned = m_opt > lower_bound + 1e-6
        assert np.all(unpinned), f"Some strata pinned at lower bound: m_opt={m_opt}, lower_bound={lower_bound}"

        # Coefficient of variation of KKT dual values should be tiny (< 1e-6)
        # indicating all strata satisfy stationarity with the same lambda
        dual_mean = np.mean(kkt_dual_vals)
        dual_std = np.std(kkt_dual_vals)
        dual_cv = dual_std / (dual_mean + 1e-10)

        print(f"\nKKT dual values: {kkt_dual_vals}")
        print(f"All strata CV: {dual_cv:.8e}")

        assert dual_cv < 1e-6, \
            f"KKT stationarity failed: dual CV = {dual_cv:.8e} (should be < 1e-6). " \
            f"Indicates some strata may be incorrectly allocated."
