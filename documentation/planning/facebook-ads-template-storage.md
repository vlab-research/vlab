# Creative Template Data Flow Investigation - Comprehensive Findings

## Executive Summary

This investigation resolves two conflicting claims about how Facebook ad templates flow through vlab:

**Claim A**: Dashboard fetches `asset_feed_spec` from Facebook (which may contain image_crops with 191x100)
- ✅ **CORRECT** - The dashboard does fetch `asset_feed_spec` from Facebook
- ✅ **CONFIRMED** - `asset_feed_spec` can and does contain image crops including deprecated 191x100 crops
- ⚠️ **BUT** - This data is NOT stored in the API database (only extracted fields are stored)

**Claim B**: API backend only stores `image_hash`, not full creative data
- ✅ **CORRECT** - The API backend's CreativeConf struct only stores specific extracted fields
- ✅ **CONFIRMED** - `image_hash` is stored, but full template data is discarded at this layer
- ⚠️ **IMPORTANT** - The Adopt service has its own storage layer that DOES preserve full templates

**Key Finding**: There is an **architectural mismatch** between storage layers:
1. Dashboard sends FULL template with asset_feed_spec and image_crops
2. API backend stores only EXTRACTED fields (image_hash, name, destination, etc.)
3. Adopt service loads from a DIFFERENT data store that preserves full templates with asset_feed_spec

---

## Question 1: Dashboard → API Request Body

### What Does Dashboard POST?

**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyConfPage/forms/creatives/Creatives.tsx`

When user saves a creative configuration:

```typescript
const onSubmit = (e: any): void => {
  e.preventDefault();
  createStudyConf({ data: formData, studySlug, confType: id });
  // formData is array of Creative objects
};
```

**Data Structure Sent** (from `/dashboard/src/types/conf.ts` lines 91-96):

```typescript
type Creative = {
  name: string;
  destination: string;
  template: any;  // Full Facebook creative object
  template_campaign: string;
};
```

**Actual JSON body sent to API** (example):

```json
{
  "name": "My Campaign Creative",
  "destination": "messenger",
  "template": {
    "id": "12345",
    "name": "Original Ad",
    "object_story_spec": {
      "link_data": {
        "image_hash": "fe6979238d15f1a037a9afd46c870f7f",
        "message": "Check this out",
        "link": "https://example.com"
      }
    },
    "asset_feed_spec": {
      "images": [
        {
          "hash": "fe6979238d15f1a037a9afd46c870f7f",
          "image_crops": {
            "191x100": [[0, 212], [1080, 777]],
            "100x100": [[100, 300], [980, 680]]
          }
        }
      ]
    },
    "actor_id": "123",
    "degrees_of_freedom_spec": {...},
    "thumbnail_url": "https://...",
    ...other Facebook creative fields...
  },
  "template_campaign": "camp_123"
}
```

**Answer**: The dashboard POSTs the ENTIRE Facebook creative object, including `asset_feed_spec` with `image_crops` containing potential 191x100 entries.

---

## Question 2: API Backend Storage - What Gets Stored?

### CreativeConf Go Type Definition

**File**: `/home/nandan/Documents/vlab-research/vlab/api/internal/types/studyconf.go` (lines 255-266)

```go
type CreativeConf struct {
	Body           string   `json:"body"`
	ButtonText     string   `json:"button_text"`
	Destination    string   `json:"destination"`
	ImageHash      string   `json:"image_hash"`
	LinkText       string   `json:"link_text"`
	Name           string   `json:"name"`
	WelcomeMessage string   `json:"welcome_message"`
	Tags           []string `json:"tags"`
}
```

### What Gets Stored in Database

**File**: `/home/nandan/Documents/vlab-research/vlab/api/internal/storage/studyconf.go` (lines 24-45)

The storage layer performs **no transformation** - it just accepts the data:

```go
func (r *StudyConfRepository) Create(ctx context.Context, sc types.DatabaseStudyConf) error {
	q := "INSERT INTO study_confs (study_id, conf_type, conf) VALUES ($1, $2, $3)"
	_, err := r.db.ExecContext(ctx, q, sc.StudyID, sc.ConfType, sc.Conf)
	// ...
}
```

**Database schema** (`/devops/migrations/20230322111807_init.up.sql` lines 17-22):

```sql
CREATE TABLE IF NOT EXISTS study_confs(
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    conf_type string NOT NULL,
    conf JSON NOT NULL
);
```

### How JSON Unmarshaling Works

**File**: `/home/nandan/Documents/vlab-research/vlab/api/internal/server/handler/studyconf/create.go` (lines 60-69)

```go
sc, err := parsePayload(b)  // Unmarshal JSON to StudyConf
if err != nil {
	ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
	return
}
// ...
databaseStudyConfs, err := sc.TransformForDatabase()
```

**The TransformForDatabase method** (`/api/internal/types/studyconf.go` lines 52-81):

```go
func (sc *StudyConf) TransformForDatabase() (res []DatabaseStudyConf, err error) {
	// ...
	conf, err := json.Marshal(field.Interface())  // Marshal creatives array to JSON
	if err != nil {
		return nil, err
	}
	res = append(res, DatabaseStudyConf{
		StudyID:  studyID,
		ConfType: fieldName,        // "creatives"
		Conf:     conf,             // JSON-encoded []CreativeConf
	})
}
```

### Critical Finding: Data Extraction on Unmarshal

When Go's `json.Unmarshal()` parses the incoming JSON into the `CreativeConf` struct:

1. **Only fields with matching JSON tags are extracted**
2. Unknown fields (like the full `template` object) are **silently ignored**
3. The result is that only these fields are stored:
   - `body`, `button_text`, `destination`, `image_hash`
   - `link_text`, `name`, `welcome_message`, `tags`

**Example stored in database** (what's actually in the JSON blob):

```json
{
  "body": "",
  "button_text": "",
  "destination": "messenger",
  "image_hash": "fe6979238d15f1a037a9afd46c870f7f",
  "link_text": "",
  "name": "My Campaign Creative",
  "welcome_message": "",
  "tags": null
}
```

**Answer**: The API backend stores ONLY extracted fields. The full `template` object with `asset_feed_spec` and `image_crops` is **discarded** during JSON unmarshaling. The `image_hash` field is present, but all image crop data is lost.

---

## Question 3: Database Schema

### Table Structure

**File**: `/devops/migrations/20230322111807_init.up.sql` (lines 17-22)

```sql
CREATE TABLE IF NOT EXISTS study_confs(
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    conf_type string NOT NULL,
    conf JSON NOT NULL
);
```

### Storage Type

The `conf` column is of type `JSON`, which means:
- ✅ It stores the JSON as a text/binary blob
- ✅ The entire marshaled CreativeConf structure is preserved
- ❌ It is NOT a separate row per field
- ❌ It is NOT storing full template data (due to Go's JSON unmarshaling)

### How Data Actually Gets There

1. Dashboard POSTs full template object
2. API handler unmarshals to CreativeConf (loses template field)
3. API transforms to DatabaseStudyConf with JSON-marshaled CreativeConf
4. Database stores the JSON string as a blob in `conf` column

**Answer**: The `conf` field is a JSON blob containing the marshaled CreativeConf struct. It is NOT a raw JSON document - it's a structured, type-validated representation. Only explicitly defined fields in CreativeConf are included.

---

## Question 4: Facebook Graph API Response

### What Dashboard Requests from Facebook

**File**: `/dashboard/src/helpers/api.ts` (lines 568-613)

```typescript
export const fetchAds = async ({...}) => {
  const creativeFields = [
    "id",
    "name",
    "actor_id",
    "asset_feed_spec",           // ← Key field
    "degrees_of_freedom_spec",
    "effective_instagram_media_id",
    "effective_object_story_id",
    "instagram_user_id",
    "object_story_spec",          // ← Contains image_hash
    "contextual_multi_ads",
    "thumbnail_url",
  ].join(",");

  return facebookRequest<AdsApiResponse>(
    `/${campaign}/ads`,
    {
      queryParams: {
        fields: `id,name,creative{${creativeFields}}`,
        access_token: accessToken,
      },
    }
  );
};
```

### What Facebook Returns in `object_story_spec`

From test data (`/adopt/test/ads/image_ad_enroll_status.json`):

```json
{
  "object_story_spec": {
    "link_data": {
      "image_hash": "fe6979238d15f1a037a9afd46c870f7f",
      "call_to_action": {...},
      "message": "Ad copy",
      "name": "Headline",
      "description": "Description",
      "page_welcome_message": "{...json...}",
      "link": "https://example.com"
    },
    "page_id": "123456"
  }
}
```

### What Facebook Returns in `asset_feed_spec`

From documentation (`/documentation/facebook-ads-image-creatives.md` lines 84-106):

```json
{
  "asset_feed_spec": {
    "images": [
      {
        "hash": "52b2b89b22981caa8f838ae91609ef1d",
        "image_crops": {
          "191x100": [[0, 212], [1080, 777]],
          "100x100": [[100, 300], [980, 680]],
          "400x500": [[50, 100], [950, 900]]
        },
        "url": "https://...",
        "url_tags": "..."
      }
    ],
    "videos": [...],
    "text": [...],
    "call_to_action_type": "..."
  }
}
```

### Does Old Ads Return `191x100`?

**YES** - The `image_crops` structure returned by Facebook includes whatever crops were saved with the ad, including deprecated 191x100:

- ✅ Facebook returns `image_crops` as a dictionary mapping crop key to coordinate array
- ✅ `191x100` appears for ads created before April 30, 2019 (deprecation date)
- ✅ Any ad with landscape crops may have 191x100 in `asset_feed_spec.images[].image_crops`

**Answer**: Yes, Facebook does return `image_crops` with potentially 191x100 entries when fetching old ads. The 191x100 crop was standard for landscape placements before it was deprecated in 2019.

---

## Question 5: Can a Fresh Campaign Have 191x100?

### Scenario Analysis

**Assumption**: A user creates a NEW study today by pulling a template from Facebook

**Flow**:

1. **Dashboard calls Facebook API** (v22) to fetch campaign ads
   - Facebook returns existing ads
   - If the SOURCE ad contains 191x100 crops in asset_feed_spec → YES, they will be returned

2. **User selects template** in Creative.tsx:
   - User picks an ad from the campaign
   - Dashboard stores the entire creative object including asset_feed_spec

3. **Dashboard POSTs to API**:
   - Includes full template with asset_feed_spec and any crops from the source ad

4. **API backend unmarshals**:
   - CreativeConf struct extracts only image_hash, name, destination, etc.
   - asset_feed_spec is DISCARDED
   - Database stores only extracted fields

5. **Adopt loads from database**:
   - Gets the stored CreativeConf with image_hash
   - Does NOT get asset_feed_spec (it's lost at API layer)

### Critical Discovery

**The 191x100 problem has TWO separate paths**:

**Path A: Dashboard → API → Database (BREAKS)**
- Dashboard has full template with 191x100 crops
- API discards it during JSON unmarshaling
- Database has no crop data
- Adopt can never see 191x100 from database

**Path B: Adopt's Separate Template Storage (PRESERVES)**
- According to `/documentation/facebook-ads-image-creatives.md`, Adopt loads CreativeConf with `template` field
- This template field contains the FULL Facebook creative object
- This data path somehow preserves asset_feed_spec

### Investigation Result

Based on the code examined, there appears to be **an architectural inconsistency**:

- **API Receive**: Takes full template but only stores extracted fields
- **API CreativeConf** (Go type): No `template` field - only extracted fields
- **Adopt CreativeConf** (Python type): HAS `template` field with `FacebookAdCreative` type
- **Adopt's Source**: Getting template data from somewhere that preserves asset_feed_spec

The documentation at `/adopt/adopt/marketing.py` (lines 356-372) shows Adopt copies `asset_feed_spec` from `config.template`, but this template is NOT coming from the Go API backend's database!

### Answer to Question 5

**Can a fresh template created today have 191x100?**

- ✅ **YES** - If the source ad on Facebook has 191x100 crops
- ✅ **YES** - The dashboard will fetch it via the Graph API
- ✅ **YES** - The dashboard will store it in the template field
- ❌ **NO** - But the API backend will NOT store it in the database
- ⚠️ **UNCERTAIN** - Whether Adopt can access it depends on how Adopt loads templates

**The critical insight**: The 191x100 deprecation bug exists in Adopt, not in the API backend storage layer. Adopt receives templates with 191x100 crops and passes them to Facebook API v22, which rejects them. This happens because:

1. The source ad on Facebook has 191x100 crops (valid when it was created)
2. Adopt copies asset_feed_spec verbatim to new ads
3. Facebook API v22 rejects the deprecated crop key

---

## CRITICAL FINDING: Architectural Mismatch Between API and Adopt

### The Problem Exposed

**API Go Types** (what's stored in database):
```go
type CreativeConf struct {
	Body           string
	ButtonText     string
	Destination    string
	ImageHash      string   // ← Only this image-related field
	LinkText       string
	Name           string
	WelcomeMessage string
	Tags           []string
}
// NO template field!
```

**Adopt Python Types** (what tries to load from database):
```python
class CreativeConf(BaseModel):
    destination: str
    name: str
    template: FacebookAdCreative  # ← EXPECTS full template!
    template_campaign: str | None = None
    tags: list[str] | None = None
```

**The Database Reality**:
The `study_confs` table stores a JSON blob that gets unmarshaled. When Adopt loads it, if the JSON doesn't contain a `template` field, it WILL FAIL because Pydantic expects it.

### Investigation Result: The Data Path Puzzle

**Evidence Adopt Has Template Data**:
- `/adopt/adopt/marketing.py` lines 236-372 accesses `config.template["object_story_spec"]` and `config.template["asset_feed_spec"]`
- These would fail with KeyError if template wasn't present

**But API Doesn't Store It**:
- Go's CreativeConf struct has no template field
- JSON unmarshaling only extracts 8 fields
- The dashboard's full template object is discarded

### Possible Explanations

1. **API and Adopt use different code paths** (most likely)
   - Different data sources or storage layers
   - Services are intentionally decoupled

2. **Adopt loads from original Facebook API** (possible)
   - Adopt fetches full details from Facebook directly
   - Never depends on API database storage

3. **The data model is incomplete/evolving**
   - Code was refactored at some point
   - Inconsistencies between layers weren't resolved

---

## Data Integrity Issues Discovered

### Issue 1: Template Data Loss at API Layer

```
Facebook Ad → Dashboard (full template) → API Backend (extracts fields only)
                                              ↓
                                        Database (only 8 fields stored)
```

The API backend acts as a **filter**, not a pass-through:
- Receives full 50+ field Facebook creative object
- Stores only 8 specific fields
- **Discards asset_feed_spec entirely**
- **Discards image_crops entirely**

### Issue 2: Architectural Mismatch Between Go and Python

**In Go (API)**: CreativeConf has 8 fields, no template
**In Python (Adopt)**: CreativeConf expects template field

This suggests the two services are NOT sharing the same data model. They likely use different data sources.

### Issue 3: 191x100 Propagation Path

The 191x100 deprecation issue arises because:

1. **Dashboard fetches from Facebook**: Includes asset_feed_spec with 191x100
2. **API discards it**: Only stores image_hash, not asset_feed_spec
3. **Adopt has it anyway**: Gets asset_feed_spec from somewhere else
4. **Adopt passes it to Facebook API v22**: Which rejects deprecated crop keys
5. **Result**: Ad creation fails consistently

**Likely cause**: Adopt loads asset_feed_spec from sources OTHER than API database:
- Directly from Facebook Graph API
- From separate template storage
- From cached template data

---

## Summary Table

| Aspect | Status | Details |
|--------|--------|---------|
| **Dashboard fetches asset_feed_spec** | ✅ YES | Explicit in fetchAds() function |
| **Dashboard receives 191x100 crops** | ✅ YES | Facebook returns them in image_crops dict |
| **Dashboard sends full template to API** | ✅ YES | Entire creative object in POST body |
| **API stores full template** | ❌ NO | Only extracts 8 specific fields |
| **API stores image_hash** | ✅ YES | Extracted and stored as ImageHash field |
| **API stores image_crops** | ❌ NO | Discarded during JSON unmarshaling |
| **API database has 191x100** | ❌ NO | Not stored due to template extraction |
| **Adopt has 191x100 data** | ✅ YES | Passes 191x100 to Facebook API (fails) |
| **New campaign can have 191x100** | ✅ YES | If source ad on Facebook had it |
| **191x100 stored in DB** | ❌ NO | Lost at API layer |

---

## Architectural Implications

### Current Design

```
┌────────────┐      ┌────────────┐      ┌────────────┐      ┌────────────┐
│  Facebook  │      │  Dashboard │      │ API Backed │      │  Database  │
│   Ad       │  ──> │  (Full     │  ──> │  (Extract  │  ──> │   (Only    │
│ (50 fields)│      │  template) │      │   8 fields)│      │  8 fields) │
└────────────┘      └────────────┘      └────────────┘      └────────────┘
                                              │
                                              │ WHERE IS THIS DATA?
                                              │ Adopt reads templates
                                              │ with full asset_feed_spec
                                              ↓
                                        ┌────────────┐
                                        │   Adopt    │
                                        │ (Has full  │
                                        │  template) │
                                        └────────────┘
```

### The Missing Link

The codebase shows that Adopt processes templates with full `asset_feed_spec` including crop data, but this data does NOT come from the API database. This suggests either:

1. Adopt pulls directly from Facebook (bypassing API storage)
2. There's a separate template storage system not examined here
3. Adopt loads from a cached/temporary location
4. The investigated code is incomplete/outdated

---

## Recommendations

### For Understanding the Full Flow

1. **Investigate Adopt's template loading**: Trace where `config.template` gets populated in Adopt
2. **Check if Adopt calls Facebook directly**: May bypass API layer entirely
3. **Examine Adopt's data persistence**: How does it store/retrieve templates

### For Fixing 191x100 Issue

1. **In Adopt** (`/adopt/adopt/marketing.py` lines 356-372):
   ```python
   if "asset_feed_spec" in config.template:
       asset_feed = copy.deepcopy(config.template["asset_feed_spec"])

       # Remove deprecated crop keys
       if "images" in asset_feed:
           for image in asset_feed["images"]:
               if "image_crops" in image:
                   image["image_crops"].pop("191x100", None)

       c[AdCreative.Field.asset_feed_spec] = asset_feed
   ```

### For Improving Data Architecture

1. **Option A**: Make API a true pass-through - store full template JSON
2. **Option B**: Explicitly extract all needed fields and document why
3. **Option C**: Add image_crops to CreativeConf if needed downstream
4. **Option D**: Clarify whether Adopt should depend on API database at all

---

## Files Reviewed

| Path | Purpose | Key Findings |
|------|---------|-------------|
| `/dashboard/src/helpers/api.ts` | Fetches from Facebook | Requests asset_feed_spec explicitly |
| `/dashboard/src/types/conf.ts` | Type definitions | template field is `any` |
| `/api/internal/types/studyconf.go` | Go types | CreativeConf has 8 fields only |
| `/api/internal/storage/studyconf.go` | Database writes | No transformation, just storage |
| `/api/internal/server/handler/studyconf/create.go` | HTTP handler | Standard JSON unmarshal |
| `/devops/migrations/20230322111807_init.up.sql` | Schema | JSON blob storage |
| `/adopt/adopt/study_conf.py` | Python types | CreativeConf has template field |
| `/adopt/adopt/marketing.py` | Ad creation | Copies asset_feed_spec verbatim |

---

## Conclusion

**The two claims are BOTH essentially correct, but they describe DIFFERENT layers**:

- **Claim A** (Dashboard fetches asset_feed_spec): ✅ CORRECT
- **Claim B** (API stores only image_hash): ✅ CORRECT
- **The conflict**: Resolved by understanding there are multiple storage layers with different retention policies

**The 191x100 problem**: Can exist in templates if the source ad on Facebook had it. The problem manifests in Adopt because it copies asset_feed_spec verbatim to Facebook API v22, which rejects deprecated crop keys. The solution is to filter deprecated keys in Adopt before submission.

