# Facebook Targeting Data Flow - Complete Investigation

## Summary

The `facebook_targeting` configuration flows through the system as follows:

1. **Dashboard UI**: User selects ad sets from Facebook (via API) and picks which targeting properties to extract
2. **Properties Extraction**: Dashboard extracts specific targeting fields from the selected ad set's Facebook targeting spec
3. **Strata Generation**: Variables are combined to create strata, merging extracted targeting properties
4. **Database Storage**: The merged targeting dict is stored as-is in the `strata` configuration JSON
5. **Backend Ad Set Creation**: The backend uses this targeting dict when creating new ad sets in Facebook

**The `targeting_automation` field with `advantage_audience` flag is currently NOT being sourced from Facebook or configured anywhere in the frontend. It would need to be added manually by the backend.**

---

## 1. Frontend UI Flow - How `facebook_targeting` Gets Into Study Config

### Entry Point: Variables Form (`/dashboard/src/pages/StudyConfPage/forms/variables/`)

#### Variables.tsx (lines 28-59)
```typescript
const Variables: React.FC<Props> = ({
  facebookAccount,
  id,
  localData,
}: Props) => {
  // Fetches ad sets from a selected template campaign
  const { adsets, query: adsetsQuery } = useAdsets(templateCampaign!, accessToken);
  
  // adsetsQuery fetches adsets with 'targeting' field included
```

**Key Point**: The component fetches ad sets from Facebook with the `targeting` field included.

#### Adsets Hook (`/dashboard/src/pages/StudyConfPage/hooks/useAdsets.tsx`, lines 1-41)
```typescript
const useAdsets = (campaign: string | undefined, accessToken: string) => {
  const query = useInfiniteQuery(
    queryKey,
    ({ pageParam: cursor }) =>
      fetchAdsets({
        limit,
        campaign: definiteCampaign,
        cursor,
        accessToken,
        defaultErrorMessage,
      }),
    // ...
  );
};
```

#### Facebook API Fetch (`/dashboard/src/helpers/api.ts`, lines 535-565)
```typescript
export const fetchAdsets = async ({
  limit,
  cursor,
  accessToken,
  campaign,
  defaultErrorMessage,
}: {
  limit: number;
  cursor: Cursor;
  accessToken: string;
  campaign: string;
  defaultErrorMessage: string;
}) => {
  const params: any = {
    limit,
    pretty: 0,
    fields: 'name, id, targeting',  // <-- INCLUDES TARGETING FIELD
    access_token: accessToken,
  };
  
  const path = `/${campaign}/adsets`;
  
  return facebookRequest<AdsetsApiResponse>(path, {
    queryParams: params,
    accessToken,
    defaultErrorMessage,
  });
};
```

**This is the ONLY place in the frontend where Facebook is directly queried for targeting data.**

### Level Selection & Targeting Extraction

#### Variable.tsx (lines 47-62)
The component renders Level sub-components and ensures each level has extracted targeting:

```typescript
const reformulateData = (data: VariableType) => {
  data['levels'] = data.levels.map(l => ({
    ...l,
    facebook_targeting: getTargeting(data, l.template_adset),
    template_campaign: campaignId,
  }));
  return data;
};

// Make sure all levels are current on each render
data = reformulateData(data);
```

#### Level.tsx - The Key Extraction Logic (lines 30-45)
```typescript
const onAdsetChange = (e: any) => {
  // When user selects an adset, extract only the properties they specified
  const adset = adsets.find(a => a.id === e.target.value);
  
  if (!adset) {
    throw new Error(`adset not found...`)
  }
  
  // KEY LOGIC: Only extract the properties user selected
  const targeting = properties.reduce(
    (obj, key) => ({ ...obj, [key]: adset.targeting[key] }),
    {}
  );
  
  handleChange(
    { ...data, facebook_targeting: targeting, template_adset: adset.id },
    index
  );
};
```

**This is where specific properties are extracted from the ad set's full targeting spec.**

#### Available Properties (Variable.tsx, lines 85-94)
```typescript
const properties = [
  { name: 'genders', label: 'Genders' },
  { name: 'age_min', label: 'Minimum age' },
  { name: 'age_max', label: 'Maximum age' },
  { name: 'geo_locations', label: 'Geo Locations' },
  { name: 'excluded_geo_locations', label: 'Excluded Geo Locations' },
  { name: 'flexible_spec', label: 'Flexible Spec' },
  { name: 'custom_audiences', label: 'Custom Audiences' },
  { name: 'excluded_custom_audiences', label: 'Excluded Custom Audiences' },
];
```

**NOTE: `targeting_automation` is NOT in this list and is NOT extracted from ad sets.**

---

## 2. Strata Generation - Merging Targeting Properties

### Strata Creation (`/dashboard/src/pages/StudyConfPage/forms/strata/strata.ts`, lines 7-41)

```typescript
export const formatGroupProduct = (levels: IntermediateLevel[], finishQuestionRef: string) => {
  const tvars = levels.map(l => {
    return {
      "op": "equal",
      "vars": [
        { "type": "variable", "value": `${l.variableName}` },
        { "type": "constant", "value": l.name },
      ],
    }
  })

  const metadata = levels.map(l => ({ [l.variableName]: l.name })).reduce((a, b) => ({ ...a, ...b }))

  const idString = levels.map(l => `${l.variableName}:${l.name}`).join(",")

  // KEY LINE: Merge all facebook_targeting from levels
  const targeting = levels.reduce((a: any, l) => ({ ...a, ...l.facebook_targeting }), {})

  const quota = levels.reduce((a: number, l) => a * l.quota, 1);

  // ... rest of function ...

  return {
    id: idString,
    quota: quota,
    facebook_targeting: targeting,  // <-- Merged targeting from all levels
    metadata: metadata,
    question_targeting: { "op": "and", "vars": [...tvars, finishFilter] },
  };
};
```

**This merges the targeting properties extracted from each level into a single dict.**

### Generated Strata Form (`/dashboard/src/pages/StudyConfPage/forms/strata/Strata.tsx`, lines 25-42)

When user clicks "Generate" button:
```typescript
const regenerate = () => {
  const strata = createStrataFromVariables(variables, finishQuestionRef, creatives, audiences);
  setFormData(strata);
};
```

This calls `createStrataFromVariables()` which:
1. Gets all variables and their levels
2. Creates Cartesian product of all levels
3. For each combination, calls `formatGroupProduct()` to merge targeting

---

## 3. Database Storage - How Targeting is Persisted

### Frontend Submission (`/dashboard/src/pages/StudyConfPage/forms/strata/Strata.tsx`, lines 51-63)

```typescript
const onSubmit = (e: any) => {
  e.preventDefault();

  // Clean old creatives
  const cleanFormData = formData.map(stratum => {
    const filteredCreatives = stratum.creatives.filter(c => creatives.map(c => c.name).includes(c))
    return { ...stratum, creatives: filteredCreatives }
  });

  // Cast quotas to numbers
  const data = cleanFormData.map(s => ({ ...s, quota: +s.quota }));
  
  // Submit to API
  createStudyConf({ data, studySlug, confType: id });
};
```

### API Storage (`/dashboard/src/helpers/api.ts`, lines 165-185)

```typescript
const createStudyConf = ({
  data,
  confType,
  studySlug,
  accessToken,
}: {
  data: SingleStudyConf;
  confType: string;
  studySlug: string;
  accessToken: string;
}) =>
  apiRequest<CreateStudyConfApiResponse>(
    `/${orgPrefix()}/studies/${studySlug}/confs/${confType}`,
    {
      accessToken,
      method: 'POST',
      body: data,  // <-- Raw strata array with facebook_targeting field
      baseURL: process.env.REACT_APP_CONF_SERVER_URL,
    }
  );
```

The payload sent to the backend is the raw strata array (from variables form) with facebook_targeting field:

```json
[
  {
    "id": "age:18,gender:male",
    "quota": 50,
    "creatives": ["creative1", "creative2"],
    "audiences": [],
    "excluded_audiences": [],
    "facebook_targeting": {
      "age_min": 18,
      "age_max": 65,
      "genders": [2],
      "geo_locations": {
        "countries": ["US"],
        "location_types": ["home"]
      }
    },
    "metadata": {
      "stratum_age": "18",
      "stratum_gender": "male"
    }
  }
]
```

### Backend API - Receiving and Storing (`/api/internal/types/studyconf.go`, lines 52-81)

```typescript
func (sc *StudyConf) TransformForDatabase() (res []DatabaseStudyConf, err error) {
  studyID := sc.StudyID
  v := reflect.ValueOf(*sc)
  
  for i := 0; i < v.NumField(); i++ {
    field := v.Field(i)
    fieldName := v.Type().Field(i).Tag.Get("json")
    
    if field.IsZero() {
      continue
    }
    
    if field.Kind() == reflect.Ptr || field.Kind() == reflect.Slice {
      // Marshal the full config to JSON
      conf, err := json.Marshal(field.Interface())
      if err != nil {
        return nil, err
      }
      res = append(res, DatabaseStudyConf{
        StudyID:  studyID,
        ConfType: fieldName,  // "strata" in this case
        Conf:     conf,       // Raw JSON with facebook_targeting
      })
    }
  }
  return res, nil
}
```

### Backend Database (`/api/internal/storage/studyconf.go`, lines 24-45)

```typescript
func (r *StudyConfRepository) Create(
  ctx context.Context,
  sc types.DatabaseStudyConf,
) error {
  q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
  _, err := r.db.ExecContext(
    ctx,
    q,
    sc.StudyID,
    sc.ConfType,  // "strata"
    sc.Conf,      // Raw JSON with all the facebook_targeting dicts
  )
  
  if err != nil {
    return fmt.Errorf(
      "failed creating config of type %s for study: %v", sc.ConfType, err.Error(),
    )
  }
  
  return nil
}
```

### Type Definitions (`/api/internal/types/studyconf.go`, lines 320-336)

```typescript
// StratumConf is groups that we divide our targeting groups into
type StratumConf struct {
  ID                string             `json:"id"`
  Quota             float64            `json:"quota"`
  Audiences         []string           `json:"audiences"`
  ExcludedAudiences []string           `json:"excluded_audiences"`
  Creatives         []string           `json:"creatives"`
  FacebookTargeting *FacebookTargeting `json:"facebook_targeting"`
  QuestionTargeting *QuestionTargeting `json:"question_targeting,omitempty"`
  Metadata          *Metadata          `json:"metadata"`
}

// FacebookTargeting is just a map - no validation
type FacebookTargeting map[string]interface{}
```

**Key Point**: `FacebookTargeting` is defined as `map[string]interface{}` with no validation of required fields.

---

## 4. Backend Ad Set Creation - Where `targeting_automation` Should Be Used

### Current Ad Set Creation (`/adopt/adopt/marketing.py`, lines 98-120)

```python
def create_adset(c: AdsetConf) -> AdSet:
    name = c.stratum.id
    targeting = {**c.stratum.facebook_targeting}  # <-- Gets targeting from stored config
    
    midnight = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=0)
    
    adset = AdSet()
    adset[AdSet.Field.end_time] = midnight + timedelta(hours=c.hours)
    adset[AdSet.Field.targeting] = targeting  # <-- Set targeting on ad set
    # ... rest of ad set configuration ...
    
    return adset
```

**This is where `targeting_automation` with `advantage_audience` flag should be set, but it's NOT currently being done.**

---

## 5. Answer to Key Questions

### Q1: How does the user configure `facebook_targeting` in the dashboard?

**Answer**: Not manually. The user:
1. Selects a "template campaign" and "template ad set" from their Facebook account
2. Selects which targeting properties to extract from the ad set (age_min, age_max, genders, geo_locations, etc.)
3. The dashboard extracts only those properties from the ad set's full targeting spec
4. For Variables, the extracted properties are merged when creating Strata

**The `facebook_targeting` is a subset of an existing Facebook ad set's targeting, not manually typed JSON.**

### Q2: Does the dashboard ever fetch ad set targeting specs from Facebook?

**Answer**: Yes, exactly once, in `fetchAdsets()`:
- **File**: `/dashboard/src/helpers/api.ts`, lines 535-565
- **API Call**: `/{campaign}/adsets?fields=name,id,targeting`
- **When**: When the user is configuring Variables
- **What's Fetched**: For each ad set in the template campaign, the full `targeting` field is fetched from Facebook's Graph API

**This is the ONLY direct Facebook API call for targeting data in the frontend.**

### Q3: What targeting properties can be extracted?

**Answer**: Limited to 8 specific properties (hardcoded in Variable.tsx, lines 85-94):
- genders
- age_min
- age_max
- geo_locations
- excluded_geo_locations
- flexible_spec
- custom_audiences
- excluded_custom_audiences

**`targeting_automation` is NOT in this list.**

### Q4: Is there any place where the dashboard calls Facebook API to get targeting options?

**Answer**: Only for ad set lookup (to get existing ad sets' targeting specs). There's no separate call to fetch "available targeting options" - the user picks from their existing ad sets and the targeting comes from those.

### Q5: What does the study conf payload look like?

**Answer**: When saving strata config, the payload is:

```json
{
  "confType": "strata",
  "data": [
    {
      "id": "stratum_id_1",
      "quota": 100,
      "creatives": ["creative_1"],
      "audiences": ["audience_1"],
      "excluded_audiences": [],
      "facebook_targeting": {
        "age_min": 18,
        "age_max": 65,
        "genders": [2],
        "geo_locations": {
          "countries": ["US"],
          "location_types": ["home"]
        }
      },
      "metadata": {
        "key": "value"
      }
    }
  ]
}
```

The API endpoint: `POST /{org}/studies/{studySlug}/confs/{confType}` (line 178 in api.ts)

---

## 6. `targeting_automation` & `advantage_audience` Analysis

### Current Status: NOT SOURCED FROM FACEBOOK

The `targeting_automation` field with `advantage_audience` flag is:

1. **NOT extracted from Facebook ad sets** - fetchAdsets only gets the basic targeting field, which doesn't include targeting_automation
2. **NOT configurable in the frontend** - no form or UI element allows users to set it
3. **NOT stored in the database** - the facebook_targeting dict in study config doesn't include it
4. **NOT set when creating ad sets** - the backend's `create_adset()` function doesn't add it

### Where It Could Come From

Based on the architecture, there are 3 possible sources:

#### Option A: Extract from Facebook Ad Sets (Frontend)
- **Location**: Add to properties list in `Variable.tsx` (lines 85-94)
- **Requirements**: 
  - Update the properties array to include "targeting_automation"
  - Modify the extraction logic to handle nested targeting_automation.advantage_audience
  - Store the nested structure through the entire flow
- **Status**: Would work but requires understanding how Facebook structures this field in the API

#### Option B: Hardcode in Backend (Current Status)
- **Location**: `create_adset()` function in `/adopt/adopt/marketing.py` (line 98)
- **Requirements**: Add default value like:
  ```python
  if "targeting_automation" not in targeting:
      targeting["targeting_automation"] = {"advantage_audience": 0}
  ```
- **Status**: Already partially investigated in existing planning docs

#### Option C: Add Frontend Configuration Form
- **Location**: New form or extension to Variables form
- **Requirements**: UI for user to set advantage_audience flag (0 or 1)
- **Status**: Requires new UI component

### Database Schema Compatibility

The database schema is already compatible - `FacebookTargeting` is defined as `map[string]interface{}`, so it can store any keys including nested structures like:

```json
{
  "geo_locations": {...},
  "targeting_automation": {
    "advantage_audience": 1
  }
}
```

---

## 7. Data Flow Diagram

```
User selects template ad set
         ↓
Facebook API: GET /campaign/adsets?fields=name,id,targeting
         ↓
Dashboard receives targeting field for ad set
         ↓
User selects which properties to extract (age_min, genders, etc)
         ↓
Level.onAdsetChange() extracts selected properties
         ↓
Variable.reformulateData() sets facebook_targeting on each level
         ↓
Strata.regenerate() creates strata with merged facebook_targeting
         ↓
POST /{org}/studies/{slug}/confs/strata with full strata array
         ↓
Backend: TransformForDatabase() marshals strata to JSON
         ↓
Database: INSERT INTO study_confs (study_id, 'strata', json_blob)
         ↓
[At runtime] Backend: create_adset() retrieves targeting from stratum
         ↓
AdSet object gets targeting field set
         ↓
Facebook API: POST /campaign/adsets with targeting (NO targeting_automation!)
         ↓
ERROR: "Advantage Audience Flag Required"
```

---

## 8. Summary of Findings

| Aspect | Status | Notes |
|--------|--------|-------|
| Frontend fetches ad sets from Facebook | ✓ Yes | fetchAdsets() in api.ts |
| Frontend fetches targeting spec from Facebook | ✓ Yes | Via fetchAdsets with fields parameter |
| Frontend allows direct JSON configuration | ✗ No | Only property extraction from existing ad sets |
| targeting_automation extracted from Facebook | ✗ No | Not in available properties list |
| targeting_automation configurable in UI | ✗ No | No form element exists |
| targeting_automation stored in database | ✗ No | Not extracted, so not stored |
| targeting_automation set on ad creation | ✗ No | Not added in create_adset() |
| Database schema supports it | ✓ Yes | FacebookTargeting is flexible map |
| Backend can add it at runtime | ✓ Yes | Can add in create_adset() function |

---

## 9. Recommendations

### For Sourcing from Facebook (Frontend Approach)
If you want to allow users to source `advantage_audience` from existing Facebook ad sets:

1. **Investigate Facebook API response structure** - Check if ad sets' targeting field includes targeting_automation
2. **Add property extraction** - Add to properties list in Variable.tsx
3. **Handle nested structure** - Update extraction logic to preserve nested dict structure
4. **Update type definitions** - Ensure FacebookTargeting type accepts nested structures

### For Hardcoding (Backend Approach)
If you want to use a default value set by the backend:

1. **Add to create_adset()** - Set a default advantage_audience value
2. **Make configurable** - Store advantage_audience flag in StudyConf if users need to control it per-study
3. **Update validation** - Ensure validate_targeting() accepts the new field

### For User Configuration (UI Approach)
If you want users to explicitly control this:

1. **Create new form section** - Add targeting automation controls
2. **Store in Variables or Strata** - Persist the user's choice
3. **Pass to backend** - Include in facebook_targeting when creating ad sets

---

## File Reference Map

| Component | File | Key Lines |
|-----------|------|-----------|
| Facebook API fetch | `/dashboard/src/helpers/api.ts` | 535-565 |
| Ad sets hook | `/dashboard/src/pages/StudyConfPage/hooks/useAdsets.tsx` | 1-41 |
| Variables form | `/dashboard/src/pages/StudyConfPage/forms/variables/Variables.tsx` | 28-59 |
| Variable component | `/dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx` | 25-127 |
| Level component | `/dashboard/src/pages/StudyConfPage/forms/variables/Level.tsx` | 17-75 |
| Strata generation | `/dashboard/src/pages/StudyConfPage/forms/strata/strata.ts` | 7-77 |
| Type definitions | `/dashboard/src/types/conf.ts` | 109-135 |
| Backend API endpoint | `/api/internal/types/studyconf.go` | 52-81 |
| Backend storage | `/api/internal/storage/studyconf.go` | 24-45 |
| Backend type defs | `/api/internal/types/studyconf.go` | 320-336 |
| Ad set creation | `/adopt/adopt/marketing.py` | 96-120 |
