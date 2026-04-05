# Respondents Over Time Implementation Plan

## Executive Summary

This document outlines the plan to change how "participants over time" data is calculated on the backend, while keeping the frontend UI unchanged. The new calculation will be based on actual participant start times and apply the same filtering logic used in the optimization process.

## Problem Statement

### Current Approach (What We Have)
- The dashboard fetches "segments progress" data from `adopt_reports` table
- These reports are snapshots generated during optimization runs
- Data includes: `currentParticipants`, `expectedParticipants`, `currentAverageDeviation`, `expectedAverageDeviation`
- The "Expected Participants" and "Deviation" metrics are calculated projections that aren't proving useful

### Issues with Current Approach
1. **Point-in-time snapshots**: Data is only recorded when optimization runs, not continuously
2. **No individual participant timestamps**: Cannot see when each participant actually started
3. **Metrics not useful**: Expected/deviation metrics are projections that don't reflect reality
4. **No filtering consistency**: Data isn't filtered the same way as optimization logic

### What We Want
- **Respondents over time** based on actual participant `timestamp` from `inference_data` table
- **Same filtering logic** as used in optimization (`prep_df_for_budget` → `only_target_users`)
- **Per-stratum breakdown** (data available, UI unchanged for now)
- **Keep UI visually identical** - same chart, same stat cards

---

## Architecture Overview

### Current Data Flow
```
adopt_reports table (snapshots from optimization runs)
    ↓
Go API: GET /studies/{slug}/segments-progress
    ↓
Dashboard: useStudy() hook → progressOverTime
    ↓
StudyProgressChart component (unchanged)
```

### Proposed Data Flow
```
inference_data table (actual participant responses)
    ↓
Adopt Server: GET /{org}/studies/{slug}/segments-progress  (NEW ENDPOINT, same path)
    ↓
Apply prep_df_for_budget filtering per stratum
    ↓
Group by time buckets (daily) + calculate cumulative counts
    ↓
Return data in same shape as current Go API response
    ↓
Dashboard: Change base URL to adopt server (MINOR CHANGE)
    ↓
StudyProgressChart component (NO CHANGE)
```

**Key Point**: The adopt server endpoint uses the same path (`/segments-progress`) and returns data in the same shape as the existing Go API, so only the base URL needs to change in the frontend.

---

## Technical Implementation

### Phase 1: New Endpoint in Adopt Server (Python)

#### Location
`adopt/adopt/server/server.py`

#### New Endpoint Specification

Uses the **same path** as the Go API (`/segments-progress`) so frontend only changes base URL.

```python
@app.get("/{org_id}/studies/{slug}/segments-progress")
async def get_segments_progress(
    org_id: str,
    slug: str,
    token: str = Depends(oauth2_scheme),
    db_cnf: str = Depends(get_db_cnf)
) -> SegmentsProgressResponse
```

#### Response Schema

Must match the existing Go API response shape that the frontend expects:

```python
class SegmentProgressResource(BaseModel):
    """Matches existing frontend expectations"""
    id: str                              # stratum_id
    name: str                            # stratum name
    datetime: int                        # Unix timestamp (seconds)
    currentParticipants: int             # THE KEY FIELD - now from inference_data
    expectedParticipants: int            # Can be 0 or calculated
    desiredParticipants: Optional[int]   # From stratum quota
    currentPercentage: float             # currentParticipants / total
    expectedPercentage: float            # Can be 0
    desiredPercentage: float             # From stratum quota
    percentageDeviationFromGoal: float   # |desired - current|
    currentBudget: float                 # Can be 0
    currentPricePerParticipant: float    # Can be 0

class SegmentsProgressResponse(BaseModel):
    """Response matches existing Go API shape"""
    data: list[dict]  # List of {segments: [...], datetime: int}
```

**Example response structure** (matches current Go API):
```json
{
  "data": [
    {
      "datetime": 1704067200,
      "segments": [
        {
          "id": "stratum-1",
          "name": "Stratum 1",
          "datetime": 1704067200,
          "currentParticipants": 45,
          "expectedParticipants": 0,
          "desiredParticipants": 100,
          "currentPercentage": 0.36,
          "expectedPercentage": 0,
          "desiredPercentage": 0.5,
          "percentageDeviationFromGoal": 0.14,
          "currentBudget": 0,
          "currentPricePerParticipant": 0
        }
      ]
    }
  ]
}
```

#### Implementation Logic

```python
async def get_segments_progress(org_id, slug, token, db_cnf):
    # 1. Auth & load study config
    user_id = await verify_tokens(token)
    study_id = await get_study_id(user_id, org_id, slug, db_cnf)
    study = await load_study_conf(study_id, db_cnf)

    # 2. Get full inference data for study duration
    inf_start = study.recruitment.start_date
    inf_end = study.recruitment.end_date or datetime.now(UTC)
    df = await get_inference_data(survey_user, study_id, db_cnf, inf_start, inf_end)

    # 3. Apply stratum filtering (THE KEY STEP - same as optimization)
    strata = study.strata
    filtered_df = prep_df_for_budget(df, strata)

    if filtered_df is None:
        return SegmentsProgressResponse(data=[])

    # 4. Get first timestamp per user (their "join" time)
    user_start_times = (
        filtered_df.groupby(['user_id', 'cluster'])
        .agg({'timestamp': 'min'})
        .reset_index()
        .rename(columns={'timestamp': 'start_time', 'cluster': 'stratum_id'})
    )

    # 5. Create daily time buckets
    buckets = create_time_buckets(inf_start, inf_end, "day")

    # 6. Build response in existing frontend format
    result = []
    cumulative_counts = {s.id: 0 for s in strata}
    total_desired = sum(s.quota for s in strata)

    for bucket_start, bucket_end in buckets:
        # Count new users in this bucket
        bucket_data = user_start_times[
            (user_start_times.start_time >= bucket_start) &
            (user_start_times.start_time < bucket_end)
        ]
        new_counts = bucket_data.groupby('stratum_id').user_id.nunique().to_dict()

        # Update cumulative counts
        for stratum_id, count in new_counts.items():
            cumulative_counts[stratum_id] += count

        # Build segment data for this timestamp
        total_current = sum(cumulative_counts.values())
        segments = []
        for stratum in strata:
            current = cumulative_counts.get(stratum.id, 0)
            desired = stratum.quota
            current_pct = current / total_current if total_current > 0 else 0
            desired_pct = desired / total_desired if total_desired > 0 else 0

            segments.append({
                "id": stratum.id,
                "name": stratum.name or stratum.id,
                "datetime": int(bucket_start.timestamp()),
                "currentParticipants": current,
                "expectedParticipants": 0,  # Not calculating expected
                "desiredParticipants": desired,
                "currentPercentage": current_pct,
                "expectedPercentage": 0,
                "desiredPercentage": desired_pct,
                "percentageDeviationFromGoal": abs(desired_pct - current_pct),
                "currentBudget": 0,
                "currentPricePerParticipant": 0,
            })

        result.append({
            "datetime": int(bucket_start.timestamp()),
            "segments": segments
        })

    return SegmentsProgressResponse(data=result)
```

#### New Helper Functions Needed

**File: `adopt/adopt/responses.py`**

```python
def create_time_buckets(
    start: datetime,
    end: datetime,
    bucket_size: str
) -> list[tuple[datetime, datetime]]:
    """Generate time bucket boundaries."""
    if bucket_size == "hour":
        delta = timedelta(hours=1)
    elif bucket_size == "day":
        delta = timedelta(days=1)
    elif bucket_size == "week":
        delta = timedelta(weeks=1)
    else:
        raise ValueError(f"Invalid bucket_size: {bucket_size}")

    buckets = []
    current = start.replace(minute=0, second=0, microsecond=0)
    if bucket_size == "day":
        current = current.replace(hour=0)
    elif bucket_size == "week":
        current = current - timedelta(days=current.weekday())
        current = current.replace(hour=0)

    while current < end:
        next_bucket = current + delta
        buckets.append((current, next_bucket))
        current = next_bucket

    return buckets
```

---

### Phase 2: Schema Definitions

#### Location
`adopt/adopt/server/server.py` (add to existing types, or new file)

```python
from pydantic import BaseModel
from typing import Optional

class SegmentProgressResource(BaseModel):
    """Matches existing Go API / frontend expectations"""
    id: str
    name: str
    datetime: int
    currentParticipants: int
    expectedParticipants: int
    desiredParticipants: Optional[int]
    currentPercentage: float
    expectedPercentage: float
    desiredPercentage: float
    percentageDeviationFromGoal: float
    currentBudget: float
    currentPricePerParticipant: float

class SegmentsProgressResponse(BaseModel):
    """List of time snapshots, each with segments"""
    data: list[dict]  # [{datetime: int, segments: [SegmentProgressResource]}]
```

---

### Phase 3: Frontend - Change API URL

The only frontend change is updating the API URL to point to the adopt server instead of the Go API.

#### Location
`dashboard/src/helpers/api.ts`

```typescript
// BEFORE: Called Go API
export async function fetchStudySegmentsProgress(slug: string) {
  const response = await fetch(
    `${getApiUrl()}/${orgPrefix()}/studies/${slug}/segments-progress`,
    { headers: await getAuthHeaders() }
  );
  return response.json();
}

// AFTER: Call adopt server directly
export async function fetchStudySegmentsProgress(slug: string) {
  const response = await fetch(
    `${getAdoptServerUrl()}/${orgPrefix()}/studies/${slug}/segments-progress`,
    { headers: await getAuthHeaders() }
  );
  return response.json();
}
```

**Note**: If `getAdoptServerUrl()` doesn't exist, add it based on environment config (similar to how other adopt server endpoints are called).

---

## File Changes Summary

### Modified Files
| File | Changes |
|------|---------|
| `adopt/adopt/server/server.py` | Add `/studies/{slug}/segments-progress` endpoint + schema types |
| `adopt/adopt/responses.py` | Add `create_time_buckets()` helper function |
| `dashboard/src/helpers/api.ts` | Change base URL from Go API to adopt server |

### Unchanged Files
| File | Notes |
|------|-------|
| `dashboard/src/pages/StudyPage/*` | All UI components unchanged |
| `dashboard/src/hooks/*` | All hooks unchanged |
| `api/*` | Go API not modified |

---

## Testing Plan

### Adopt Server Tests
Location: `adopt/adopt/server/test_server.py`

```python
async def test_segments_progress_endpoint():
    # Test with mock inference_data
    # Verify filtering matches prep_df_for_budget
    # Test daily bucket aggregation
    # Test cumulative counting
    # Test empty data handling
    # Test per-stratum counts
    # Verify response shape matches existing frontend expectations

async def test_time_bucket_creation():
    # Test create_time_buckets with various inputs
    # Test edge cases (DST, year boundaries)
```

### Integration Test
- Deploy to staging
- Compare old (`adopt_reports` via Go API) vs new (`inference_data` via adopt server) participant counts
- Verify UI displays correctly with new data source

---

## Migration Strategy

### Phase 1: Deploy New Endpoint
1. Deploy new endpoint to adopt server
2. Test endpoint independently (can call directly)
3. Verify response shape matches what frontend expects

### Phase 2: Switch Frontend URL
1. Update `dashboard/src/helpers/api.ts` to point to adopt server
2. Deploy frontend change
3. Monitor for errors

### Phase 3: Validate
1. Compare new respondent counts with old data
2. Ensure UI looks identical
3. Optionally remove old Go API endpoint if no longer needed

---

## Performance Considerations

### Adopt Server (Python)
- **Query optimization**: Index `inference_data` table on `(study_id, timestamp)`
- **Caching**: Consider caching results for 1-5 minutes (data doesn't change rapidly)
- **Async**: Already async in FastAPI, ensure DB queries are non-blocking

### Response Size
- Daily buckets limit response size (max ~365 buckets for daily over 1 year)
- Per-stratum breakdown adds modest overhead

---

## Open Questions / Decisions Needed

1. **Expected/Deviation data?** Keep these fields in response (with zeros) or remove from API contract?
2. **Caching strategy?** Cache at adopt server level?
3. **Go API cleanup?** Remove old segments-progress endpoint from Go API later?

### Decisions Made
- **UI visually unchanged**: Only API URL changes in frontend
- **Data source**: Switch from `adopt_reports` to `inference_data` with filtering
- **Aggregation**: Daily buckets, cumulative counts
- **Skip Go API**: Frontend calls adopt server directly

---

## Appendix: Key Code References

### Existing Filtering Logic
- `adopt/adopt/budget.py:110-119` - `prep_df_for_budget()`
- `adopt/adopt/clustering.py:96-114` - `only_target_users()`, `users_fulfilling()`
- `adopt/adopt/clustering.py:26-94` - `make_pred()` for question targeting

### Current Data Endpoint
- `adopt/adopt/server/server.py` - `get_current_data()`
- `adopt/adopt/responses.py` - `get_inference_data()`

### Dashboard Chart Components
- `dashboard/src/pages/StudyPage/components/SingleAreaChart.tsx`
- `dashboard/src/pages/StudyPage/components/StudyProgressChart.tsx`

### Database Schema (Referenced Tables)
- `inference_data`: `user_id`, `variable`, `value`, `timestamp`, `study_id`
- `adopt_reports`: `study_id`, `report_type`, `details`, `created`
