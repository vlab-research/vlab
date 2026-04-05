# Budget Optimization Counterfactual Analysis

## Overview

Enhanced the budget optimization in `adopt/adopt/budget.py` to return counterfactual analysis alongside the optimal solution. This shows what would happen if the non-binding constraint wasn't present.

## Problem Statement

When optimizing budget allocation, we have two potential constraints:
1. **Budget constraint**: Maximum amount we can spend
2. **Respondents constraint**: Maximum number of respondents we want (max_sample_size)

Previously, the optimization would return the optimal allocation based on whichever constraint was binding, but we had no visibility into what the alternative scenario would look like.

**Use case**: When budget is binding, we know we'll spend all the budget and get fewer respondents than the limit. But how much *would* it cost to get all the respondents? This is often useful information for planning and stakeholder communication.

## Solution

When both constraints are provided, the optimization now computes both solutions and returns counterfactual data based on which constraint binds:

| Binding Constraint | Primary Result | Counterfactual |
|---|---|---|
| Budget | Spend all budget, get fewer respondents | Cost per stratum to fill sample |
| Respondents | Spend less, get max respondents | Respondents per stratum with full budget |

The binding constraint is implicit from which counterfactual field is populated in the report.

## Implementation

### New Data Structure

Added `OptimizationResult` dataclass to encapsulate optimization output:

```python
@dataclass
class OptimizationResult:
    new_spend: np.ndarray
    expected_recruits: np.ndarray
    counterfactual_spend: Optional[np.ndarray] = None  # when budget binds
    counterfactual_recruits: Optional[np.ndarray] = None  # when respondents bind
```

### Modified Functions

1. **`proportional_opt`**: Now returns `OptimizationResult` instead of tuple. Preserves both solutions when both constraints are provided and populates the appropriate counterfactual field.

2. **`proportional_budget`**: Updated return signature to include counterfactuals:
   ```python
   def proportional_budget(...) -> Tuple[Dict, Dict, Optional[Dict], Optional[Dict]]:
       # Returns: (new_spend, expected, counterfactual_spend, counterfactual_recruits)
   ```

3. **`get_budget_lookup`**: Includes counterfactuals in the report when present:
   - `counterfactual_spend_to_fill_sample` (when budget binds)
   - `counterfactual_participants_with_unlimited_budget` (when respondents bind)

### Logic Flow

```
proportional_opt():
    1. If budget provided: compute budget_solution
    2. If only budget constraint: return OptimizationResult(budget_solution, no counterfactuals)

    3. Compute recruit_solution for max_recruits
    4. If only respondents constraint: return OptimizationResult(recruit_solution, no counterfactuals)

    5. Both constraints present - determine binding:
       - If recruit_solution.spend > budget:
           Budget binds → return budget_solution with counterfactual_spend=recruit_solution.spend
       - Else:
           Respondents bind → return recruit_solution with counterfactual_recruits=budget_solution.recruits
```

## Report Output

The AdOptReport now conditionally includes counterfactual fields:

```python
# When budget binds:
{
    "stratum_id": {
        ...existing fields...
        "counterfactual_spend_to_fill_sample": 150.0  # cost to fill sample
    }
}

# When respondents bind:
{
    "stratum_id": {
        ...existing fields...
        "counterfactual_participants_with_unlimited_budget": 45.0  # recruits with full budget
    }
}
```

## Files Modified

- `adopt/adopt/budget.py` - Core implementation
- `adopt/adopt/test_budget.py` - Tests (39 total, 3 new for counterfactuals)

## Testing

Three new test cases cover the counterfactual behavior:

1. `test_proportional_budget_with_both_constraints_shows_counterfactual_spend` - Verifies counterfactual_spend is returned when budget binds
2. `test_proportional_budget_with_both_constraints_shows_counterfactual_recruits` - Verifies counterfactual_recruits is returned when respondents bind
3. `test_proportional_budget_no_counterfactual_when_only_max_recruits` - Verifies no counterfactual when only one constraint

Run tests:
```bash
cd adopt && poetry run pytest adopt/test_budget.py -v
```

## Backward Compatibility

- `get_budget_lookup` return signature unchanged: `Tuple[Optional[Budget], Optional[AdOptReport]]`
- Counterfactuals are embedded in the report, not changing the function signature
- Existing callers will work without modification; they simply have additional data available in the report
