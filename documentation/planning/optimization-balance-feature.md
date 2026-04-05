# Plan: Variance-Efficiency Slider for Budget Optimization

## Problem Statement

The current budget optimization algorithm prioritizes **variance reduction** - it allocates budget to strata that are furthest from their quotas, regardless of cost. This means an expensive stratum ($50/person) can receive 100% of the budget while a cheap stratum ($5/person) gets nothing.

**User Goal**: Prioritize total N (sample size) over variance reduction when desired. Allow control over the tradeoff between:
- **Variance optimization** (current): Hit quotas proportionally, regardless of cost
- **Cost efficiency** (new): Maximize total respondents for the budget

## Solution: Efficiency Weight Parameter

Add an `efficiency_weight` parameter (0.0 to 1.0) that blends between the two objectives:
- `efficiency_weight = 1.0`: Pure variance optimization (current behavior)
- `efficiency_weight = 0.0`: Pure cost efficiency (maximize total N)
- `efficiency_weight = 0.5`: Balanced approach

### Mathematical Design

**Key Insight**: "Weighted" vs "Unweighted" variance
- **Weighted** (current): Optimizes distribution across strata according to goals
- **Unweighted**: Ignores strata entirely, just maximizes total N

Current loss function (weighted):
```python
variance_loss = Σ (goal² / projection_i)  # Per-stratum, weighted by goal²
```

New unweighted loss (maximizes total N):
```python
efficiency_loss = 1 / Σ(projection_i)  # Minimize reciprocal = maximize total
```

Both have units of **1/people**. To normalize magnitudes (variance_loss is ~P times larger):

```python
P = number of strata

# Normalized blend
loss = ew × variance_loss + (1 - ew) × P × efficiency_loss
     = ew × Σ(goal²/projection_i) + (1 - ew) × P / Σ(projection_i)
```

**Behavior**:
- `ew=1.0`: Pure variance optimization → projections ∝ goals (current behavior)
- `ew=0.0`: Pure total N maximization → ALL budget to cheapest stratum
- `ew=0.5`: Balanced blend

**Example Impact** (from `test_proportional_budget_prioritizes_underperforming_even_at_high_cost`):
- Strata: bar ($5/person), baz ($20/person), foo ($50/person)
- Current (ew=1.0): foo gets $100 (variance optimal, but only ~2 recruits)
- With ew=0.0: bar gets $100 (total N optimal, ~20 recruits)

---

## Implementation Plan

### Phase 1: Backend Core (adopt/adopt/budget.py)

**File**: `adopt/adopt/budget.py`

1. **Modify `budget_opt()` function** (line 122-128):
   ```python
   def budget_opt(S, goal, tot, price, budget, efficiency_weight=1.0):
       C = 1 / price
       s = S / S.sum()
       new_spend = s * budget
       projection = C * new_spend + tot + 1

       # Weighted variance loss (current)
       variance_loss = np.sum(goal**2 / projection)

       # Unweighted efficiency loss (maximize total N)
       P = len(goal)
       efficiency_loss = P / np.sum(projection)

       # Blended loss
       loss = efficiency_weight * variance_loss + (1 - efficiency_weight) * efficiency_loss
       return loss * tot.sum()
   ```

2. **Modify `recruits_opt()` function** (line 131-136):
   - Add parallel `efficiency_weight` support with same blended loss structure

3. **Modify `proportional_opt()` function** (line 139-188):
   - Add `efficiency_weight` parameter
   - Pass through to `budget_opt` and `recruits_opt` in the `opt()` inner function

4. **Modify `proportional_budget()` function** (line 191-211):
   - Add `efficiency_weight` parameter (default 1.0)
   - Pass through to `proportional_opt()`

5. **Modify `get_budget_lookup()` function** (line 262-316):
   - Add `efficiency_weight` parameter (default 1.0)
   - Pass through to `proportional_budget()`

6. **Modify `get_budget_lookup_with_db()` function** (line 414-463):
   - Add `efficiency_weight` parameter (default 1.0)
   - Pass through to `get_budget_lookup()`

### Phase 2: Configuration Classes (adopt/adopt/study_conf.py)

**File**: `adopt/adopt/study_conf.py`

1. **Modify `SimpleRecruitment` class** (line 143-188):
   ```python
   efficiency_weight: float = 1.0  # 1.0 = variance focus, 0.0 = cost focus
   ```

2. **Modify `PipelineRecruitmentExperiment` class** (line 206-304):
   - Add same `efficiency_weight` field

3. **Modify `DestinationRecruitmentExperiment` class** (line 307-356):
   - Add same `efficiency_weight` field

### Phase 3: Integration (adopt/adopt/malaria.py)

**File**: `adopt/adopt/malaria.py`

1. **Modify `update_ads_for_campaign()`** or related functions:
   - Extract `efficiency_weight` from recruitment config
   - Pass to `get_budget_lookup_with_db()`

### Phase 4: Dashboard Types (dashboard/src/types/conf.ts)

**File**: `dashboard/src/types/conf.ts`

1. **Modify `RecruitmentSimple` interface** (line 15-26):
   ```typescript
   efficiency_weight?: number;  // 0.0-1.0, default 1.0
   ```

2. **Modify `RecruitmentDestination` interface** (line 28-40):
   - Add same field

3. **Modify `PipelineExperiment` interface** (line 42-56):
   - Add same field

### Phase 5: Dashboard UI (dashboard/src/pages/StudyConfPage/forms/recruitment/)

**File**: `dashboard/src/pages/StudyConfPage/forms/recruitment/Simple.tsx`

1. **Add slider/input field**:
   - Label: **"Optimization Balance"**
   - Range: 0 to 1 (displayed as 0% to 100%)
   - Left endpoint (0%): "Maximize Total N" (cost efficient)
   - Right endpoint (100%): "Optimize Variance" (quota balance)
   - Default: 1.0 / 100% (current behavior)
   - Help text: "Controls tradeoff between maximizing total respondents vs. hitting quota targets proportionally"

2. **Add validation** in `validateInput()` function

3. **Update initial state** in `Recruitment.tsx` (line 44-88):
   - Add `efficiency_weight: 1` to all initial states

**Files**: `Destination.tsx`, `PipelineExperiment.tsx`
- Add same slider component to each form

### Phase 6: Tests (adopt/adopt/test_budget.py)

**File**: `adopt/adopt/test_budget.py`

Add new test cases:

1. `test_proportional_budget_with_efficiency_weight_zero_allocates_all_to_cheapest()`:
   ```python
   def test_proportional_budget_with_efficiency_weight_zero_allocates_all_to_cheapest():
       """With ew=0, ALL budget goes to cheapest stratum to maximize total N."""
       spend = {"bar": 100.0, "baz": 100.0, "foo": 100.0}
       tot = {"bar": 5, "baz": 5, "foo": 5}
       price = {"bar": 5.0, "baz": 20.0, "foo": 50.0}  # bar is cheapest
       goal = {"foo": 1/3, "bar": 1/3, "baz": 1/3}
       budget, _ = proportional_budget(goal, spend, tot, price, 100, efficiency_weight=0.0)
       assert budget["bar"] == 100  # ALL to cheapest
       assert budget["baz"] == 0
       assert budget["foo"] == 0
   ```

2. `test_proportional_budget_with_efficiency_weight_one_matches_current_behavior()`:
   - Use existing test case data, verify results unchanged with ew=1.0

3. `test_proportional_budget_with_efficiency_weight_half_balances()`:
   - Verify intermediate allocation between variance and total N

4. `test_efficiency_weight_default_preserves_backward_compatibility()`:
   - Run all existing tests without specifying efficiency_weight
   - Verify same results as before

---

## Files to Modify

| File | Changes |
|------|---------|
| `adopt/adopt/budget.py` | Core optimization logic with efficiency_weight |
| `adopt/adopt/study_conf.py` | Add efficiency_weight to recruitment configs |
| `adopt/adopt/malaria.py` | Thread efficiency_weight through integration |
| `adopt/adopt/test_budget.py` | New test cases |
| `dashboard/src/types/conf.ts` | TypeScript interface updates |
| `dashboard/src/pages/StudyConfPage/forms/recruitment/Simple.tsx` | Add slider UI |
| `dashboard/src/pages/StudyConfPage/forms/recruitment/Destination.tsx` | Add slider UI |
| `dashboard/src/pages/StudyConfPage/forms/recruitment/PipelineExperiment.tsx` | Add slider UI |
| `dashboard/src/pages/StudyConfPage/forms/recruitment/Recruitment.tsx` | Update initial states |

---

## Verification Plan

1. **Unit Tests**:
   ```bash
   cd adopt && pytest adopt/test_budget.py -v -k "efficiency"
   ```

2. **Backward Compatibility**:
   - Run all existing budget tests to ensure they pass with default efficiency_weight=1.0
   ```bash
   cd adopt && pytest adopt/test_budget.py -v
   ```

3. **Manual Testing**:
   - Create a test study with strata at varying prices
   - Set efficiency_weight to different values (0, 0.5, 1)
   - Verify budget allocation changes as expected

4. **UI Testing**:
   - Verify slider appears in recruitment form
   - Verify value persists after save
   - Verify value is passed correctly to backend

---

## Design Decisions

1. **Why a continuous slider vs. binary toggle?**
   - Continuous control allows fine-tuning the balance
   - Users can find their preferred tradeoff point
   - More flexible than "on/off" price caps

2. **Why study-level vs. per-stratum?**
   - Simpler mental model for users
   - Per-stratum would require N additional inputs
   - Can add per-stratum override later if needed

3. **Why default to 1.0 (variance)?**
   - Backward compatibility
   - Current behavior is well-tested
   - Users must opt-in to new behavior

4. **UI placement - Recruitment form vs. General form?**
   - Recruitment form: grouped with other budget settings
   - Makes conceptual sense alongside budget, min_budget, etc.
