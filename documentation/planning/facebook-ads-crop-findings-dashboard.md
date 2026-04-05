# Facebook Ad Templates Cropping Investigation - Findings

## Overview
This document details how the vlab dashboard client fetches ad templates from Facebook and how image data (including image_hash, image_crops, and related fields) flows through the system from Facebook API → Dashboard → Adopt Service.

## Key Finding: Missing Image Crop Data
**Critical Discovery**: While the Dashboard fetches `object_story_spec` from Facebook (which includes `image_hash`), there is **NO evidence of `image_crop` or `image_crops` fields being fetched, stored, or passed** to the adopt service. The system only stores and uses `image_hash` for template images.

---

## 1. Data Flow: Facebook API → Dashboard → Adopt Service

### 1.1 Dashboard Frontend Fetches Ads from Facebook
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/helpers/api.ts` (lines 568-613)

#### Function: `fetchAds()`
```typescript
export const fetchAds = async ({
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

  const creativeFields = [
    "id",
    "name",
    "actor_id",
    "asset_feed_spec",
    "degrees_of_freedom_spec",
    "effective_instagram_media_id",
    "effective_object_story_id",
    "instagram_user_id",
    "object_story_spec",
    "contextual_multi_ads",
    "thumbnail_url",
  ].join(",")

  const params: any = {
    limit,
    pretty: 0,
    fields: `id,name,creative{${creativeFields}}`,
    access_token: accessToken,
  };
  if (cursor) {
    params['cursor'] = cursor;
  }

  const path = `/${campaign}/ads`;

  return facebookRequest<AdsApiResponse>(path, {
    queryParams: params,
    accessToken,
    defaultErrorMessage,
  });
};
```

**GraphQL/REST API Details**:
- **Endpoint**: `GET /{campaign_id}/ads`
- **Facebook API Version**: Dynamic, loaded from `process.env.REACT_APP_FACEBOOK_API_VERSION`
- **Base URL**: `https://graph.facebook.com/{FACEBOOK_API_VERSION}` (line 439)
- **Timeout**: 10 seconds (line 443)

#### Creative Fields Requested from Facebook
The dashboard requests these fields from the Facebook `AdCreative` object:
1. `id` - Creative ID
2. `name` - Creative name
3. `actor_id` - Page/account ID
4. `asset_feed_spec` - Asset feed specification
5. `degrees_of_freedom_spec` - Creative degrees of freedom (optimization preferences)
6. `effective_instagram_media_id` - Instagram media ID
7. `effective_object_story_id` - Story ID
8. `instagram_user_id` - Instagram user ID
9. **`object_story_spec`** - Contains link_data and video_data (see below)
10. `contextual_multi_ads` - Multi-ad context
11. `thumbnail_url` - Thumbnail image URL

**Notable Absences**:
- ❌ `image_crops` is NOT requested
- ❌ `image_hash` is NOT directly requested (but comes in `object_story_spec.link_data.image_hash`)
- ❌ Individual ad crop data is not fetched

### 1.2 What Comes Back in `object_story_spec`
When the dashboard fetches ads, the `object_story_spec` contains:
- **For Link Data Ads**:
  - `link_data.image_hash` - Hash reference to the image in Facebook's system
  - `link_data.message` - Ad message/text
  - `link_data.name` - Ad name
  - `link_data.description` - Ad description
  - `link_data.call_to_action` - CTA spec
  - `link_data.page_welcome_message` - Messenger welcome message (JSON)
  - `link_data.link` - Landing page URL

- **For Video Data Ads**:
  - `video_data.image_hash` - Thumbnail image hash
  - `video_data.title` - Video title
  - `video_data.message` - Ad copy
  - `video_data.video_id` - Facebook video ID

**Example from Test Data** (`/home/nandan/Documents/vlab-research/vlab/adopt/test/ads/image_ad_enroll_status.json`):
```json
{
  "object_story_spec": {
    "link_data": {
      "image_hash": "fe6979238d15f1a037a9afd46c870f7f",
      "call_to_action": { ... },
      "page_welcome_message": "{...}",
      "link": "https://fb.com/messenger_doc/"
    },
    "page_id": "1855355231229529"
  },
  "thumbnail_url": "https://external-lga3-2.xx.fbcdn.net/emg1/v/...",
  "degrees_of_freedom_spec": { ... }
}
```

---

## 2. Template Data Structure in Dashboard

### 2.1 How Templates Are Displayed to Users
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/pages/StudyConfPage/forms/creatives/Creative.tsx` (lines 49-58)

```typescript
const handleSelectTemplate = (e: any) => {
  const { value } = e.target;
  const ad = ads.find(a => a.id === value)
  const template = ad["creative"]
  if (!!data.name) {
    return updateFormData({ ...data, template }, index)
  }
  return updateFormData({ ...data, template, name: ad.name }, index)
}
```

**What happens**:
1. User selects an ad from the campaign (dropdown in Creative.tsx)
2. The entire `creative` object from the Facebook response is stored as the `template`
3. This includes the complete `object_story_spec` with `image_hash`
4. User optionally renames the creative

### 2.2 Template Type Definition
**File**: `/home/nandan/Documents/vlab-research/vlab/dashboard/src/types/conf.ts` (lines 91-96)

```typescript
export type Creative = {
  name: string;
  destination: string;
  template: any; // TODO: create a type for facebook adcreative (stubs?)
  template_campaign: string;
};
```

**Note**: The template is typed as `any` because there's no TypeScript definition. The comment suggests this was a known TODO.

---

## 3. Template Storage in Backend (API)

### 3.1 Creative Configuration Struct
**File**: `/home/nandan/Documents/vlab-research/vlab/api/internal/types/studyconf.go` (lines 255-266)

```go
// CreativeConf these are essential fields that relate to an ad
// and link to a destination
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

**Critical Finding**: The API backend **does NOT store the full template object**. Instead, it extracts specific fields:
- ✅ `ImageHash` - Direct hash reference
- ✅ `Name` - Creative name
- ✅ `Destination` - Where users are sent
- ✅ `WelcomeMessage` - Messenger welcome message
- ✅ `Body`, `ButtonText`, `LinkText` - Ad copy elements
- ✅ `Tags` - Ad tags

❌ **Missing**: The full `object_story_spec` template and any crop data

### 3.2 Database Storage
**File**: `/home/nandu/Documents/vlab-research/vlab/api/internal/testhelpers/databasestudyconf.go`

Example stored CreativeConf:
```json
{
  "body": "Foobar",
  "button_text": "Foobar",
  "destination": "fly",
  "image_hash": "8ef11493ade6deced04f36b9e8cf3900",
  "link_text": "Foobar",
  "name": "Ad1_Recruitment",
  "welcome_message": "welcome",
  "tags": null
}
```

---

## 4. How Adopt Service Uses Templates

### 4.1 Adopt's Creative Configuration Type
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/study_conf.py` (lines ~395-401)

```python
class CreativeConf(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    destination: str
    name: str
    template: FacebookAdCreative  # Dict[str, Any]
    template_campaign: str | None = None
    tags: list[str] | None = None
```

Where:
```python
FacebookAdCreative = Dict[str, Any]
```

**Key Difference from API**: Adopt DOES store the full template as a dictionary!

### 4.2 Template Usage in Creative Creation
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py` (lines 281-374)

The `_create_creative()` function copies specific fields from the template:

```python
def _create_creative(
    config: CreativeConf,
    call_to_action: dict[str, Any],
    page_welcome_message: str | None = None,
    url_tags: str | None = None,
    link: str | None = None,
) -> AdCreative:
    c = AdCreative()

    c[AdCreative.Field.name] = config.name

    # Copy these fields from template if present
    fields_to_copy = [
        AdCreative.Field.actor_id,
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.thumbnail_url,
        AdCreative.Field.contextual_multi_ads,
    ]

    for field in fields_to_copy:
        if field in config.template:
            c[field] = config.template[field]

    # Extract link_data from template's object_story_spec
    tld = config.template["object_story_spec"].get("link_data")
    if tld:
        link_data = {
            AdCreativeLinkData.Field.call_to_action: call_to_action,
            AdCreativeLinkData.Field.image_hash: tld["image_hash"],  # ← Uses image_hash
            AdCreativeLinkData.Field.message: tld.get("message"),
            AdCreativeLinkData.Field.name: tld.get("name"),
            AdCreativeLinkData.Field.description: tld.get("description"),
        }
        # ... adds page_welcome_message and link if provided ...

    # Similar for video_data
    tvd = config.template["object_story_spec"].get("video_data")
    if tvd:
        video_data = {
            AdCreativeVideoData.Field.image_hash: tvd.get("image_hash"),  # ← Uses image_hash
            AdCreativeVideoData.Field.message: tvd.get("message"),
            # ... other fields ...
        }
```

**Critical Finding**: Adopt only uses `image_hash` from the template. It does NOT use or reference:
- ❌ `image_crops`
- ❌ `image_crop_key`
- ❌ Crop-related fields
- ❌ "191x100" references (not found anywhere in codebase)

---

## 5. Adopt Service Facebook API Calls

### 5.1 Getting Existing Ads from Facebook
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/facebook/state.py` (lines 35-55)

```python
def get_creatives(api: FacebookAdsApi, ids: List[str]) -> List[AdCreative]:
    if not ids:
        return []

    fields = [
        AdCreative.Field.actor_id,
        AdCreative.Field.image_crops,        # ← Requested here!
        AdCreative.Field.asset_feed_spec,
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.object_story_spec,
        AdCreative.Field.thumbnail_url,
        AdCreative.Field.contextual_multi_ads,
        AdCreative.Field.url_tags,
    ]

    return call(AdCreative.get_by_ids, ids=ids, fields=fields, api=api)
```

**Interesting Finding**: When Adopt loads existing ads from Facebook, it DOES request `image_crops`, but this is only used when:
- Fetching state of existing ads already running in Facebook
- **Not** when creating new ads or using templates

### 5.2 Facebook Business SDK Fields
**File**: `/home/nandan/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/adcreativelinkdata.pyi` (lines 1-48)

The Facebook Business SDK type hints show these image-related fields available on AdCreativeLinkData:
```python
class Field(AbstractObject.Field):
    image_crops: str      # Image crop specifications
    image_hash: str       # Image hash reference
    image_layer_specs: str
    image_overlay_spec: str
    # ... other fields ...
```

---

## 6. The Cropping Gap: "191x100" and crop_key

### 6.1 Search Results
**🔍 Investigation Result**: No occurrences found in the codebase of:
- ❌ `191x100` - Not found anywhere
- ❌ `crop_key` - Not found anywhere
- ❌ `image_crop` as a dedicated field - Only `image_crops` (plural) in Facebook SDK stubs
- ❌ Crop transformation logic - Not implemented

### 6.2 What This Means
The vlab system:
1. ✅ Retrieves templates from Facebook with `image_hash`
2. ✅ Stores and passes `image_hash` to Adopt
3. ✅ Adopt uses `image_hash` when creating ads
4. ❌ Does NOT handle image crops or crop specifications
5. ❌ Does NOT transform images to specific aspect ratios like 191x100
6. ❌ Relies entirely on Facebook's original image via `image_hash`

---

## 7. Complete Data Flow Diagram

```
┌─────────────────────────────────┐
│   Facebook Ad Account           │
│   (Published Ads)               │
└────────────┬────────────────────┘
             │
             │ Dashboard calls fetchAds()
             │
             ▼
┌─────────────────────────────────────────┐
│ Facebook Graph API v{VERSION}           │
│ GET /{campaign}/ads                     │
│ Fields: creative{                       │
│   id, name, actor_id,                   │
│   object_story_spec,        ← Has image_hash
│   degrees_of_freedom_spec,              │
│   ...                                   │
│ }                                       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Dashboard Frontend (React)              │
│ Creative Template Selection UI          │
│ (Creative.tsx)                          │
│                                         │
│ Stores: {                               │
│   name, destination,                    │
│   template: { entire creative object }, │
│   template_campaign                     │
│ }                                       │
└────────────┬────────────────────────────┘
             │
             │ User submits form
             │
             ▼
┌─────────────────────────────────────────┐
│ API Backend (Go)                        │
│ POST /studies/{slug}/confs/creatives    │
│                                         │
│ Extracts & stores:                      │
│ - image_hash (from template)            │
│ - name, destination                     │
│ - welcome_message, body, etc.           │
│                                         │
│ Database CreativeConf {                 │
│   ImageHash, Name, Destination, ...     │
│ }                                       │
└────────────┬────────────────────────────┘
             │
             │ Adopt loads from DB
             │
             ▼
┌─────────────────────────────────────────┐
│ Adopt Service (Python)                  │
│ CreativeConf {                          │
│   template: FacebookAdCreative,         │
│   destination, name, ...                │
│ }                                       │
│                                         │
│ Uses: image_hash from template          │
│       to create new ads via SDK         │
└─────────────────────────────────────────┘
```

---

## 8. Data Integrity Issues

### Issue 1: Template Extraction Mismatch
**Problem**: Dashboard passes full template object, but API only stores specific fields.

**Flow**:
1. Dashboard stores full `creative` object (potentially 50+ fields)
2. API receives it but only extracts 8 fields
3. Data is lost if not explicitly mapped
4. Adopt receives no template on current flow (must come from separate storage)

### Issue 2: Image Data Loss Path
- ✅ Dashboard has full `object_story_spec`
- ⚠️ API might lose this if template is not properly stored
- ⚠️ Adopt depends on template from different source

---

## 9. Facebook API Version Reference

**Current Configuration**:
- Dashboard uses: `process.env.REACT_APP_FACEBOOK_API_VERSION`
- Environment variable is set at build time
- No specific version found in example .env file
- Need to check runtime configuration to see actual version

---

## 10. Summary of Findings

| Aspect | Status | Details |
|--------|--------|---------|
| **Image Hash** | ✅ Supported | Fetched, stored, passed to Adopt |
| **Image Crops** | ❌ Not implemented | Not requested, not stored, not used |
| **crop_key** | ❌ Not found | No references in codebase |
| **191x100 dimension** | ❌ Not found | No aspect ratio handling |
| **Template Full Object** | ⚠️ Partial | Dashboard fetches full, API extracts fields |
| **Facebook API Version** | ⏳ Dynamic | Loaded from environment |
| **Data Integrity** | ⚠️ Potential gaps | Between Dashboard→API→Adopt flows |

---

## 11. Recommendations

1. **For Image Cropping Support**:
   - Add `image_crops` to API CreativeConf if crop data is needed
   - Implement crop extraction logic in API
   - Add crop field to Adopt's CreativeConf

2. **For Type Safety**:
   - Create proper TypeScript type for Facebook AdCreative (instead of `any`)
   - Document FacebookAdCreative structure in Adopt

3. **For Data Completeness**:
   - Verify whether full template should be stored in API or just metadata
   - Document the template data flow architecture decision

4. **For Debugging**:
   - Log the full creative object when stored to catch data loss
   - Add telemetry for crop field presence/absence

---

## Appendix: File Locations

| Component | File Path | Key Lines |
|-----------|-----------|-----------|
| **Dashboard Ads Fetch** | `/dashboard/src/helpers/api.ts` | 568-613 |
| **Dashboard Creative Selection** | `/dashboard/src/pages/StudyConfPage/forms/creatives/Creative.tsx` | 49-58 |
| **Dashboard Type Def** | `/dashboard/src/types/conf.ts` | 91-96 |
| **API Creative Config** | `/api/internal/types/studyconf.go` | 255-266 |
| **Adopt Creative Config** | `/adopt/adopt/study_conf.py` | ~395-401 |
| **Adopt Creative Creation** | `/adopt/adopt/marketing.py` | 281-374 |
| **Adopt Existing Ad Fetch** | `/adopt/adopt/facebook/state.py` | 35-55 |
| **Facebook SDK Types** | `/adopt/stubs/facebook_business/adobjects/adcreativelinkdata.pyi` | 1-48 |
| **Test Ad Data** | `/adopt/test/ads/image_ad_enroll_status.json` | 1-68 |

