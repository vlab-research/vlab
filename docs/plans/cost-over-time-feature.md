# Plan: Replace Deviation Charts with Cost Charts

## Overview

Replace the unused deviation metrics with cost metrics in the StudyPage:

| Current (Remove) | New (Add) |
|------------------|-----------|
| Current Avg. Deviation | **Total Spent** → Cumulative Spend Over Time chart |
| Expected Avg. Deviation | **Avg Cost Per Participant** → Marginal Cost Over Time chart |

Keep: Current Participants, Expected Participants (unchanged)

---

## Architecture

The UI uses clickable stat cards (`StudyProgressStats`) that control which chart (`StudyProgressChart`) is displayed. We'll extend this pattern to support cost charts.

**Data flow:**
1. Backend computes cost-over-time report during optimization (like respondents-over-time)
2. New endpoint serves the data
3. Frontend fetches and displays via existing stat/chart pattern

---

## Backend Implementation

### Step 1: Query Spend by Date

**File**: `adopt/adopt/recruitment_data.py`

Add function after `calculate_stat_sql()` (~line 370):

```python
def get_spend_by_date(
    db_conf: DBConf,
    study_id: str,
) -> list[dict]:
    """
    Get daily spend aggregated across all campaigns/strata.
    Returns: [{"date": date, "spend": float}, ...]
    """
    q = """
    WITH combined AS (
        SELECT period_start, data
        FROM recruitment_data_events
        WHERE study_id = %s AND temp = FALSE
        UNION
        (SELECT period_start, data
         FROM recruitment_data_events
         WHERE study_id = %s AND temp = TRUE
         ORDER BY period_end DESC
         LIMIT 1)
    )
    SELECT
        DATE(period_start) as day,
        SUM(CAST(metrics->>'spend' AS FLOAT)) as daily_spend
    FROM combined
    CROSS JOIN LATERAL jsonb_each(data) AS campaign(campaign_id, campaign_data)
    CROSS JOIN LATERAL jsonb_each(campaign_data) AS stratum(stratum_id, metrics)
    GROUP BY DATE(period_start)
    ORDER BY day ASC
    """
    results = list(query(db_conf, q, (study_id, study_id)))
    return [{"date": row[0], "spend": row[1] or 0.0} for row in results]
```

### Step 2: Cost Calculation Module

**File**: `adopt/adopt/cost_over_time.py` (new file)

```python
"""Cost over time calculations for recruitment analytics."""

from datetime import datetime, date
from typing import Optional
import pandas as pd


def count_new_respondents_by_day(
    user_start_times: pd.DataFrame,
) -> dict[date, int]:
    """
    Count new respondents per day from user start times.

    Args:
        user_start_times: DataFrame with columns [user_id, stratum_id, start_time]

    Returns:
        Dict mapping date -> count of new respondents that day
    """
    if user_start_times.empty:
        return {}

    df = user_start_times.copy()
    df['date'] = df['start_time'].dt.date

    # Count unique users per day (user can only be "new" once)
    daily_counts = df.groupby('date')['user_id'].nunique()
    return daily_counts.to_dict()


def calculate_cost_over_time(
    spend_by_day: list[dict],
    new_respondents_by_day: dict[date, int],
    incentive_per_respondent: float,
) -> list[dict]:
    """
    Calculate cumulative spend and marginal cost per respondent for each day.

    Returns list of:
    {
        "datetime": int (ms timestamp),
        "cumulativeSpend": float,
        "cumulativeRespondents": int,
        "marginalCost": float | None,  # None if no new respondents that day
        "newRespondents": int,
        "dailySpend": float,
    }
    """
    # Get all dates from both sources
    spend_dates = {d["date"] for d in spend_by_day}
    respondent_dates = set(new_respondents_by_day.keys())
    all_dates = sorted(spend_dates | respondent_dates)

    if not all_dates:
        return []

    # Build lookup for spend
    spend_lookup = {d["date"]: d["spend"] for d in spend_by_day}

    result = []
    cumulative_spend = 0.0
    cumulative_respondents = 0

    for day in all_dates:
        daily_spend = spend_lookup.get(day, 0.0)
        new_respondents = new_respondents_by_day.get(day, 0)

        # Update cumulative values
        cumulative_spend += daily_spend
        cumulative_respondents += new_respondents

        # Calculate daily incentive cost
        daily_incentive = new_respondents * incentive_per_respondent
        daily_total = daily_spend + daily_incentive

        # Marginal cost (None if no new respondents to avoid division by zero)
        marginal_cost = None
        if new_respondents > 0:
            marginal_cost = daily_total / new_respondents

        # Convert date to millisecond timestamp
        dt = datetime.combine(day, datetime.min.time())
        timestamp_ms = int(dt.timestamp() * 1000)

        result.append({
            "datetime": timestamp_ms,
            "cumulativeSpend": cumulative_spend,
            "cumulativeRespondents": cumulative_respondents,
            "marginalCost": marginal_cost,
            "newRespondents": new_respondents,
            "dailySpend": daily_spend,
        })

    return result
```

### Step 3: Report Computation

**File**: `adopt/adopt/malaria.py`

Add function (after `calculate_respondents_over_time_report`):

```python
def calculate_cost_over_time_report(
    df: Optional[pd.DataFrame],
    strata: list[StratumConf],
    db_conf: DBConf,
    study_id: str,
    incentive_per_respondent: float,
) -> list[dict]:
    """Calculate cost over time data for storage."""
    from .budget import prep_df_for_budget
    from .segments_progress import get_user_start_times
    from .cost_over_time import count_new_respondents_by_day, calculate_cost_over_time
    from .recruitment_data import get_spend_by_date

    if df is None or df.empty:
        return []

    # Get user start times (same logic as respondents_over_time)
    filtered_df = prep_df_for_budget(df, strata)
    if filtered_df.empty:
        return []

    user_start_times = get_user_start_times(filtered_df)
    new_respondents_by_day = count_new_respondents_by_day(user_start_times)

    # Get spend by day from database
    spend_by_day = get_spend_by_date(db_conf, study_id)

    return calculate_cost_over_time(
        spend_by_day, new_respondents_by_day, incentive_per_respondent
    )
```

In `update_ads_for_campaign()`, after line ~103 (respondents report), add:

```python
        # Generate and store cost over time report
        try:
            from .campaign_queries import create_cost_over_time_report
            cost_report = calculate_cost_over_time_report(
                df, study.strata, db_conf, study.id,
                study.recruitment.incentive_per_respondent
            )
            create_cost_over_time_report(study.id, cost_report, db_conf)
        except BaseException as e:
            logging.error(f"Error creating cost over time report: {e}")
```

### Step 4: Report Storage

**File**: `adopt/adopt/campaign_queries.py`

Add after `get_latest_respondents_over_time_report()`:

```python
def create_cost_over_time_report(study_id: str, report_data: list, cnf: DBConf):
    """Store cost over time report."""
    return create_adopt_report(study_id, "cost_over_time", report_data, cnf)


def get_latest_cost_over_time_report(study_id: str, cnf: DBConf) -> list | None:
    """Get the latest cost over time report."""
    q = """
    SELECT details
    FROM adopt_reports
    WHERE study_id = %s AND report_type = 'cost_over_time'
    ORDER BY created DESC
    LIMIT 1
    """
    result = list(query(cnf, q, (study_id,)))
    return result[0][0] if result else None
```

### Step 5: API Endpoint

**File**: `adopt/adopt/server/server.py`

Add models (near other response models):

```python
class CostTimePointData(BaseModel):
    datetime: int
    cumulativeSpend: float
    cumulativeRespondents: int
    marginalCost: Optional[float]
    newRespondents: int
    dailySpend: float


class CostOverTimeResponse(BaseModel):
    data: list[CostTimePointData]
```

Add endpoint (after `get_segments_progress`):

```python
@app.get(
    "/{org_id}/studies/{slug}/cost-over-time",
    response_model=CostOverTimeResponse,
)
async def get_cost_over_time(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> CostOverTimeResponse:
    """Get cost metrics over time (cumulative spend and marginal cost)."""
    db_cnf = get_db_conf()
    study_id = get_study_id(user.id, org_id, slug, db_cnf)

    report = get_latest_cost_over_time_report(study_id, db_cnf)

    if not report:
        return CostOverTimeResponse(data=[])

    return CostOverTimeResponse(
        data=[CostTimePointData(**point) for point in report]
    )
```

---

## Frontend Implementation

### Step 6: Types

**File**: `dashboard/src/types/study.ts`

Add after `RespondentsOverTimeApiResponse`:

```typescript
// Cost over time types
export interface CostTimePointData {
  datetime: number;
  cumulativeSpend: number;
  cumulativeRespondents: number;
  marginalCost: number | null;
  newRespondents: number;
  dailySpend: number;
}

export interface CostOverTimeApiResponse extends ApiResponse<CostTimePointData[]> {}
```

### Step 7: API Helper

**File**: `dashboard/src/helpers/api.ts`

Add fetch function and export:

```typescript
const fetchCostOverTime = ({
  slug,
  accessToken,
}: {
  slug: string;
  accessToken: string;
}) =>
  apiRequest<CostOverTimeApiResponse>(
    `/${orgPrefix()}/studies/${slug}/cost-over-time`,
    {
      accessToken,
      baseURL: process.env.REACT_APP_CONF_SERVER_URL,
    }
  );
```

Add to `useAuthenticatedApi` return object.

### Step 8: Hook Updates

**File**: `dashboard/src/pages/StudyPage/hooks/useStudy.tsx`

Add query for cost over time:

```typescript
const useCostOverTimeQuery = (slug: string) => {
  const { fetchCostOverTime } = useAuthenticatedApi();
  return useQuery(
    ['study', slug, 'cost-over-time'],
    () => fetchCostOverTime({ slug }),
    {
      refetchInterval: 5 * 60 * 1000, // 5 minutes
    }
  );
};
```

Update `useStudy` to:
1. Call `useCostOverTimeQuery`
2. Compute `totalSpent` and `avgCostPerParticipant` from the data
3. Return `costOverTime` data for the chart

Add to `UseStudyReturn` interface:
```typescript
costOverTime: CostTimePointData[];
costOverTimeIsLoading: boolean;
totalSpent: number;
avgCostPerParticipant: number;
```

### Step 9: Update StudyProgressStats

**File**: `dashboard/src/pages/StudyPage/components/StudyProgressStats.tsx`

Replace deviation stats with cost stats:

```tsx
import { formatCurrency } from '../../../helpers/numbers';

// Update props interface to include cost data
interface StudyProgressStatsProps {
  currentProgress?: StudyProgressResource;
  totalSpent: number;
  avgCostPerParticipant: number;
  selectedStat: string;
  onSelectStat: (selectedStat: string) => void;
}

// Update stats array:
stats={[
  {
    name: 'Current Participants',
    stat: formatNumber(currentProgress.currentParticipants),
  },
  {
    name: 'Expected Participants',
    stat: formatNumber(currentProgress.expectedParticipants),
  },
  {
    name: 'Total Spent',
    stat: formatCurrency(totalSpent),
  },
  {
    name: 'Avg Cost Per Participant',
    stat: avgCostPerParticipant > 0
      ? formatCurrency(avgCostPerParticipant)
      : '-',
  },
]}
```

Update skeleton to match new stat names.

### Step 10: Update StudyProgressChart

**File**: `dashboard/src/pages/StudyPage/components/StudyProgressChart.tsx`

Add cost data props and handle cost chart rendering:

```tsx
import { StudyProgressResource, CostTimePointData } from '../../../types/study';

interface StudyProgressChartProps {
  label: string;
  data?: StudyProgressResource[];
  costData?: CostTimePointData[];
}

const StudyProgressChart = ({ label, data, costData }: StudyProgressChartProps) => {
  // ... skeleton handling ...

  // Handle cost charts
  if (label === 'Total Spent' && costData) {
    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChart
          testId="cumulative-spend-chart"
          label={label}
          data={costData.map(point => ({
            primary: new Date(point.datetime),
            secondary: point.cumulativeSpend,
          }))}
        />
      </div>
    );
  }

  if (label === 'Avg Cost Per Participant' && costData) {
    // Filter out days with no new respondents
    const chartData = costData
      .filter(point => point.marginalCost !== null)
      .map(point => ({
        primary: new Date(point.datetime),
        secondary: point.marginalCost!,
      }));

    return (
      <div className="pt-5 sm:pt-6 lg:pt-10">
        <SingleAreaChart
          testId="marginal-cost-chart"
          label={label}
          data={chartData}
        />
      </div>
    );
  }

  // Existing participant charts
  return (
    <div className="pt-5 sm:pt-6 lg:pt-10">
      <SingleAreaChart
        testId="study-progress-chart"
        label={label}
        data={data?.map(resource => ({
          primary: new Date(resource.datetime),
          secondary:
            {
              'Current Participants': resource.currentParticipants,
              'Expected Participants': resource.expectedParticipants,
            }[label] || resource.currentParticipants,
        }))}
      />
    </div>
  );
};
```

### Step 11: Update StudyPage

**File**: `dashboard/src/pages/StudyPage/StudyPage.tsx`

Pass cost data to components:

```tsx
<StudyProgressStats
  currentProgress={study.isLoading ? undefined : study.currentProgress}
  totalSpent={study.totalSpent}
  avgCostPerParticipant={study.avgCostPerParticipant}
  selectedStat={selectedStat}
  onSelectStat={newSelectedStat => {
    setSelectedState(newSelectedStat);
  }}
/>

<StudyProgressChart
  label={selectedStat}
  data={study.isLoading ? undefined : study.progressOverTime}
  costData={study.costOverTimeIsLoading ? undefined : study.costOverTime}
/>
```

---

## Files to Modify Summary

| File | Change |
|------|--------|
| `adopt/adopt/recruitment_data.py` | Add `get_spend_by_date()` |
| `adopt/adopt/cost_over_time.py` | **New file** - calculation logic |
| `adopt/adopt/malaria.py` | Add `calculate_cost_over_time_report()` and call it |
| `adopt/adopt/campaign_queries.py` | Add storage/retrieval functions |
| `adopt/adopt/server/server.py` | Add endpoint and models |
| `dashboard/src/types/study.ts` | Add cost types |
| `dashboard/src/helpers/api.ts` | Add fetch function |
| `dashboard/.../hooks/useStudy.tsx` | Add cost query and computed values |
| `dashboard/.../StudyProgressStats.tsx` | Replace deviation with cost stats |
| `dashboard/.../StudyProgressChart.tsx` | Handle cost chart rendering |
| `dashboard/.../StudyPage.tsx` | Pass cost data to components |

---

## Verification

1. **Backend**:
   - Run existing tests: `cd adopt && pytest`
   - Trigger optimization for a study with spend data
   - Check `adopt_reports` table for `cost_over_time` report
   - Call `GET /cost-over-time` endpoint

2. **Frontend**:
   - Run: `cd dashboard && npm test`
   - View StudyPage - should show 4 stat cards (2 participant, 2 cost)
   - Click "Total Spent" - should show cumulative spend chart
   - Click "Avg Cost Per Participant" - should show marginal cost chart

3. **Integration**:
   - Verify charts render with real data
   - Verify stat values match chart endpoints
