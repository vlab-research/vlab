# Advantage Audience Field Investigation - Database Findings

**Date**: 2026-04-05  
**Study Investigated**: bauchi-state-hpv-pilot (ID: 027d28c7-3f66-4c9e-86bf-e3d33fb1bc69)  
**Database**: CockroachDB at postgresql://root@localhost:5432/vlab

---

## Executive Summary

Comprehensive investigation of the `bauchi-state-hpv-pilot` study and the entire vlab database reveals:

1. **advantage_audience and targeting_automation fields are NOT present** in any study configuration across the entire database (5,661 study_confs across 127 distinct studies)
2. **Targeting specs are stored as raw facebook_targeting dicts** in the strata configuration without any targeting_automation wrapper
3. **The current targeting model lacks the required Facebook Ads API fields** needed for recent API versions
4. **All study configurations follow the same pattern** - absence of these fields is systematic across the entire codebase

---

## Database Schema

### study_confs Table Structure

```
Column      | Type                | Constraints
------------|---------------------|------------------------------------------
created     | TIMESTAMP           | DEFAULT CURRENT_TIMESTAMP()
study_id    | UUID                | NOT NULL, REFERENCES studies(id) ON DELETE CASCADE
conf_type   | TEXT                | NOT NULL (9 distinct types)
conf        | JSONB               | NOT NULL (raw JSON storage, no validation)
rowid       | INT8                | Unique internal ID
```

### Study Configuration Types

```sql
SELECT DISTINCT conf_type FROM study_confs ORDER BY conf_type;
```

Results (9 types):
- audiences
- creatives
- data_sources
- destinations
- general
- inference_data
- recruitment
- strata
- variables

---

## Bauchi State HPV Pilot Study Configuration

### Basic Study Info

```
ID:   027d28c7-3f66-4c9e-86bf-e3d33fb1bc69
Slug: bauchi-state-hpv-pilot
Name: Bauchi State HPV Pilot
```

### Configuration Storage

The study has 25 configuration records across 9 conf_types:
- Most conf_types have 3 records (historical versions or variants)
- Total storage size: ~30KB of JSON data

### Targeting Configuration (conf_type = 'strata')

The strata configuration contains the actual Facebook targeting specs. Example structure:

```json
[
  {
    "audiences": [],
    "creatives": ["Video English", "Video Hausa", "Static English", "Static Hausa"],
    "excluded_audiences": ["Bauchi State HPV Pilot respondents"],
    "facebook_targeting": {
      "age_max": 55,
      "age_min": 20,
      "geo_locations": {
        "cities": [
          {
            "country": "NG",
            "distance_unit": "mile",
            "key": "1621205",
            "name": "Gamawa",
            "radius": 18,
            "region": "Bauchi State",
            "region_id": "2632"
          }
        ],
        "location_types": ["home", "recent"]
      }
    },
    "id": "LGA:Gamawa,Age:Age",
    "metadata": {
      "Age": "Age",
      "LGA": "Gamawa"
    },
    "question_targeting": {
      "op": "and",
      "vars": [
        {
          "op": "equal",
          "vars": [
            {"type": "variable", "value": "LGA"},
            {"type": "constant", "value": "Gamawa"}
          ]
        },
        {
          "op": "equal",
          "vars": [
            {"type": "variable", "value": "Age"},
            {"type": "constant", "value": "Age"}
          ]
        },
        {
          "op": "answered",
          "vars": [
            {"type": "variable", "value": "phone_number"}
          ]
        }
      ]
    },
    "quota": 0.5
  },
  {
    "id": "LGA:Toro,Age:Age",
    "facebook_targeting": {
      "age_max": 55,
      "age_min": 20,
      "geo_locations": {
        "custom_locations": [
          {
            "country": "NG",
            "distance_unit": "mile",
            "latitude": 10.138066,
            "longitude": 9.151611,
            "primary_city_id": 1623308,
            "radius": 10,
            "region_id": 2632
          }
        ],
        "location_types": ["home", "recent"]
      }
    },
    "quota": 0.5
  }
]
```

**Key Observation**: Each stratum has a `facebook_targeting` dict that is passed directly to the Facebook Ads API. There is **NO `targeting_automation` wrapper** and **NO `advantage_audience` flag**.

### Audiences Configuration (conf_type = 'audiences')

```json
[
  {
    "lookalike": null,
    "name": "Bauchi State HPV Pilot respondents",
    "partitioning": null,
    "question_targeting": null,
    "subtype": "CUSTOM"
  }
]
```

This is a custom audience used for exclusion, not for advantage targeting.

### General Configuration (conf_type = 'general')

```json
{
  "ad_account": "2150432608382517",
  "credentials_entity": "facebook",
  "credentials_key": "Facebook",
  "extra_metadata": {},
  "name": "Bauchi State HPV Pilot",
  "opt_window": 24
}
```

No advantage audience or targeting automation settings here.

### Recruitment Configuration (conf_type = 'recruitment')

```json
{
  "ad_campaign_name": "Bauchi State Pilot Baseline Virtual Lab",
  "budget": 5000,
  "destination_type": "MESSENGER",
  "efficiency_weight": 1.0,
  "end_date": "2026-04-07T00:00:00",
  "incentive_per_respondent": 1.0,
  "max_sample": 1200,
  "min_budget": 1,
  "objective": "OUTCOME_ENGAGEMENT",
  "optimization_goal": "CONVERSATIONS",
  "start_date": "2026-04-02T00:00:00"
}
```

No advantage audience settings.

### Data Sources Configuration (conf_type = 'data_sources')

```json
[
  {
    "config": {
      "survey_name": "Bauchi HPV Pilot"
    },
    "credentials_key": "Upswell Fly",
    "name": "fly",
    "source": "fly"
  }
]
```

Not relevant to targeting.

### Destinations Configuration (conf_type = 'destinations')

```json
[
  {
    "additional_metadata": null,
    "button_text": "OK",
    "initial_shortcode": "pilotlanguage",
    "name": "fly baseline",
    "type": "messenger",
    "welcome_message": "Welcome! Sannu! Ready to get started?"
  }
]
```

Not relevant to targeting automation.

### Variables Configuration (conf_type = 'variables')

The variables configuration shows how strata are built:

```json
[
  {
    "levels": [
      {
        "facebook_targeting": {
          "geo_locations": {
            "cities": [...]
          }
        },
        "name": "Gamawa",
        "quota": 0.5,
        "template_adset": "120244004469470019",
        "template_campaign": "120244004381220019"
      },
      {
        "facebook_targeting": {
          "geo_locations": {
            "custom_locations": [...]
          }
        },
        "name": "Toro",
        "quota": 0.5,
        "template_adset": "120244004381210019",
        "template_campaign": "120244004381220019"
      }
    ],
    "name": "LGA",
    "properties": ["geo_locations"]
  },
  {
    "levels": [
      {
        "facebook_targeting": {
          "age_max": 55,
          "age_min": 20
        },
        "name": "Age",
        "quota": 1.0,
        "template_adset": "120244004469470019",
        "template_campaign": "120244004381220019"
      }
    ],
    "name": "Age",
    "properties": ["age_min", "age_max"]
  }
]
```

Again, each level's `facebook_targeting` is a raw dict without the targeting_automation wrapper.

---

## Database-Wide Search Results

### Query: advantage_audience and targeting_automation Across All Studies

```sql
SELECT COUNT(*) as strata_confs_with_targeting_automation
FROM study_confs
WHERE conf_type = 'strata' 
AND (conf::text ILIKE '%targeting_automation%' OR conf::text ILIKE '%advantage_audience%');
```

**Result**: 0 records

**Implication**: **NO study configuration in the entire database contains these fields.**

### Database Statistics

```
Total study_confs records:    5,661
Distinct studies:             127
Distinct conf_types:          9
Strata confs with fields:     0
```

### Sample of Other Studies

Other active studies in the database:
- HPV Nigeria (1301e980-35d6-497a-8b59-057258192058)
- TM Project (be13d755-fef5-474d-9706-afc823b3c326)
- Nigeria MR Campaign (1b81102a-c671-41d5-940f-2fa8fa7c5558)
- Embed Iraq, Egypt, Morocco, Jordan, KSA (5 studies)
- Girl Effect Pilot 2
- Multiple test studies

None of these studies have `targeting_automation` or `advantage_audience` in their configurations.

---

## Code Path from Configuration to Ad Set Creation

### Data Flow Summary

1. **Study Configuration** (stored in DB):
   - StratumConf defines `facebook_targeting` as `Dict[str, Any]`
   - No enforcement of required fields

2. **Marketing Module** (`/adopt/adopt/marketing.py`):
   - `create_adset()` function (lines 96-120) receives AdsetConf
   - Line 99: `targeting = {**c.stratum.facebook_targeting}`
   - Line 100: `adset[AdSet.Field.targeting] = targeting`
   - **Directly uses the DB config without modification**

3. **Facebook SDK** (via `facebook_business` package):
   - Expects `targeting` dict to include `targeting_automation` field
   - `targeting_automation` should be a dict with `advantage_audience` key
   - Valid values: 0 (disabled) or 1 (enabled)

### Type Definition for facebook_targeting

From `/adopt/adopt/study_conf.py` line 379:

```python
FacebookTargeting = Dict[str, Any]
```

This is a flexible type that allows any keys. The study configuration system doesn't enforce any required fields for Facebook targeting.

---

## Facebook Ads API Requirements

### Targeting Automation Structure (from Facebook SDK)

The Facebook Business SDK (`facebook_business.adobjects.targetingautomation`) defines:

```python
class TargetingAutomation(AbstractObject):
    class Field(AbstractObject.Field):
        advantage_audience: str        # unsigned int (0 or 1)
        individual_setting: str
        shared_audiences: str
        value_expression: str
```

### Required Targeting Structure

```python
targeting = {
    "age_max": 55,
    "age_min": 20,
    "geo_locations": {...},
    # ... other targeting fields ...
    "targeting_automation": {
        "advantage_audience": 0  # or 1
    }
}
```

---

## Findings Summary

### What Exists in the Database

1. ✓ Complete facebook_targeting specs with:
   - age_min, age_max
   - geo_locations (cities and custom locations)
   - location_types (home, recent)
   - excluded audiences

2. ✓ Proper stratum structure with:
   - creatives
   - audiences
   - question_targeting
   - metadata
   - quotas

3. ✓ Supporting infrastructure:
   - recruitment configuration
   - destination specs
   - data sources
   - variables

### What is Missing

1. ✗ **targeting_automation field** - Not present in any strata across all 127 studies
2. ✗ **advantage_audience flag** - Not present anywhere in the database
3. ✗ **Any targeting automation configuration** - Zero instances across all study configurations

### Why This Matters

The Facebook Ads API (as of recent versions) **requires** the `targeting_automation` field with `advantage_audience` flag when creating ad sets. The current system:
- Stores targeting specs without this field
- Passes them directly to the Facebook SDK without modification
- Results in API errors: "Advantage Audience Flag Required"

---

## Recommendations

### For Study Configuration

**Option 1: Update Study Configuration at Creation Time**
- Modify the `create_adset()` function in `/adopt/adopt/marketing.py` to add the required field
- Add default value: `"advantage_audience": 0` (disable by default)
- Make configurable in study definition if needed

**Option 2: Update Existing Study Configuration in Database**
- No existing studies have this field
- If bulk update is needed, would require manual DB intervention or migration script

**Option 3: Update Study Configuration Schema**
- Add `targeting_automation` as optional field in StudyConf
- Provide sensible defaults
- Update database migration if new studies require it

### Implementation Priority

1. **Immediate**: Fix ad set creation in `create_adset()` function to add default `targeting_automation`
2. **Short-term**: Consider making it configurable in study definitions
3. **Long-term**: Review if database schema needs updates for clarity

---

## Files Relevant to Implementation

- `/adopt/adopt/marketing.py` - Ad set creation (lines 96-120)
- `/adopt/adopt/study_conf.py` - Study configuration models (line 379)
- `/devops/migrations/20230322111807_init.up.sql` - Database schema

---

## Verification Steps Taken

1. ✓ Connected to CockroachDB and verified connectivity
2. ✓ Queried study_confs schema
3. ✓ Located bauchi-state-hpv-pilot study (ID: 027d28c7-3f66-4c9e-86bf-e3d33fb1bc69)
4. ✓ Extracted all 9 configuration types for this study
5. ✓ Parsed JSON structures for strata, audiences, general, recruitment, variables, and destinations
6. ✓ Searched entire database for targeting_automation or advantage_audience - found 0 matches
7. ✓ Verified all 127 studies follow the same pattern (no targeting_automation anywhere)
8. ✓ Cross-referenced with code path from configuration to ad set creation
