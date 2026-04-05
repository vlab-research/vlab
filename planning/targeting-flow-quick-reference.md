# Facebook Targeting Flow - Quick Reference

## Q: How does `facebook_targeting` get into the study configuration?

**A**: Via ad set selection and property extraction in the frontend Variables form, not manual JSON input.

## The Flow (5 Steps)

### 1. Dashboard Fetches Ad Sets from Facebook
- **Component**: `Variables.tsx` component with `useAdsets` hook
- **API Call**: `fetchAdsets()` in `/dashboard/src/helpers/api.ts`
- **What's Fetched**: `/{campaign}/adsets?fields=name,id,targeting`
- **Result**: List of ad sets with their full `targeting` field

### 2. User Selects Properties to Extract
- **Component**: `Variable.tsx` component
- **Hardcoded Options** (8 total):
  - genders
  - age_min / age_max
  - geo_locations / excluded_geo_locations
  - flexible_spec
  - custom_audiences / excluded_custom_audiences
- **File**: `/dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx`, lines 85-94

### 3. Level Component Extracts Selected Properties
- **Component**: `Level.tsx`, lines 30-45
- **Logic**: `targeting = properties.reduce((obj, key) => ({ ...obj, [key]: adset.targeting[key] }), {})`
- **Result**: Only selected properties extracted from ad set into Level's `facebook_targeting`

### 4. Strata Generation Merges All Targeting
- **Function**: `createStrataFromVariables()` → `formatGroupProduct()`
- **File**: `/dashboard/src/pages/StudyConfPage/forms/strata/strata.ts`, line 23
- **Logic**: `const targeting = levels.reduce((a: any, l) => ({ ...a, ...l.facebook_targeting }), {})`
- **Result**: All level targeting merged into single stratum's `facebook_targeting`

### 5. Submit to Backend API
- **Endpoint**: `POST /{org}/studies/{slug}/confs/strata`
- **File**: `/dashboard/src/helpers/api.ts`, line 181
- **Payload**: Array of strata with merged `facebook_targeting` dicts

## Storage Flow

```
Frontend (Strata Array)
    ↓
API (createStudyConf)
    ↓
Backend (TransformForDatabase)
    ↓
Database (study_confs table)
    ↓
Targeting stored as JSON: {"age_min": 18, "genders": [2], ...}
```

## Important: What's NOT Being Done

- `targeting_automation` is **NOT** extracted from Facebook ad sets
- No direct form for manual targeting configuration
- `advantage_audience` flag is **NOT** being set anywhere
- Frontend only passes through what's extracted; backend must add required fields

## Database Schema

**Table**: `study_confs`
**Columns**: `study_id`, `conf_type`, `conf` (JSON), `created`
**Storage**: Raw JSON blob (no schema validation)

Example entry:
```json
{
  "conf_type": "strata",
  "conf": [
    {
      "id": "stratum_1",
      "facebook_targeting": {
        "age_min": 18,
        "genders": [2],
        "geo_locations": {"countries": ["US"]}
      }
    }
  ]
}
```

## Possible Sources for `targeting_automation`

| Source | Status | Effort | Notes |
|--------|--------|--------|-------|
| Extract from Facebook | Not Done | Medium | Would need to add property, handle nested structure |
| Hardcode in Backend | Not Done | Low | Just add in `create_adset()` |
| User Config Form | Not Done | High | Need new UI |

## Key Files

| Purpose | File | Key Lines |
|---------|------|-----------|
| FB API Fetch | `/dashboard/src/helpers/api.ts` | 535-565 |
| Variables Form | `/dashboard/src/pages/StudyConfPage/forms/variables/Variables.tsx` | 28-59 |
| Level Extraction | `/dashboard/src/pages/StudyConfPage/forms/variables/Level.tsx` | 30-45 |
| Strata Merge | `/dashboard/src/pages/StudyConfPage/forms/strata/strata.ts` | 23 |
| Properties List | `/dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx` | 85-94 |
| API Endpoint | `/dashboard/src/helpers/api.ts` | 165-185 |
| Backend Storage | `/api/internal/storage/studyconf.go` | 24-45 |
| Ad Set Creation | `/adopt/adopt/marketing.py` | 96-120 |

## For More Details

See `/planning/advantage-audience-targeting-source.md` for:
- Complete data flow diagram
- Code examples with context
- Detailed recommendations for each approach
- Type definitions and schema validation details
