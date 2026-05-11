# Optimizer Validation — Empirical Results & Solver Notes

Companion to [`optimizer.md`](optimizer.md). The contract (closed form ≡ CVXPY
to `rtol=1e-6` for pure variance, `rtol=1e-4` for blended) is enforced by
`test_budget_cvxpy_oracle.py` and `test_budget_blended.py`. This note records
the *observed* numerical agreement between the three optimizers
(`proportional_opt_closed_form`, `proportional_opt_cvxpy`, `proportional_opt`)
on the prod cases — for both the pure-variance and blended-objective regimes —
plus the solver-configuration rationale that the tests don't capture.

## Three-Way Comparison on Prod Cases

All 6 budget-binding `PROD_CASES` from `adopt/adopt/test_budget_prod_regimes.py`,
run through `proportional_opt_closed_form` (CF), `proportional_opt_cvxpy` (CVX),
and `proportional_opt` (L-BFGS-B legacy). Reported metrics:

- **CF vs CVX rel** — max relative diff on `expected_recruits` elementwise
- **CF vs LBFGS rel** — same, against the legacy path
- **obj** — objective `sum(goal² / (expected_recruits + n0))`, n0=1
- **budget err** — `|sum(new_spend) - budget|` (constraint satisfaction)

| case                       | H | CF vs CVX rel | CF vs LBFGS rel | obj_CF         | obj_CVX        | obj_LBFGS      | budget err CF | budget err CVX | budget err LBFGS |
|----------------------------|---|---------------|-----------------|----------------|----------------|----------------|---------------|----------------|------------------|
| case_1_H4_budget19_tot1    | 4 | 1.6e-11       | 6.0e-05         | 6.873326e-02   | 6.873326e-02   | 6.873326e-02   | 0             | 3.6e-15        | 0                |
| case_2_H2_budget19_tot1    | 2 | 3.6e-15       | 1.2e-16         | 1.040409e-01   | 1.040409e-01   | 1.040409e-01   | 3.6e-15       | 3.6e-15        | 0                |
| case_3_H6_budget4558_tot54 | 6 | 9.0e-08       | 2.0e-04         | 2.406091e-03   | 2.406091e-03   | 2.406091e-03   | 0             | 1.8e-12        | 0                |
| case_4_H6_budget4308_tot100| 6 | 1.8e-07       | 7.2e-05         | 2.185777e-03   | 2.185777e-03   | 2.185777e-03   | 9.1e-13       | 9.1e-13        | 9.1e-13          |
| case_5_H2_budget15_tot6    | 2 | 4.5e-14       | 1.6e-16         | 7.019161e-02   | 7.019161e-02   | 7.019161e-02   | 1.8e-15       | 7.1e-15        | 0                |
| case_6_H2_budget4797_tot1  | 2 | 4.6e-13       | 2.8e-05         | 8.187396e-04   | 8.187396e-04   | 8.187396e-04   | 0             | 0              | 0                |

Generated 2026-05-10; reproduce with the snippet at the end.

## Reading the Table

**All three optimizers reach the same objective to 6+ digits on every case.**
The optimum is unambiguous — what differs is *solver precision on the variable*,
not the answer to the problem.

**Three-tier precision hierarchy.** This is the practical reason for keeping
both cross-checks (legacy and CVX oracle):

| Reference          | Achieves on `expected_recruits` | Role                                              |
|--------------------|--------------------------------|---------------------------------------------------|
| Closed form        | Analytic exact (active-set)     | Primary path; the reference solution               |
| CVXPY + ECOS       | 1e-11 to 1e-15 on easy cases    | Tight oracle (`rtol=1e-6` bound, ~1000× headroom) |
| CVXPY + CLARABEL   | ~1e-7 on hard H=6 cases         | Fallback oracle when ECOS hits its iteration cap   |
| L-BFGS-B (legacy)  | ~1e-4 noise floor               | Loose secondary check ("no worse than legacy")     |

The L-BFGS-B floor at ~1e-4 is set by its `ftol=1e-14, gtol=1e-10, eps=1e-12`
plus the degenerate scaling parameterization in `proportional_opt` (the
`s = S / S.sum()` workaround for L-BFGS-B not supporting native equality
constraints). H=2 cases (case_2, case_5) come out
near-machine-precision because the problem is effectively a single degree of
freedom, which L-BFGS-B can resolve.

**Budget constraint** is satisfied to machine precision (~1e-12 or better) by
all three optimizers on every case. No optimizer leaves money on the table.

## Solver Configuration — What Works and Why

The plan's nominal recipe ("ECOS with `abstol/reltol/feastol = 1e-10`, CLARABEL
fallback") did not converge as written. Two adjustments were required, both
documented inline in `adopt/adopt/budget.py::_solve_cvxpy_budget_binding`.

### 1. Variable rescaling

The native problem is poorly scaled: `expected_recruits` is O(100) on prod
cases, the objective coefficients `(goal·σ)²` are O(0.1), and `cp.inv_pos(m)`
is therefore O(1e-3). Asking ECOS for `abstol=1e-10` on an objective of
magnitude 1e-3 forces it to drive a duality gap that's already at the
solver's effective precision floor.

Fix: solve in `m_tilde = m / M` where `M = B' / sum(price)` (the average
per-stratum allocation). The reformulated problem is mathematically
equivalent (linear change of variables) but the variable is O(1), so tight
tolerances are reachable. Budget constraint becomes `price @ m_tilde == B'/M`;
lower bound becomes `m_tilde >= (tot + n0) / M`. The caller multiplies the
returned `m_tilde` by `M` to recover the answer.

Before rescaling: case_6 returned `expected_recruits` off by 1.3% (the test
that exposed this is preserved). After rescaling: case_6 agrees to 4.6e-13.

### 2. Asymmetric status acceptance

ECOS and CLARABEL behave differently when they hit `OPTIMAL_INACCURATE`:

- **ECOS** `OPTIMAL_INACCURATE` on these problems can be off by ~1e-3
  (case_3, case_4 with default tolerances). Not acceptable for a 1e-6 oracle.
- **CLARABEL** `OPTIMAL_INACCURATE` reliably stays within 1e-7 because of its
  interior-point refinement. Accepting it is the difference between case_4
  failing and passing.

Helper policy:
- Try ECOS first (faster). Accept `OPTIMAL` only.
- On `OPTIMAL_INACCURATE` or `SolverError`, fall through to CLARABEL.
- From CLARABEL, accept `OPTIMAL` or `OPTIMAL_INACCURATE`.
- If both refuse, raise `RuntimeError` with status, error, and inputs.

ECOS raises `SolverError` (not a non-optimal status) when it diverges, so the
helper has to catch the exception, not just check `problem.status`.

### 3. Requested tolerances

`abstol=reltol=feastol=1e-12` for ECOS and the matching `tol_gap_abs/rel/feas`
for CLARABEL. With rescaling these are reachable. CLARABEL uses different
setting names (`tol_gap_abs`, not `eps_abs` or `abstol`) — the helper
dispatches per solver via a `solver_opts` dict.

`max_iters=400` (ECOS) and `max_iter=5000` (CLARABEL) — generous enough that
the helper never bails for iteration-cap reasons, only for genuine
non-convergence.

## Blended Objective (`efficiency_weight < 1`)

The blended objective

    L(m) = w · Σ_h (goal_h · sigma_h)² / m_h  +  (1 − w) / Σ_h m_h

is handled by CVXPY (extra `(1−w)·cp.inv_pos(cp.sum(m))` term in the convex
program) and the legacy L-BFGS-B path. Closed-form
(`proportional_opt_closed_form`) raises `NotImplementedError` for `w < 1` —
see the *Decision Record* section below for the empirical basis of that
choice.

Empirical comparison of CVXPY vs L-BFGS-B on the 6 budget-binding
`PROD_CASES`, swept over `w ∈ {0.25, 0.5, 0.75, 0.9}` (24 combinations),
generated 2026-05-10:

| Metric                                       | Worst-case across 24 (case × w) |
|----------------------------------------------|---------------------------------|
| CVX vs LBFGS rel diff on `expected_recruits` | ~4.4e-4                         |
| budget constraint violation (CVXPY)          | ≤ 2e-5 relative                 |
| budget constraint violation (L-BFGS-B)       | ≤ 1e-5 relative                 |

**L-BFGS-B drift is ~4e-4 on the allocation** — same order as the pure-variance
case, set by the same `ftol=1e-14, gtol=1e-10, eps=1e-12` floor and the
degenerate `s = S / S.sum()` parameterization. Both solvers agree on the
objective value to within solver tolerance; the difference is purely in the
allocation precision.

**Cutover impact.** Flipping `optimizer_version` from `lbfgs` to `cvxpy` on a
blended study moves individual stratum counts by up to ~0.04%, with no change
in the objective value to several digits. Same answer, tighter solution.

## Runtime Performance — Pure Variance

Median of 50 runs per case on the 6 budget-binding `PROD_CASES`, measured
2026-05-10. Microseconds per call, `efficiency_weight = 1`.

| case   | H | closed-form | CVXPY    | L-BFGS-B | CF speedup vs LBFGS |
|--------|---|-------------|----------|----------|---------------------|
| case_1 | 4 |       52 μs | 13500 μs |  3070 μs |                 59× |
| case_2 | 2 |      160 μs | 11800 μs |  1130 μs |                  7× |
| case_3 | 6 |       77 μs | 23600 μs | 11700 μs |                153× |
| case_4 | 6 |       48 μs | 25200 μs | 14700 μs |                305× |
| case_5 | 2 |      165 μs | 11200 μs |  1260 μs |                  8× |
| case_6 | 2 |       49 μs | 10900 μs |  2280 μs |                 46× |

The pure-variance active-set sweep is a handful of numpy operations with no
iteration. CVXPY pays its framework + interior-point setup cost (~10–25 ms);
L-BFGS-B pays its line-search cost (~1–15 ms).

## Decision Record — Why no closed-form blended path?

We implemented a nested-bisection closed-form for the blended case
(`_blended_bisection_budget`) per `paper/variance_extension.tex` §9 Case B,
then removed it. The empirical case for the decision:

**Runtime (blended, measured 2026-05-10):**

| case   | H | closed-form (bisection) | CVXPY    | L-BFGS-B |
|--------|---|-------------------------|----------|----------|
| case_1 | 4 |                86000 μs | 16100 μs | 13200 μs |
| case_2 | 2 |                86000 μs | 15600 μs |  1300 μs |
| case_3 | 6 |               116000 μs | 15900 μs | 11900 μs |
| case_4 | 6 |                91000 μs | 15700 μs | 13300 μs |
| case_5 | 2 |                78000 μs | 15200 μs |  1100 μs |
| case_6 | 2 |               101000 μs | 30500 μs |  6900 μs |

The bisection ran up to ~200 outer × ~200 inner iterations, each evaluating an
O(H) numpy expression in a Python loop — ~40K Python-level numpy calls
dominated.

**Properties:**

- **Not analytic.** Nested bisection has its own convergence tolerance and
  bracket-expansion logic. The "exact" property that justifies closed-form for
  `w = 1` does not carry over to `w < 1`.
- **5–10× slower than CVXPY.** Each blended call took ~80–120 ms vs CVXPY's
  ~15 ms.
- **~150 lines of subtle code.** Active-set pinning, slack-shrinking,
  dual-bracket logic — each a small bug surface.
- **CVXPY is already loaded** for the oracle tests and the `optimizer_version =
  "cvxpy"` flag, so "no extra dependency" is moot for the blended path.

**Decision (2026-05-10):** retire `_blended_bisection_budget`.
`proportional_opt_closed_form` is pure-variance only and raises
`NotImplementedError` for `w < 1`. The blended path is served by
`proportional_opt_cvxpy` (primary) and the legacy `proportional_opt`. The
pure-variance closed-form retains its advantages — 200×+ faster than CVXPY,
analytic exactness, inspectable allocation rule — where they are real.

If a future objective extension makes CVXPY too slow or restrictive, the math
note's Case B derivation and its implementation are recoverable from
git history (commit `5c7e32e` introduced the bisection; the commit removing
it is the predecessor of the current head).

Operationally the choice doesn't matter for runtime: `adopt` optimizes once
per study per cycle (hours apart), so milliseconds vs microseconds is
imperceptible. The decision is about *code* clarity, not runtime.

## What This Is Not a Replacement For

- The contract is in the tests (`test_budget_cvxpy_oracle.py`,
  `test_budget_blended.py`, `test_objective_no_worse_than_lbfgs` in
  `test_budget_prod_regimes.py`). If you change the optimizer, the tests catch
  regressions; this doc just records what "passing" looked like on 2026-05-10.
- Solver-config rationale belongs in code comments first (and is there); this
  doc collects it for the next person evaluating whether to retune.
- Future objective extensions (correlated outcomes, regularization) will break
  the closed-form path. At that point CVX becomes the primary, the precision
  hierarchy collapses, and this doc needs revisiting.

## Reproducing the Table

From the `adopt/` directory:

```bash
poetry run python - <<'EOF'
import numpy as np
from adopt.budget import proportional_opt_closed_form, proportional_opt_cvxpy, proportional_opt
from adopt.test_budget_prod_regimes import PROD_CASES

for c in PROD_CASES:
    kw = dict(goal=np.array(c.goal), tot=np.array(c.tot, dtype=float),
              price=np.array(c.price), budget=c.budget,
              max_recruits=c.max_recruits, efficiency_weight=c.efficiency_weight)
    cf = proportional_opt_closed_form(**kw)
    cv = proportional_opt_cvxpy(**kw)
    lb = proportional_opt(**kw, tol=0.01)
    goal, n0 = np.array(c.goal), 1
    rel_cv = np.max(np.abs(cf.expected_recruits - cv.expected_recruits)
                    / np.maximum(np.abs(cf.expected_recruits), 1e-9))
    rel_lb = np.max(np.abs(cf.expected_recruits - lb.expected_recruits)
                    / np.maximum(np.abs(cf.expected_recruits), 1e-9))
    obj = lambda r: float(np.sum(goal**2 / (r + n0)))
    print(f"{c.name:30s} CF/CVX={rel_cv:.2e}  CF/LB={rel_lb:.2e}  "
          f"obj_CF={obj(cf.expected_recruits):.6e}")
EOF
```

Blended sweep — call `proportional_opt_cvxpy` and `proportional_opt` (not
`proportional_opt_closed_form`, which raises on `w < 1`) in a loop over
`w in [0.25, 0.5, 0.75, 0.9]` and compute the blended objective
`w · sum(goal² / m) + (1-w) / sum(m)`.
