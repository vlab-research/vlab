# Advantage Audience Flag Investigation - Findings

## Summary

The user is encountering Facebook Ads API error: "Advantage Audience Flag Required. To create your ad set, you need to enable or disable the Advantage audience feature. This can be done by setting the advantage_audience flag to either 1 or 0 within the targeting_automation field in the targeting spec."

This flag is **NOT currently being set anywhere** in the codebase when creating ad sets. This is the root cause of the error.

## Quick Action Summary

**Location**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, function `create_adset()`, line 98-105

**Problem**: The targeting dict is created from study config but never includes the required `targeting_automation` nested object with `advantage_audience` flag.

**Quick Fix**: After line 98 where `targeting = {**c.stratum.facebook_targeting}` is created, add:
```python
if "targeting_automation" not in targeting:
    targeting["targeting_automation"] = {"advantage_audience": 0}
```

**Why**: Facebook Ads API now requires the `advantage_audience` flag (0 or 1) within the `targeting_automation` field. All ad set creation fails without it.

---

## Ad Set Creation Code Path

### Main Entry Point: `create_adset()` function
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py` (lines 96-120)

```python
def create_adset(c: AdsetConf) -> AdSet:
    name = c.stratum.id
    targeting = {**c.stratum.facebook_targeting}  # <-- Targets copied from study conf

    midnight = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=0)

    adset = AdSet()
    adset[AdSet.Field.end_time] = midnight + timedelta(hours=c.hours)
    adset[AdSet.Field.targeting] = targeting  # <-- Targeting spec is set here
    adset[AdSet.Field.status] = c.status
    adset[AdSet.Field.daily_budget] = c.budget
    adset[AdSet.Field.name] = name
    adset[AdSet.Field.start_time] = datetime.utcnow() + timedelta(minutes=5)
    adset[AdSet.Field.campaign_id] = c.campaign["id"]
    adset[AdSet.Field.optimization_goal] = c.optimization_goal
    adset[AdSet.Field.destination_type] = c.destination_type
    adset[AdSet.Field.billing_event] = AdSet.BillingEvent.impressions
    adset[AdSet.Field.bid_strategy] = AdSet.BidStrategy.lowest_cost_without_cap

    if c.promoted_object:
        adset[AdSet.Field.promoted_object] = c.promoted_object

    return adset
```

**Key Point**: The targeting spec is built from `c.stratum.facebook_targeting` - this comes directly from the Stratum model configured in the study configuration.

### Caller: `adset_instructions()` function
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py` (lines 443-503)

This function calls `create_adset()` with an `AdsetConf` object constructed from:
- Stratum data (including `facebook_targeting`)
- Recruitment configuration
- Budget information

---

## Study Configuration Structure

### Where Targeting is Defined
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/study_conf.py`

#### StratumConf (lines 404-414)
```python
class StratumConf(BaseModel):
    id: str
    quota: float
    creatives: List[str]
    audiences: List[str]
    excluded_audiences: List[str]
    facebook_targeting: FacebookTargeting  # <-- Raw dict of targeting params
    question_targeting: Optional[QuestionTargeting] = None
    metadata: Dict[str, str]
```

#### FacebookTargeting Type Definition (line 379)
```python
FacebookTargeting = Dict[str, Any]
```

**This is just a dictionary with any keys/values - no validation or required fields are enforced.**

#### Example Usage in Tests
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/test_heal_reports.py`

```python
Stratum(
    id="stratum_1",
    quota=100.0,
    creatives=[],
    facebook_targeting={"geo_locations": {"countries": ["US"]}},
    question_targeting=None,
    metadata={},
)
```

---

## Facebook SDK Type Definitions

### Targeting.Field (from stubs and actual SDK)
**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/targeting.pyi` (line 88-89)

The `Targeting.Field` class includes:
```python
targeting_automation: str  # Line 88
targeting_optimization: str  # Line 89
```

### TargetingAutomation Class
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/targetingautomation.pyi`

```python
class TargetingAutomation(AbstractObject):
    class Field(AbstractObject.Field):
        advantage_audience: str        # <-- The required flag
        individual_setting: str
        shared_audiences: str
        value_expression: str
```

The actual SDK implementation (`/adopt/.venv/lib/python3.10/site-packages/facebook_business/adobjects/targetingautomation.py`) confirms:
- `advantage_audience` field type is `'unsigned int'`
- Valid values are 0 or 1 (binary flag)

### AdSet.Field
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/adset.pyi` (line 68)

```python
targeting: str  # The targeting field that accepts a dict with all targeting params
```

---

## Current State of the Targeting Spec

### What's Currently Being Set
Looking through the codebase, targeting specs typically include fields like:
- `geo_locations` (with `countries` sub-field)
- Potentially custom audiences, interests, behaviors, etc.

### What's NOT Being Set
**The `targeting_automation` field is NEVER being constructed or added to the targeting dict.**

Example of what Facebook requires (implied by the error message):
```python
targeting = {
    "geo_locations": {"countries": ["US"]},
    # ... other targeting fields ...
    "targeting_automation": {
        "advantage_audience": 1  # or 0 - MUST be explicitly set
    }
}
```

---

## Database Schema

**File**: `/home/nandan/Documents/vlab-research/vlab/devops/migrations/20230322111807_init.up.sql` (lines 17-22)

```sql
CREATE TABLE IF NOT EXISTS study_confs(
       created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
       study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
       conf_type string NOT NULL,
       conf JSON NOT NULL
);
```

The entire configuration (including `facebook_targeting`) is stored as raw JSON in the `conf` column. There's no enforcement of required fields at the database level.

---

## Code References

### Validation Function
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py` (lines 89-93)

There IS a validation function for targeting specs:
```python
def validate_targeting(targeting):
    valid_targets = set(dir(Targeting.Field))
    for k, _ in targeting.items():
        if k not in valid_targets:
            raise Exception(f"Targeting config invalid, key: {k} does not exist!")
```

**This validates that targeting keys are valid Targeting.Field values, but it's NEVER CALLED in the main code path.** It exists but is unused.

---

## Root Cause

1. **The targeting spec is built from study configuration**: `c.stratum.facebook_targeting` comes from the `StratumConf` object
2. **No default value is provided**: The targeting dict is just a pass-through from configuration
3. **No validation ensures required fields**: The `validate_targeting()` function exists but is never called
4. **The `targeting_automation` field is never added**: Even if present in the study config, it would need to be a nested dict with `advantage_audience` inside it
5. **Facebook now requires this flag**: Recent changes to the Facebook Ads API now make this a required field for ad set creation

---

## Exact Locations Summary

| Item | File | Line(s) |
|------|------|---------|
| Where targeting is set in AdSet | `/adopt/adopt/marketing.py` | 105 |
| Where targeting dict is created | `/adopt/adopt/marketing.py` | 98 |
| Where AdsetConf is created | `/adopt/adopt/marketing.py` | 489-498 |
| Stratum model definition | `/adopt/adopt/study_conf.py` | 557-563 |
| StratumConf definition | `/adopt/adopt/study_conf.py` | 404-414 |
| FacebookTargeting type alias | `/adopt/adopt/study_conf.py` | 379 |
| validate_targeting() definition | `/adopt/adopt/marketing.py` | 89-93 |
| validate_targeting() called from | `/adopt/adopt/malaria.py` | 471 |
| Targeting.Field definition | `/adopt/stubs/facebook_business/adobjects/targeting.pyi` | 88-89 |
| TargetingAutomation definition | `/adopt/stubs/facebook_business/adobjects/targetingautomation.pyi` | 4-11 |

---

## Solution Path

To fix this, we need to:

1. **Add `targeting_automation` field to the targeting spec** in the `create_adset()` function
2. **Set the `advantage_audience` flag** to either 0 or 1 (default recommendation: 0 to disable Advantage Audience)
3. **Make this configurable** in the StudyConf if users want to enable it
4. **Consider validation updates** for the new nested field structure

### Example Fix Location
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py`

The fix should go in the `create_adset()` function, after line 98:

```python
def create_adset(c: AdsetConf) -> AdSet:
    name = c.stratum.id
    targeting = {**c.stratum.facebook_targeting}

    # Add required targeting_automation field with advantage_audience flag
    if "targeting_automation" not in targeting:
        targeting["targeting_automation"] = {
            "advantage_audience": 0  # Disable by default (0 = disabled, 1 = enabled)
        }

    # ... rest of the code ...
```

Or more robustly, if the field might already be partially defined:

```python
# Ensure targeting_automation field is set with advantage_audience
targeting_automation = targeting.get("targeting_automation", {})
if "advantage_audience" not in targeting_automation:
    targeting_automation["advantage_audience"] = 0
targeting["targeting_automation"] = targeting_automation
```

---

## Files Modified or Created
- No changes needed to `/adopt/adopt/study_conf.py` (the FacebookTargeting type is already flexible enough)
- No changes needed to database schema (JSON column is flexible)
- Main change needed in `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py` in the `create_adset()` function

---

## Additional Code References

### validate_targeting() Usage
**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/malaria.py` (line 471)

This is the ONLY place validate_targeting() is called:
```python
def load_strata_for_campaign(
    state: FacebookState, strata: List[StratumConf], creatives: List[CreativeConf]
) -> List[Stratum]:
    # Validate strata
    uniqueness(strata)
    for s in strata:
        validate_targeting(s.facebook_targeting)  # <-- Called here
```

This function is part of the malaria workflow for loading studies. The validation happens after study configuration is loaded from the database.

### How facebook_targeting Gets Built
**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/configuration.py`

The targeting specification is constructed dynamically during study creation from:
1. Base targeting params (app_install_state, user_device, user_os for app destinations)
2. Dynamically merged targeting parameters from configuration variables
3. Question targeting filters for segmentation

Example:
```python
facebook_targeting = base_targeting.copy()
# Then merged with additional targeting from config
if "facebook" in source:
    facebook_targeting = {**facebook_targeting, **c["params"]}
```

All constructed fields are flat key-value pairs. No nested structures are created at this stage.

## Critical Implementation Detail

The targeting dict is passed as-is to the AdSet object. The AdSet SDK field `targeting` accepts a dictionary. When sent to the Facebook API, this dictionary must include:

```python
{
    "targeting_automation": {
        "advantage_audience": 0 | 1
    }
}
```

The nested structure is NOT automatically created by the SDK - it must be explicitly constructed in the code.

## References to investigate further
- Facebook Ads API documentation on targeting_automation and advantage_audience
- Study configuration files in the repo (not explored in detail here) to see how targeting specs are currently being built
- Any recent changes to the Facebook Business SDK that might have introduced this requirement
- Whether advantage_audience flag should be configurable per-study or use a global default
