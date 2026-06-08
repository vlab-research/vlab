# Soak Deployment: Retire L-BFGS-B, Ship Closed-Form + CVXPY

## Summary

Steps 2 + 3 + 4 + 4a + 4b + Phase 1 shadow soak + Phase 2 cutover are complete. We have:

- `proportional_opt_closed_form` — analytic active-set, primary path for
  `efficiency_weight == 1`. Microsecond runtime. Verified against L-BFGS-B on
  prod data within 0.033%.
- `proportional_opt_cvxpy` — CVXPY+ECOS / CLARABEL fallback, handles all
  `efficiency_weight ∈ [0, 1]`. Primary path for blended (`w < 1`). Verified
  against L-BFGS-B on prod data within 4.4e-4.
- `proportional_opt` (L-BFGS-B) — legacy. Has known correctness issues we no
  longer want to ship: returns negative recruits on synthetic edge cases,
  degenerate normalization parameterization, KKT non-convergence on large H,
  noise floor ~1e-4 on the allocation.
- 189 tests including KKT-as-oracle and three-way cross-checks on
  `PROD_CASES`.

This plan ships the new optimizer path to production, retires L-BFGS-B as the
primary path, but **keeps it available as a per-study fallback** for one
release cycle. Two phases: shadow mode for a few days to confirm allocations
match offline expectations, then cut over. Few prod studies + close human
oversight means we **fail loud, not safe**: no defensive try/except hiding
solver errors — if cvxpy throws, it throws, we see it in the logs, we fix
the underlying bug.

## Why now (and not after Step 5)

Step 5 changes the *math* (heterogeneous σ̂² instead of σ = 1). If we deploy
both at once and anything breaks in production, we can't tell whether it's the
new optimizer or the new variance model. Doing the optimizer cutover first
isolates the risk.

## Pre-flight checklist (block deployment until all green)

### 1. Runtime dependencies in the deploy image

CVXPY is now a *runtime* dep, not just dev/test. Confirm:

- `cvxpy`, `ecos`, `clarabel` are in `adopt/pyproject.toml` under
  `[tool.poetry.dependencies]` (not `[tool.poetry.group.dev.dependencies]`).
- `poetry.lock` reflects the same.
- `adopt/Dockerfile` (or whatever builds the deploy image) installs the runtime
  group only — i.e., `poetry install --without dev` or equivalent should still
  install cvxpy/ecos/clarabel.
- Local sanity: build the deploy image, `docker run … python -c "import cvxpy,
  ecos, clarabel; print('ok')"`.

Fail-fast: if cvxpy isn't in the deploy image, the first study with
`efficiency_weight < 1` will throw `ModuleNotFoundError` at optimization time
— exactly the moment we don't want surprises.

### 2. Add `optimizer_version` to `StudyConf.recruitment`

Per-study override so individual studies can be reverted without redeploying.
Step 7's full feature flag pattern; we're landing the field early.

**File:** `adopt/adopt/study_conf.py` — add field to `RecruitmentConf`:

```python
optimizer_version: Literal["closed_form", "lbfgs"] = "closed_form"
```

Default to `closed_form` because that's what we're promoting to primary. Any
study can override by writing a new `StudyConf` row with
`optimizer_version="lbfgs"` if we need to revert just that one.

### 3. Wire the dispatch into `proportional_budget`

`proportional_budget` already accepts an `optimizer` parameter. The dispatch
lives at the caller — `get_budget_lookup` — which reads
`recruitment.optimizer_version`, `recruitment.efficiency_weight`, and picks the
right optimizer:

```python
def _pick_optimizer(study_conf):
    version = study_conf.recruitment.optimizer_version  # "closed_form" or "lbfgs"
    w = study_conf.recruitment.efficiency_weight
    if version == "lbfgs":
        return proportional_opt
    # closed_form: closed form for w=1, cvxpy for w<1
    if w >= 1.0:
        return proportional_opt_closed_form
    return proportional_opt_cvxpy
```

Plumb through `get_budget_lookup` → `proportional_budget(..., optimizer=…)`.

### 4. Structured logging on every optimization call

Without per-call logs, "a few days of running" produces zero signal. Log every
optimization, including (at minimum):

- `study_id`
- `H` (number of strata)
- `efficiency_weight`
- `optimizer_version` (which path actually ran)
- `solver_status` (CVXPY's; or `"ok"` for closed-form/L-BFGS-B)
- `time_ms`
- `budget_residual` = `abs(sum(new_spend) - budget) / max(budget, 1)`
- `any_strata_pinned` (bool — only meaningful for closed-form/cvxpy)
- `max_abs_relative_diff_vs_lbfgs` (only set during shadow/parallel mode)

Use the existing logger; structured fields (JSON) preferred for queryability.
Log at INFO. Errors (CVXPY `SolverError`, infeasibility, unexpected exception)
log at ERROR with full inputs sanitized — these are the highest-signal events
during soak.

### 5. Acceptance criteria for ending soak

Define before deploying so the bar is unambiguous:

- **Hard fails (any one of these = revert):**
  - Any `solver_status` not in `{OPTIMAL, OPTIMAL_INACCURATE}` from CVXPY
  - Any allocation with `new_spend < 0` on any stratum (would be a real bug)
  - Any optimization call that throws
  - Latency p95 worse than the L-BFGS-B baseline by more than 2×
  - Allocations on a study moving >2× the expected baseline (currently
    ~4e-4 worst case from offline validation)
- **Soft signals (worth investigation, not auto-revert):**
  - Any `OPTIMAL_INACCURATE` from CVXPY (acceptable but worth knowing the
    rate; doc says CLARABEL inaccurate ~1e-7, fine)
  - Any study with `efficiency_weight < 1` whose allocation shifted >1e-3
    relative — probably benign but flag it
  - Latency degradation under 2× (unlikely on closed-form path, possible on
    blended where CVXPY can be slower than L-BFGS-B on H=2 cases)

## Phase 1 — Shadow Mode (24–48 hours)

**Goal:** observe the new path's behavior under prod load with **zero
behavioral risk**.

### What ships

- `optimizer_version` field on `StudyConf` (defaults `closed_form`)
- New optimizer dispatch wired in `get_budget_lookup`
- Structured logging on every optimization call
- **Dispatch override during shadow phase**: the `optimizer_version` field is
  *ignored* and `proportional_budget` always uses `proportional_opt`
  (L-BFGS-B). The new path is computed *unconditionally in parallel*, with no
  try/except — if cvxpy errors, we want the whole call to error so we see it.

```python
# In get_budget_lookup, before returning the L-BFGS-B result:
t0 = time.perf_counter()
shadow_result = _pick_new_optimizer(study_conf)(goal, tot, price, …)
shadow_time = time.perf_counter() - t0
max_rel_diff = compute_rel_diff(real_result, shadow_result)
log.info("optimizer_shadow", extra={…, "max_rel_diff": max_rel_diff,
         "shadow_time_ms": shadow_time})
```

No `try`. If the new path throws, the optimization cycle fails loudly, the
exception lands in error logs / paging, we look at it, we fix it. Few prod
users, close oversight — better to surface a bug immediately than swallow it
and discover it weeks later.

The real allocation served to Facebook is still L-BFGS-B's. The shadow run
gives us full per-call data.

### What to watch

- Any exceptions from the shadow path. Each one is a bug to investigate.
- Is `max_rel_diff` distributed where offline validation said it should be?
  Pure variance studies: ~1e-5. Blended: ~1e-4.
- Are there latency outliers on the shadow side?
- Any exception thrown specifically on `efficiency_weight < 1` studies
  → smoking gun for missing CVXPY dep in deploy image.

### Pass criterion for advancing to Phase 2

A few days of continuous prod data with:
- No unhandled exceptions from the shadow path
- All `max_rel_diff` values within offline validation expectations
- Latency distribution matches offline benchmarks

If a real bug shows up (exception, allocation drift outside spec), fix it in
the new path and reset the clock. The point of shadow mode is to surface
those bugs without affecting production allocations.

## Phase 2 — Cutover

**Goal:** the new path serves real allocations.

### What ships

Flip the dispatch: served allocation comes from the **new path**
(closed-form/CVXPY per `optimizer_version` + `efficiency_weight`). Remove the
shadow-mode parallel L-BFGS-B compute — shadow mode has already established
agreement on real prod inputs, so paying for L-BFGS-B every cycle adds no
information.

`proportional_opt` (L-BFGS-B) stays in `budget.py` as a fallback target for
any study that sets `optimizer_version="lbfgs"`. No callers do by default.

### Rollback

- **Per-study:** write a `StudyConf` row with `optimizer_version="lbfgs"`.
  Granular revert without redeploying.
- **Global:** revert the dispatch change in `get_budget_lookup`, or set an
  `ADOPT_OPTIMIZER_DEFAULT=lbfgs` env var that overrides the per-study
  default. Single flip.

Few prod users, close oversight — if a study admin reports something off,
revert that study, investigate, fix.

### Pass criterion for declaring done

One quiet release cycle with no rollbacks invoked. Then Step 7 can delete
L-BFGS-B and the `optimizer_version` field entirely.

## What this plan explicitly does NOT do

- **No Step 5 work.** Variance estimation stays at σ = 1 (legacy behavior).
  Step 5 is a separate deployment after this soak.
- **No closed-form blended.** That path was retired in Step 3; blended studies
  route through CVXPY. This plan doesn't change that.
- **No deletion of L-BFGS-B yet.** Kept as fallback. Removal is Step 7 after
  one quiet release cycle.
- **No changes to math.** Same allocation rule, just better solvers.

## File touch list

| File | Change |
|------|--------|
| `adopt/adopt/study_conf.py` | Add `optimizer_version: Literal["closed_form", "lbfgs"] = "closed_form"` to `RecruitmentConf` |
| `adopt/adopt/budget.py` | New `_pick_optimizer(study_conf)` helper; `get_budget_lookup` calls it and passes through `proportional_budget(..., optimizer=…)`. Add shadow-mode parallel call + logging. |
| `adopt/adopt/malaria.py` | (Verify) `update_ads_for_campaign` already reads `recruitment.optimizer_version` via the study config; no code change expected, just confirm. |
| `adopt/pyproject.toml` | (Verify) `cvxpy`, `ecos`, `clarabel` are runtime deps. |
| `adopt/Dockerfile` | (Verify) `poetry install` includes runtime deps incl. cvxpy. |
| `adopt/adopt/test_study_conf.py` | New test: `optimizer_version` default + override deserialization. |
| `adopt/adopt/test_budget.py` | New test: `_pick_optimizer` returns correct callable for each (version, w) combination. |
| `adopt/docs/optimizer.md` | Add a "Deployment" section noting the per-study override and the soak phases (so future readers know why the dispatch exists). |

No tests in `test_budget_closed_form.py`, `test_budget_cvxpy_oracle.py`,
`test_budget_blended.py`, or `test_budget_prod_regimes.py` need to change —
the optimizer functions themselves are unchanged.

## Open risks

- **CVXPY `OPTIMAL_INACCURATE` rate in the wild.** Offline we saw it primarily
  on H=6 cases under tight tolerances. If prod studies regularly hit it, that's
  a soft signal worth investigating but not a deploy blocker (CLARABEL
  inaccurate is still ~1e-7, well within any sensible allocation tolerance).
- **Latency on blended studies.** CVXPY for `w < 1` is comparable to L-BFGS-B
  (~10–15 ms vs ~1–15 ms) — no expected regression, but H=2 blended studies
  may be a few ms slower. Within noise for the once-per-cycle cadence.
- **Researcher confusion.** Studies that have been quietly running on L-BFGS-B
  will shift allocations by up to ~4e-4 relative. Worth a heads-up in whatever
  changelog/release-note channel exists.
- **Step 5 already in flight?** If anyone has work-in-progress on
  `estimate_variance` wiring (Layers 2/3), pause it during the soak. Don't
  ship two changes at once.

## Acceptance Criteria for the Whole Plan

- All pre-flight checks green.
- Phase 1: 24–48h shadow soak with no failures, max rel diff within offline
  validation expectations.
- Phase 2: 3–5 days as primary with no hard-fail events.
- Phase 3: parallel L-BFGS-B compute removed, no rollback invoked in 1
  release cycle.
- Step 5 begins only after Phase 2 completes successfully.
