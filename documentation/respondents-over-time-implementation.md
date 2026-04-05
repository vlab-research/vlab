# Respondents Over Time Implementation

## Goal

Replace snapshot-based "participants over time" data from `adopt_reports` table with real-time participant counts from `inference_data` table, using the same filtering logic as optimization.

## Problem Statement

### What We Had
- Dashboard fetched "segments progress" data from `adopt_reports` table
- Reports were point-in-time snapshots generated during optimization runs
- Data included projected metrics (Expected Participants, Deviation) that weren't proving useful
- No individual participant timestamps - couldn't see when each participant actually started

### Issues
1. **Snapshots only when optimization runs** - not continuous data
2. **No actual participant timestamps** - couldn't track real join times
3. **Projections not useful** - expected/deviation metrics don't reflect reality
4. **Filtering inconsistency** - data wasn't filtered the same way as optimization logic

### What We Wanted
- Respondents over time based on actual participant `timestamp` from `inference_data`
- Same filtering logic as optimization (`prep_df_for_budget` → `only_target_users`)
- Per-stratum breakdown
- Fast API response (not computing on every request)

---

## Architecture

### Data Flow

```
Optimization Run (update_ads_for_campaign)
    ↓
Load inference_data (already happening)
    ↓
Calculate respondents over time using same filtering
    ↓
Store in adopt_reports table (type: 'respondents_over_time')
    ↓
Dashboard API Request
    ↓
Adopt Server: GET /{org}/studies/{slug}/segments-progress
    ↓
Read pre-computed report from adopt_reports (fast DB lookup)
    ↓
Dashboard: useStudy() hook transforms data
    ↓
StudyProgressChart component displays time chart
```

### Two API Endpoints

| API | Endpoint | Used For | Data Source |
|-----|----------|----------|-------------|
| **Old Go API** | `GET /studies/{slug}/segments-progress` | Segment table, stats cards, other components | Original adopt_reports snapshots |
| **New Adopt Server** | `GET /{org}/studies/{slug}/segments-progress` | Participants over time chart | Pre-computed respondents_over_time reports |

---

## Implementation

### Backend Changes

#### 1. Business Logic Module (`adopt/adopt/segments_progress.py`)

Pure, testable functions for calculating respondents over time:

```python
def get_user_start_times(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """Extract first timestamp per user by stratum."""

def count_users_in_bucket(user_start_times, bucket_start, bucket_end) -> dict[str, int]:
    """Count new users per stratum within a time bucket."""

def build_segments_progress_data(user_start_times, buckets, strata_ids) -> list[dict]:
    """Build time-series data with cumulative participant counts."""
```

**Test Coverage:** 18 unit tests with 100% coverage

#### 2. Time Bucketing Helper (`adopt/adopt/responses.py`)

```python
def create_time_buckets(start: datetime, end: datetime, bucket_size: str) -> list[tuple]:
    """Generate time bucket boundaries (hour, day, or week)."""
```

**Test Coverage:** 34 tests covering edge cases, boundaries, DST

#### 3. Report Generation (`adopt/adopt/malaria.py`)

```python
def calculate_respondents_over_time_report(
    df: pd.DataFrame,
    strata: list[StratumConf],
    start_date: datetime,
    end_date: datetime
) -> dict:
    """Calculate respondents over time data for storage as a report."""
```

Called during `update_ads_for_campaign()` - runs automatically during optimization.

#### 4. Report Storage & Retrieval (`adopt/adopt/campaign_queries.py`)

```python
def create_respondents_over_time_report(study_id: str, report_data: dict, cnf: DBConf):
    """Store respondents over time report in adopt_reports table."""

def get_latest_respondents_over_time_report(study_id: str, cnf: DBConf) -> dict | None:
    """Retrieve latest report for a study."""
```

#### 5. API Endpoint (`adopt/adopt/server/server.py`)

```python
@app.get("/{org_id}/studies/{slug}/segments-progress")
async def get_segments_progress(...) -> RespondentsOverTimeResponse:
    """
    Fast endpoint that reads pre-computed report from database.
    Returns empty data if no report exists yet.
    """
```

**Response Schema:**
```json
{
  "data": [
    {
      "datetime": 1704067200000,
      "totalParticipants": 150,
      "segments": [
        {"id": "segment_1", "participants": 80},
        {"id": "segment_2", "participants": 70}
      ]
    }
  ]
}
```

### Frontend Changes

#### 1. API Functions (`dashboard/src/helpers/api.ts`)

```typescript
// Old Go API - for segment table and other components
const fetchStudySegmentsProgress = ({ slug, accessToken }) =>
  apiRequest<StudySegmentsProgressApiResponse>(
    `/${orgPrefix()}/studies/${slug}/segments-progress`,
    { accessToken }
  );

// New Adopt Server API - for participants over time chart
const fetchRespondentsOverTime = ({ slug, accessToken }) =>
  apiRequest<RespondentsOverTimeApiResponse>(
    `/${orgPrefix()}/studies/${slug}/segments-progress`,
    {
      accessToken,
      baseURL: process.env.REACT_APP_CONF_SERVER_URL,
    }
  );
```

#### 2. React Hook (`dashboard/src/pages/StudyPage/hooks/useStudy.tsx`)

```typescript
const useStudy = (slug: string) => {
  // Old Go API - for segment table
  const studySegmentsProgressQuery = useStudySegmentsProgressQuery(slug);

  // New Adopt Server API - for time chart
  const respondentsOverTimeQuery = useRespondentsOverTimeQuery(slug);

  const progressOverTime = useMemo(() => {
    const apiData = respondentsOverTimeQuery.data?.data ?? [];
    return apiData.map(transformToStudyProgress);
  }, [respondentsOverTimeQuery.data]);

  const currentSegmentsProgress = useMemo(() => {
    const lastTimePoint = lastValue(segmentsProgressOverTime);
    return lastTimePoint ? lastTimePoint.segments : [];
  }, [segmentsProgressOverTime]);

  // ... return both for different UI components
};
```

#### 3. TypeScript Types (`dashboard/src/types/study.ts`)

```typescript
export interface SegmentParticipantsData {
  id: string;
  participants: number;
}

export interface RespondentsTimePointData {
  datetime: number;
  totalParticipants: number;
  segments: SegmentParticipantsData[];
}

export interface RespondentsOverTimeApiResponse
  extends ApiResponse<RespondentsTimePointData[]> {}
```

---

## Key Design Decisions

### 1. Pre-compute During Optimization
**Decision:** Calculate and store reports during optimization runs instead of computing on-demand.

**Rationale:**
- Inference data is already loaded during optimization
- Minimal additional cost to calculate at that time
- Fast API response (DB lookup vs. processing all data)
- Consistent with existing report pattern

**Trade-off:** Data only updates when optimization runs (acceptable for this use case)

### 2. API Returns Only Participant Counts
**Decision:** Don't include quota/budget/price data in the new API.

**Rationale:**
- This data is static configuration (doesn't change over time)
- Frontend already has access to study config
- Keeps API response clean and focused
- Reduces payload size

**Alternative Considered:** Include all metrics like the old API - rejected as unnecessary duplication.

### 3. Two Separate API Calls
**Decision:** Keep old Go API for segment table, add new adopt server API for time chart.

**Rationale:**
- Allows gradual migration
- Old components continue working unchanged
- New chart gets better data source
- Can deprecate old API later if needed

**Alternative Considered:** Single unified API - rejected as too risky for migration.

### 4. Reuse Existing Patterns
**Decision:** Use `fetch_current_data()`, `load_basics()`, and existing report storage.

**Rationale:**
- Reduces code duplication
- Consistent with codebase patterns
- Leverages battle-tested functions
- Easier to maintain

---

## Testing

### Unit Tests
- **`test_segments_progress.py`**: 18 tests for business logic (100% coverage)
- **`test_responses.py`**: 34 tests for time bucketing (edge cases, boundaries, DST)

### Test Strategy
- Business logic extracted into pure functions for easy testing
- No mocking needed - functions are side-effect free
- Integration testing happens naturally during optimization runs

---

## Deployment Notes

### First-Time Setup

1. **Run optimization to generate first report:**
   ```bash
   # Optimization will automatically create respondents_over_time report
   poetry run python -m adopt.malaria update_ads
   ```

2. **Verify report in database:**
   ```sql
   SELECT study_id, report_type, created
   FROM adopt_reports
   WHERE report_type = 'respondents_over_time'
   ORDER BY created DESC;
   ```

3. **Test API endpoint:**
   ```bash
   curl http://localhost:3500/{org_id}/studies/{slug}/segments-progress \
     -H "Authorization: Bearer {token}"
   ```

### Environment Variables

Dashboard needs adopt server URL:
```bash
REACT_APP_CONF_SERVER_URL=http://localhost:3500
```

### Performance Expectations

- **API Response Time:** ~10-50ms (database lookup)
- **Report Generation:** Adds ~100-500ms to optimization run
- **Report Size:** ~1-10KB per study (depends on date range and strata count)

---

## Future Improvements

### Possible Enhancements

1. **On-Demand Report Generation**
   - Add endpoint to trigger report calculation manually
   - Useful for debugging or immediate updates

2. **Hourly/Weekly Bucketing**
   - Currently uses daily buckets
   - Add UI control to select bucket size

3. **Export Functionality**
   - Download CSV of respondents over time data
   - Useful for external analysis

4. **Real-time Updates**
   - WebSocket or polling for live updates
   - Currently updates only during optimization

5. **Unified API**
   - Merge old and new APIs into single endpoint
   - Deprecate old Go API segments-progress endpoint

---

## Files Changed

### Created
- `adopt/adopt/segments_progress.py` - Business logic (122 lines)
- `adopt/adopt/test_segments_progress.py` - Unit tests (454 lines)

### Modified
- `adopt/adopt/responses.py` - Added `create_time_buckets()` helper
- `adopt/adopt/test_responses.py` - Added 34 time bucket tests
- `adopt/adopt/server/server.py` - Added endpoint (updated to read from reports)
- `adopt/adopt/malaria.py` - Added report calculation function + trigger
- `adopt/adopt/campaign_queries.py` - Added report storage/retrieval functions
- `dashboard/src/helpers/api.ts` - Added `fetchRespondentsOverTime()`
- `dashboard/src/pages/StudyPage/hooks/useStudy.tsx` - Updated to use both APIs
- `dashboard/src/types/study.ts` - Added new response types

### Test Results
```
52 passed (Python)
- 18 tests for segments_progress
- 34 tests for time bucketing
```

---

## Commits

1. `feat(dashboard): add respondents over time from inference data` - Initial implementation
2. `refactor(server): reuse fetch_current_data in segments-progress endpoint` - Code cleanup
3. `perf(server): pre-compute respondents over time in optimization runs` - Performance optimization

---

## References

- Original plan: `/home/nandan/Documents/vlab-research/vlab/docs/plans/respondents-over-time-implementation.md`
- Development philosophy: `/home/nandan/Documents/vlab-research/vlab/CLAUDE.md`
