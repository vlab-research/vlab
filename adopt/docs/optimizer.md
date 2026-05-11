# Budget Optimizer

The `adopt` service allocates ad spend across recruitment strata by solving a
variance-minimization problem each cycle. This doc describes the working state
of the optimizer: problem formulation, the three implementations that share the
same contract, and the testing strategy that keeps them in agreement.

Reference for the math derivation: `paper/variance_extension.tex` §9 Case A
(pure variance, `efficiency_weight = 1`). The blended case (Case B,
`efficiency_weight < 1`) is handled by CVXPY and the legacy L-BFGS-B path —
closed-form is intentionally pure-variance only; see *Why no closed-form for
blended?* below.

## Problem

Per cycle we have, for each stratum `h ∈ 1..H`:

- `goal_h` — target proportion of total sample (sums to 1 across strata).
- `tot_h` — respondents already recruited.
- `price_h` — current cost per recruit.
- `sigma_h` — per-stratum outcome variance estimate (1.0 by default; per-stratum
  values arrive from `estimate_variance`, see below).
- `n0` — prior effective sample size, default 1 (= α + β under the Jeffreys
  Beta(½,½) prior). See *Bayesian prior coupling* below.

We choose `expected_recruits_h ≥ tot_h` to:

    minimize    w · sum_h (goal_h · sigma_h)^2 / m_h  +  (1 − w) / sum_h m_h
                where  m_h := expected_recruits_h + n0, w := efficiency_weight
    subject to  either  sum_h price_h · (expected_recruits_h - tot_h) == budget   (budget-binding)
                or      sum_h expected_recruits_h == max_recruits                  (recruits-binding)
                expected_recruits_h ≥ tot_h

At `w = 1` the efficiency term drops out and the objective is pure-variance
(Neyman-on-a-prior). At `w < 1` the `(1 − w) / Σ m_h` term penalizes small total
sample size, biasing allocations toward cheap strata. Only CVXPY and the legacy
path handle `w < 1`; closed-form raises `NotImplementedError`.

For the recruits-binding subproblem, the efficiency term `(1 − w) / M_prime` is
*constant* on the feasible set (Σ m is pinned by the constraint), so the
blended objective reduces to pure-variance there for any `w ∈ (0, 1]`.

`m_h` is the *effective sample size* — data (`tot + new_recruits`) plus prior
(`n0`). The variance term `1/m_h` is the variance of the weighted stratified-mean
estimator under prior + data. Working in `m`-space makes the lower bound
`m_h ≥ tot_h + n0` and KKT condition `m_h ∝ goal_h · sigma_h` clean.

When both constraints are present we solve both subproblems and return whichever
binds (smaller `new_spend`), plus the counterfactual from the non-binding one.

## Bayesian prior coupling

`n0` is the effective sample size of the prior on the outcome variance. With
Beta(α, β) on Bernoulli `π`, posterior is Beta(α + s, β + n - s) and the
posterior mean of `π(1-π)` is `(α+s)(β+n-s) / ((α+β+n)(α+β+n+1))`. The prior
contributes `α + β` virtual observations.

For internal consistency the optimizer's `n0` and the variance estimator's prior
must come from the same hyperparameters: **`n0 = α + β`**. Default `(α, β) =
(½, ½)` → `n0 = 1`. If a caller switches to e.g. Beta(2, 2), it must pass
`n0 = 4` to the optimizer.

`estimate_variance(n, s, prior=(α, β))` in `adopt/adopt/budget.py` is the pure
function implementing the posterior-mean estimate. As of 2026-05-10 it is a
Layer 1 stub: no production caller wires it in. When it ships, the call site
must pass `n0 = α + β` from the same prior to the optimizer.

## Three implementations, one contract

| Function | Solver | Role |
|---|---|---|
| `proportional_opt_closed_form` | Analytic active-set | Pure-variance primary path (`w = 1` only). Microseconds, exact, inspectable. Raises `NotImplementedError` on `w < 1`. |
| `proportional_opt_cvxpy` | CVXPY + ECOS, CLARABEL fallback | Handles all `w ∈ [0, 1]`. Acts as oracle for closed-form at `w = 1`; primary path for blended `w < 1`. |
| `proportional_opt` | `scipy.optimize.minimize` (L-BFGS-B) | Legacy. Handles all `w ∈ [0, 1]`. Still the production default via the `optimizer_version` flag until cutover. |

At `w = 1` all three solve the same problem under `n0 = 1`. At `w < 1` only the
latter two are available. Cross-validation lives in the test suite (see
*Testing* below); empirical agreement is in
[`optimizer-validation.md`](optimizer-validation.md).

L-BFGS-B's hardcoded `+1` in the projection (`m = C·spend + tot + 1`) is now
interpretable as exactly the same `n0 = 1` prior shift, which is why all three
optimizers reach the same objective.

## Closed-form algorithm

KKT stationarity on unpinned strata gives `m_h ∝ goal_h · sigma_h` (recruits-binding)
or `m_h ∝ goal_h · sigma_h / √price_h` (budget-binding). The lower bound
`m_h ≥ tot_h + n0` can bind on a non-trivial subset of strata in two ways:

1. A stratum past its proportional share (`tot_h` large for its `goal_h`).
2. A low-`goal_h` stratum where the variance contribution is small enough that
   any additional mass is more usefully spent elsewhere.

We handle both with active-set iteration: allocate proportionally, pin any
stratum below its lower bound at the bound, subtract its pinned mass from the
constraint, re-allocate the active set, repeat until no new pins.

Two helpers in `budget.py`:

- `_active_set_allocate(goal, sigma, price, tot, B_prime, n0)` — budget-binding,
  where `B_prime = B + p^T(tot + n0)` and the allocation rule includes `1/√p`.
- `_active_set_allocate_recruits(goal, sigma, tot, M_prime, n0)` — recruits-binding,
  where `M_prime = max_recruits + H·n0` and price drops out of the allocation
  rule and lower-bound bookkeeping.

Termination is `O(H)` (at most one stratum pins per iteration; `H` iterations
suffice). For `H ≤ 72` the whole solve is microseconds with no framework
overhead.

## Why no closed-form for blended?

Adding the `(1 − w) / S` term where `S := Σ_h m_h` couples all strata through a
single scalar `S`, so there is no analytic closed form. KKT (math note Eq.
eq:blended-mh) reduces it to two scalar unknowns `(λ, S)` solvable by nested
bisection. We implemented this (`_blended_bisection_budget`) and then retired
it. Reasoning:

- It is *numerical*, not analytic — nested bisection with its own convergence
  tolerance and bracket-expansion logic. Not "exact" in any meaningful sense
  beyond what CVXPY achieves.
- It was slower than CVXPY (~80–120 ms vs ~15 ms on prod cases), because each
  bisection iteration evaluates an O(H) numpy expression in a Python loop.
- It was ~150 lines of subtle code (active-set pinning, slack-shrinking,
  dual-bracket logic) with no clear advantage over a 10-line CVXPY objective
  change.

The pure-variance closed-form's advantages — analytic exactness, 200×+
speedup, inspectable allocation rule — don't carry over to the blended case.
For `w < 1`, route through `proportional_opt_cvxpy` (or the legacy
`proportional_opt`). See [`optimizer-validation.md`](optimizer-validation.md)
for the empirical numbers behind this decision.

## CVXPY runtime path

`proportional_opt_cvxpy` builds the same convex program with `cp.inv_pos(m)` for
the variance term plus `(1 − w) · cp.inv_pos(cp.sum(m))` for the efficiency
term when `w < 1`, and `m ≥ tot + n0` for the lower bound. It serves two roles:

1. **Primary path for `w < 1`.** Closed-form is pure-variance only; CVXPY (or
   the legacy L-BFGS-B path) handles blended objectives. CVXPY is preferred:
   it produces a tighter solution than L-BFGS-B (the latter has a ~1e-4
   allocation noise floor from its degenerate parameterization).
2. **Independent oracle for `w = 1`.** An interior-point solver in a different
   code path is the strongest regression sentinel for the closed-form active
   set. The two agree elementwise to `rtol = 1e-6` on every prod case.

Future objective extensions (correlated outcomes, regularization, per-stratum
precision constraints) drop into CVXPY without reaching for new analytic
derivations.

Wired into the `optimizer_version` flag as a third option. Closed form remains
the default.

For numeric configuration (rescaling, solver tolerances, asymmetric status
acceptance for ECOS vs CLARABEL), see [`optimizer-validation.md`](optimizer-validation.md).

## Testing

Four layers:

1. **Hand-derived anchors** (`test_budget_closed_form.py::TestClosedFormHandComputed`
   and `TestProduction9cd58b37Bug`). Small H=2/3/4 cases where the optimum is
   computable by hand from the math note. These pin the algorithm to the
   correct math; everything else is regression-only.

2. **Prod-regime parametric tests** (`test_budget_prod_regimes.py`). Six cases
   extracted from real `FACEBOOK_ADOPT` reports, each run through 6 assertions:
   snapshot match, constraint feasibility, lower bounds, KKT stationarity on
   unpinned strata, KKT complementary slackness on pinned strata, and objective
   no worse than L-BFGS-B.

3. **CVXPY oracle** (`test_budget_cvxpy_oracle.py`). Same prod cases, asserts
   `expected_recruits` from CVXPY matches closed form to `rtol=1e-6`. Catches
   any future active-set bug at interior-point precision.

4. **System-level optimizer-parametrized tests** (`test_budget.py`). The
   end-to-end `proportional_budget` tests run under a pytest fixture
   parametrizing over `[proportional_opt, proportional_opt_closed_form]`. Both
   solvers must satisfy the same scenarios (turn-off-empty-groups, drop-to-zero-
   budget, prioritize-underperforming, etc.) for `efficiency_weight = 1.0`.

5. **Blended cross-checks** (`test_budget_blended.py`). For `w ∈ {0.25, 0.5,
   0.75, 0.9, 0.99}`: CVXPY blended ≡ L-BFGS-B blended (allocation
   `rtol = 1e-3`), CVXPY blended satisfies the blended-KKT equation
   (Eq. eq:blended-mh on unpinned strata), budget feasibility,
   `w → 1` reduces to pure variance, closed-form rejects `w != 1`.

The four layers together: a unit test for math correctness (1), regression
guards against silent drift (2), an independent solver as oracle (3), and a
system contract that both deployed paths must honor (4).

## Deployment

This section describes how the three optimizers are selected at run time.
Full rationale and phase-by-phase plan in `planning/soak-deployment.md`.

### Dispatch

`budget._pick_optimizer(efficiency_weight)` picks the live optimizer:

- env `ADOPT_OPTIMIZER_DEFAULT=lbfgs` → force legacy `proportional_opt`
  (L-BFGS-B). This is the global rollback switch — flip it in helm values to
  revert without redeploying app code.
- otherwise: `proportional_opt_closed_form` for `w == 1`,
  `proportional_opt_cvxpy` for `w < 1`.

There is no per-study override. The decision is global.

### Shadow phase (current)

`get_budget_lookup` serves the L-BFGS-B allocation to production but also runs
`_pick_optimizer(...)` in parallel and logs a structured `optimizer_shadow`
record per optimization cycle:

- `study_id`, `H`, `efficiency_weight`, `optimizer_version`
- `lbfgs_time_ms`, `shadow_time_ms`
- `max_abs_relative_diff_vs_lbfgs`
- `budget_residual` (sum-of-spend vs target budget, relative)
- `any_negative_spend`

The shadow run is **not** wrapped in try/except — if cvxpy/closed-form throws,
the optimization cycle fails loudly. Better to surface a bug immediately than
swallow it.

### Cutover

When shadow soak passes acceptance criteria, swap the served allocation to the
new path: `optimizer=shadow_optimizer` instead of `optimizer=proportional_opt`
in the `proportional_budget` call inside `get_budget_lookup`, and drop the
parallel L-BFGS-B compute. The env-var rollback continues to work because
`_pick_optimizer` honors it.

## File map

| File | Contents |
|---|---|
| `adopt/adopt/budget.py` | All three optimizer functions, the two active-set helpers, `estimate_variance`, the `proportional_budget` wrapper that dicts/undicts arrays. |
| `adopt/adopt/test_budget.py` | System-level tests, optimizer-parametrized via the `optimizer` fixture. Also covers `estimate_variance`, `estimate_price`, `calculate_strata_stats`, `get_budget_lookup`. |
| `adopt/adopt/test_budget_closed_form.py` | Hand-derived math anchors and the H=4 active-set regression case. |
| `adopt/adopt/test_budget_prod_regimes.py` | Six prod-derived parametric cases × six assertions. |
| `adopt/adopt/test_budget_cvxpy_oracle.py` | CVXPY ≡ closed-form on every prod case to `rtol=1e-6` at `w = 1`. |
| `adopt/adopt/test_budget_blended.py` | Blended (`w ∈ {0.25, 0.5, 0.75, 0.9, 0.99}`) tests: CVXPY ≡ L-BFGS-B, CVXPY KKT stationarity, w → 1 limit, closed-form-rejects-blended. |
| `adopt/docs/optimizer.md` | This file. |
| `adopt/docs/optimizer-validation.md` | Three-way empirical comparison (closed-form / CVXPY / L-BFGS-B) and solver-config rationale. |
| `adopt/docs/efficiency-weight-optimization.md` | The blended-objective math; closed-form + CVXPY implementations now live in `budget.py`. |
| `paper/variance_extension.tex` | Full derivation and proofs. |
