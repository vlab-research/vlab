# Report Healing Job Implementation Plan

## Overview

Create a "healing job" that regenerates `respondents_over_time` and `cost_over_time` reports for studies without running the full optimization process. This job runs daily via cron and processes studies that have been active within the past X days.

### Why This Is Needed

Currently, reports are only generated as a side effect of the optimization job (`update_ads_for_campaign` in `malaria.py`). If optimization fails or is skipped, reports are not generated. The healing job provides a lightweight way to ensure reports stay up-to-date.

### Key Insight

The report generation functions (`calculate_respondents_over_time_report` and `calculate_cost_over_time_report`) are **not coupled to optimization**. They only need:
- `inference_data` table (survey responses)
- `recruitment_data_events` table (ad spend data)
- Study configuration (strata, incentive_per_respondent)

**No Facebook API access or optimization logic required.**

---

## File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `adopt/adopt/recruitment_data.py` | MODIFY | Add `get_recent_studies()` function |
| `adopt/adopt/malaria.py` | MODIFY | Add 3 functions for healing job |
| `adopt/heal_reports.py` | NEW | Entry point script for cron |
| `devops/helm/values.yaml` | MODIFY | Add cronjob configuration |

---

## Implementation Details

### 1. Add `get_recent_studies()` to `recruitment_data.py`

**Location:** `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/recruitment_data.py`

**Purpose:** Query studies that have been active within the past X days (not just currently active ones).

**Add after the existing `get_active_studies()` function (around line 280):**

```python
def get_recent_studies(db_conf: DBConf, now: datetime, days_back: int) -> list[str]:
    """
    Get studies that have been active within the past X days.

    This includes:
    - Studies currently active (start_date < now < end_date)
    - Studies that ended within the past X days
    - Studies that started within the past X days

    Args:
        db_conf: Database configuration (PG_URL)
        now: Current datetime
        days_back: Number of days to look back

    Returns:
        List of study IDs
    """
    cutoff = now - timedelta(days=days_back)

    q = """
    SELECT id FROM studies
    JOIN study_state USING(id)
    WHERE
        -- Currently active
        (study_state.start_date < %s AND study_state.end_date > %s)
        OR
        -- Ended within the past X days
        (study_state.end_date >= %s AND study_state.end_date <= %s)
        OR
        -- Started within the past X days
        (study_state.start_date >= %s AND study_state.start_date <= %s)
    """

    res = query(db_conf, q, (now, now, cutoff, now, cutoff, now))
    return [t[0] for t in res]
```

**Required import:** `timedelta` from `datetime` (already imported in this file).

---

### 2. Add Healing Job Functions to `malaria.py`

**Location:** `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/malaria.py`

Add these three functions. Suggested location: after `run_updates()` function (around line 294).

#### 2.1 `get_study_conf_for_reports()`

**Purpose:** Load study configuration without requiring Facebook credentials.

```python
def get_study_conf_for_reports(db_conf: DBConf, study_id: str) -> StudyConf:
    """
    Load study configuration for report generation only.

    Unlike get_study_conf(), this does not require valid Facebook credentials.
    It uses the study_id as the survey_user since get_inference_data()
    queries by study_id directly.

    Args:
        db_conf: Database configuration
        study_id: Study ID

    Returns:
        StudyConf with minimal user info (no FB token required)
    """
    from .campaign_queries import get_campaign_configs

    confs = get_campaign_configs(study_id, db_conf)
    cd = {v["conf_type"]: v["conf"] for v in confs}

    # For reports, we don't need actual Facebook credentials
    # Use study_id as survey_user since inference_data is queried by study_id
    user_info = {"token": "", "survey_user": study_id}

    params = {"id": str(study_id), "user": user_info, **cd}
    return StudyConf(**params)
```

#### 2.2 `heal_reports_for_study()`

**Purpose:** Generate both reports for a single study.

```python
def heal_reports_for_study(db_conf: DBConf, study_id: str) -> tuple[bool, bool]:
    """
    Generate respondents_over_time and cost_over_time reports for a study.

    This function does NOT run optimization or require Facebook API access.
    It only reads from inference_data and recruitment_data_events tables.

    Args:
        db_conf: Database configuration
        study_id: Study ID to generate reports for

    Returns:
        Tuple of (respondents_success, cost_success) booleans
    """
    respondents_success = False
    cost_success = False

    try:
        study = get_study_conf_for_reports(db_conf, study_id)
    except Exception as e:
        logging.error(f"Failed to load study config for {study_id}: {e}")
        return respondents_success, cost_success

    # Get inference window from recruitment config
    now = datetime.utcnow()
    inf_start, inf_end = study.recruitment.get_inference_window(now)

    # Load inference data (no FB API needed)
    df = get_inference_data(
        study.user.survey_user, study.id, db_conf, inf_start, inf_end
    )

    # Generate respondents over time report
    try:
        from .campaign_queries import create_respondents_over_time_report
        respondents_report = calculate_respondents_over_time_report(
            df, study.strata, inf_start, inf_end
        )
        create_respondents_over_time_report(study.id, respondents_report, db_conf)
        logging.info(f"Healed respondents_over_time report for study {study_id}")
        respondents_success = True
    except Exception as e:
        logging.error(f"Error healing respondents_over_time report for {study_id}: {e}")

    # Generate cost over time report
    try:
        from .campaign_queries import create_cost_over_time_report
        cost_report = calculate_cost_over_time_report(
            df, study.strata, db_conf, study.id,
            study.recruitment.incentive_per_respondent
        )
        create_cost_over_time_report(study.id, cost_report, db_conf)
        logging.info(f"Healed cost_over_time report for study {study_id}")
        cost_success = True
    except Exception as e:
        logging.error(f"Error healing cost_over_time report for {study_id}: {e}")

    return respondents_success, cost_success
```

#### 2.3 `run_report_healing()`

**Purpose:** Main entry point - iterate over recent studies and heal reports.

```python
def run_report_healing(days_back: int = 14) -> None:
    """
    Heal reports for all studies active in the past X days.

    This is the entry point for the healing CronJob. It:
    1. Gets all studies active within the lookback window
    2. Generates respondents_over_time and cost_over_time reports for each
    3. Does NOT run optimization or require Facebook API access

    Args:
        days_back: Number of days to look back for studies (default: 14)
    """
    from .recruitment_data import get_recent_studies

    env = Env()
    db_conf = get_db_conf(env)
    now = datetime.utcnow()

    studies = get_recent_studies(db_conf, now, days_back)
    logging.info(f"Report healing: found {len(studies)} studies (lookback: {days_back} days)")

    success_count = 0
    failure_count = 0

    for study_id in studies:
        try:
            respondents_ok, cost_ok = heal_reports_for_study(db_conf, study_id)
            if respondents_ok and cost_ok:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logging.error(f"Failed to heal reports for study {study_id}: {e}")
            failure_count += 1

    logging.info(f"Report healing complete: {success_count} succeeded, {failure_count} failed")
```

---

### 3. Create Entry Point Script

**Location:** `/home/nandan/Documents/vlab-research/vlab/adopt/heal_reports.py` (NEW FILE)

**Purpose:** Entry point for the cron job, following the pattern of `malaria_ads.py`.

```python
"""
Report healing job entry point.

Generates respondents_over_time and cost_over_time reports for recent studies
without running optimization. Safe to run frequently as it only reads from
inference_data and recruitment_data_events tables.

Environment variables:
    REPORT_HEALING_DAYS_BACK: Number of days to look back (default: 14)
    PG_URL: PostgreSQL connection string (required)
"""

import os
from adopt.malaria import run_report_healing

DAYS_BACK = int(os.environ.get("REPORT_HEALING_DAYS_BACK", "14"))

run_report_healing(days_back=DAYS_BACK)
```

---

### 4. Add CronJob Configuration

**Location:** `/home/nandan/Documents/vlab-research/vlab/devops/helm/values.yaml`

**Add to the `cronjobs` list:**

```yaml
  - name: adopt-heal-reports
    schedule: "0 5 * * *"  # Daily at 5 AM UTC
    image:
      repository: "vlabresearch/adopt"
      tag: "inference-data"
      pullPolicy: Always
    args:
      - python
      - heal_reports.py
    env:
      - name: REPORT_HEALING_DAYS_BACK
        value: "14"
```

**Schedule reasoning:**
- Runs once daily at 5 AM UTC
- After the overnight `adopt-recruitment-data` job (which runs at `10 */4 * * *`)
- Low-traffic time for database

---

## Data Flow

```
heal_reports.py (entry point)
    │
    ▼
run_report_healing(days_back=14)
    │
    ├── get_recent_studies(db_conf, now, days_back)
    │       │
    │       ▼
    │   SELECT from studies + study_state
    │   (studies active/started/ended in past 14 days)
    │
    └── for each study_id:
            │
            ▼
        heal_reports_for_study(db_conf, study_id)
            │
            ├── get_study_conf_for_reports(db_conf, study_id)
            │       │
            │       ▼
            │   Load from study_confs table (no FB credentials needed)
            │
            ├── get_inference_data(survey_user, study_id, db_conf, inf_start, inf_end)
            │       │
            │       ▼
            │   SELECT from inference_data table
            │
            ├── calculate_respondents_over_time_report(df, strata, inf_start, inf_end)
            │       │
            │       ▼
            │   Pure calculation (no I/O)
            │
            ├── create_respondents_over_time_report(study_id, report, db_conf)
            │       │
            │       ▼
            │   INSERT into adopt_reports table
            │
            ├── calculate_cost_over_time_report(df, strata, db_conf, study_id, incentive)
            │       │
            │       ▼
            │   Calculation + SELECT from recruitment_data_events
            │
            └── create_cost_over_time_report(study_id, report, db_conf)
                    │
                    ▼
                INSERT into adopt_reports table
```

---

## Error Handling

Following the existing pattern in `run_updates()`:

1. **Continue on failure**: If one study fails, continue processing others
2. **Log errors with study ID**: Include study_id in all error messages
3. **Track success/failure counts**: Log summary at end
4. **Graceful degradation**: If respondents report fails, still try cost report

---

## Testing

### Manual Testing

```bash
# Set environment
export PG_URL="postgresql://..."
export REPORT_HEALING_DAYS_BACK=7

# Run directly
cd /home/nandan/Documents/vlab-research/vlab/adopt
python heal_reports.py
```

### Verify Reports Created

```sql
-- Check for recent reports
SELECT study_id, report_type, created
FROM adopt_reports
WHERE report_type IN ('respondents_over_time', 'cost_over_time')
ORDER BY created DESC
LIMIT 20;
```

### Unit Tests to Add

**File:** `adopt/test/test_heal_reports.py`

```python
def test_get_recent_studies_includes_active():
    """Active studies should be included."""

def test_get_recent_studies_includes_recently_ended():
    """Studies that ended within lookback window should be included."""

def test_get_recent_studies_excludes_old():
    """Studies that ended before lookback window should be excluded."""

def test_get_study_conf_for_reports_no_fb_credentials():
    """Should load config without requiring Facebook token."""

def test_heal_reports_for_study_creates_both_reports():
    """Should create both respondents and cost reports."""

def test_heal_reports_continues_on_single_failure():
    """If one report fails, should still attempt the other."""
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `REPORT_HEALING_DAYS_BACK` | `14` | Number of days to look back for studies |
| `PG_URL` | (required) | PostgreSQL connection string |

---

## Rollout Plan

1. **Implement code changes** (recruitment_data.py, malaria.py, heal_reports.py)
2. **Test locally** against staging database
3. **Verify reports** appear correctly in adopt_reports table
4. **Build and push** new adopt Docker image
5. **Deploy Helm chart** with new cronjob
6. **Monitor logs** for first few runs

---

## Dependencies

### Database Tables (read)
- `studies` - Study metadata
- `study_state` - Start/end dates
- `study_confs` - Study configuration (strata, recruitment config)
- `inference_data` - Survey response data
- `recruitment_data_events` - Ad spend data from Facebook

### Database Tables (write)
- `adopt_reports` - Report storage

### Python Functions (existing, no changes needed)
- `calculate_respondents_over_time_report()` in malaria.py
- `calculate_cost_over_time_report()` in malaria.py
- `create_respondents_over_time_report()` in campaign_queries.py
- `create_cost_over_time_report()` in campaign_queries.py
- `get_inference_data()` in responses.py
- `get_campaign_configs()` in campaign_queries.py

---

## Notes

- The healing job does **not** require Facebook API credentials
- Reports are append-only (immutable) - running multiple times is safe
- The job uses the same calculation functions as the optimization job, ensuring consistency
- Schedule can be adjusted based on operational needs (more frequent if reports are critical)
