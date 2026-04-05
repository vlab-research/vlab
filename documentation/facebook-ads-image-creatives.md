# Facebook Ads Image Creatives: System Flow and Implementation Guide

## 1. Overview

Image ad creatives in vlab flow through the entire system via a multi-stage pipeline:

1. **Facebook**: Existing ads with image_hash and crop specifications
2. **Dashboard**: UI fetches and displays templates for selection
3. **API Backend**: Receives and validates creative templates
4. **Database**: Stores template configurations in `study_confs` table
5. **Adopt Service**: Loads templates and creates new ads via Facebook API
6. **Facebook**: New ads published with specified image creatives

This document provides a complete reference for understanding image creative handling and the critical deprecation issue around the `191x100` crop key.

---

## 2. Ad Template Pull (Dashboard)

### 2.1 Facebook Graph API Request

**Location**: `/dashboard/src/helpers/api.ts`, lines 568-613

The dashboard fetches ad templates from Facebook using the Graph API:

```typescript
export const fetchAds = async ({
  limit,
  cursor,
  accessToken,
  campaign,
  defaultErrorMessage,
}: {...}) => {
  const creativeFields = [
    "id",
    "name",
    "actor_id",
    "asset_feed_spec",           // ← Includes image array with crop specs
    "degrees_of_freedom_spec",
    "effective_instagram_media_id",
    "effective_object_story_id",
    "instagram_user_id",
    "object_story_spec",           // ← Contains image_hash in link_data/video_data
    "contextual_multi_ads",
    "thumbnail_url",
  ].join(",");

  return facebookRequest<AdsApiResponse>(`/${campaign}/ads`, {
    queryParams: {
      fields: `id,name,creative{${creativeFields}}`,
      access_token: accessToken,
      ...
    },
  });
};
```

**API Details**:
- **Endpoint**: `GET /{campaign_id}/ads`
- **API Version**: Dynamic, from `process.env.REACT_APP_FACEBOOK_API_VERSION`
- **Base URL**: `https://graph.facebook.com/{version}/`

### 2.2 Fields Captured from Facebook

**Note**: The dashboard **does NOT request** `image_crops` directly from the Graph API. Image crop specifications come as part of `object_story_spec` and `asset_feed_spec`.

#### From `object_story_spec`:

For **Link Data Ads**:
- `link_data.image_hash` — Hash reference to image already in Facebook's account
- `link_data.message` — Primary ad copy
- `link_data.name` — Headline text
- `link_data.description` — Description text
- `link_data.call_to_action` — Button and action spec
- `link_data.page_welcome_message` — Messenger welcome message (JSON)
- `link_data.link` — Landing URL

For **Video Data Ads**:
- `video_data.image_hash` — Thumbnail image hash
- `video_data.title` — Video title
- `video_data.message` — Ad copy
- `video_data.video_id` — Facebook video ID

#### From `asset_feed_spec`:

Contains the asset feed specification with structure:
```json
{
  "images": [
    {
      "hash": "52b2b89b22981caa8f838ae91609ef1d",
      "image_crops": {
        "191x100": [[0, 212], [1080, 777]],
        "100x100": [[100, 300], [980, 680]],
        ...
      },
      "url": "https://...",
      "url_tags": "..."
    }
  ],
  "videos": [...],
  "text": [...],
  "call_to_action_type": "...",
  "link_urls": [...]
}
```

### 2.3 What Gets Stored in the Database

**Location**: Dashboard UI component `/dashboard/src/pages/StudyConfPage/forms/creatives/Creative.tsx`, lines 49-58

When a user selects a template from Facebook:

```typescript
const handleSelectTemplate = (e: any) => {
  const ad = ads.find(a => a.id === value);
  const template = ad["creative"];  // Entire creative object
  updateFormData({ ...data, template, name: ad.name }, index);
};
```

**API Backend Storage** (Go): `/api/internal/types/studyconf.go`, lines 255-266

```go
type CreativeConf struct {
    Body            string   `json:"body"`
    ButtonText      string   `json:"button_text"`
    Destination     string   `json:"destination"`
    ImageHash       string   `json:"image_hash"`      // Key field
    LinkText        string   `json:"link_text"`
    Name            string   `json:"name"`
    WelcomeMessage  string   `json:"welcome_message"`
    Tags            []string `json:"tags"`
}
```

**Critical Finding**: The API backend **extracts only specific fields** from the full template. The complete `object_story_spec` with all crop specifications is **not stored** in the database.

However, the **Adopt service has its own storage** that preserves the full template object.

---

## 3. Ad Creation (Adopt Service)

### 3.1 Template Loading from Database

**Location**: `/adopt/adopt/campaign_queries.py`, lines 86-99

```python
def get_campaign_configs(campaignid, cnf: DBConf):
    """Query study_confs table and return configurations by type."""
    results = cnf.execute("""
        SELECT conf_type, conf
        FROM study_confs
        WHERE campaign_id = %s
        ORDER BY id DESC
    """, [campaignid])

    return [
        {"conf_type": row[0], "conf": json.loads(row[1])}
        for row in results
    ]
```

**Data Flow**:
1. Study loads configs from `study_confs` table
2. Parses JSON `conf` field for each `conf_type` (including 'creatives')
3. `get_study_conf()` creates a dictionary mapping conf_type → config
4. Pydantic model `StudyConf` parses the creatives array

**Location**: `/adopt/adopt/malaria.py`, lines 43-50

```python
def get_study_conf():
    configs = get_campaign_configs(campaignid, cnf)
    cd = {conf["conf_type"]: conf["conf"] for conf in configs}
    return StudyConf(**params)  # Pydantic parses cd['creatives']
```

### 3.2 CreativeConf Data Structure

**Location**: `/adopt/adopt/study_conf.py`, lines 395-401

```python
class CreativeConf(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    destination: str                           # e.g., "messenger", "web"
    name: str                                  # Creative identifier
    template: FacebookAdCreative               # Full Facebook template dict
    template_campaign: str | None = None       # Optional campaign association
    tags: list[str] | None = None              # Optional tags

# Type alias:
FacebookAdCreative = Dict[str, Any]
```

**Key Point**: The `template` field contains the **complete Facebook ad creative object**, including:
- `object_story_spec` with link_data/video_data and image_hash
- `asset_feed_spec` with images array containing crop specifications
- `degrees_of_freedom_spec` with optimization settings
- `actor_id`, `instagram_user_id`, `thumbnail_url`, etc.

### 3.3 How Adopt Creates Ads

**Location**: `/adopt/adopt/marketing.py`, lines 281-374

The `_create_creative()` function constructs new ads by:

1. **Creating AdCreative object** (line 288):
   ```python
   c = AdCreative()
   c[AdCreative.Field.name] = config.name
   ```

2. **Copying template fields** (lines 295-305):
   ```python
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
   ```

3. **Processing version spec** (lines 306-307):
   ```python
   convert_version(c)  # Removes deprecated fields if present
   ```

4. **Constructing link_data** (lines 309-326):
   ```python
   tld = config.template["object_story_spec"].get("link_data")
   if tld:
       link_data = {
           AdCreativeLinkData.Field.call_to_action: call_to_action,
           AdCreativeLinkData.Field.image_hash: tld["image_hash"],  # ← From template
           AdCreativeLinkData.Field.message: tld.get("message"),
           AdCreativeLinkData.Field.name: tld.get("name"),
           AdCreativeLinkData.Field.description: tld.get("description"),
       }
       # Optionally inject link and page_welcome_message
   ```

5. **Handling asset_feed_spec** (lines 356-372):
   ```python
   # Copy entire asset_feed_spec from template (includes image_crops!)
   if "asset_feed_spec" in config.template:
       asset_feed = config.template["asset_feed_spec"]
       # Replace link_urls with new link if provided
       if link:
           asset_feed["link_urls"] = [link]
       c[AdCreative.Field.asset_feed_spec] = asset_feed
   ```

**Critical Insight**: The `asset_feed_spec`, including all image crop specifications, is **copied verbatim from the template**. This is where the `191x100` deprecation bug originates.

### 3.4 Image Crops Specification Format

**From test data**: `/adopt/test/ads/image_ad_website.json`, lines 24-35

```json
{
  "asset_feed_spec": {
    "images": [
      {
        "hash": "52b2b89b22981caa8f838ae91609ef1d",
        "image_crops": {
          "191x100": [
            [0, 212],
            [1080, 777]
          ],
          "100x100": [
            [100, 400],
            [980, 780]
          ]
        }
      }
    ]
  }
}
```

**Format Specification**:
- **Key**: Aspect ratio string (e.g., "191x100", "100x100")
- **Value**: 2-element array of coordinates
  - First element: `[x_min, y_min]` — Top-left corner
  - Second element: `[x_max, y_max]` — Bottom-right corner
  - Coordinates are absolute pixel positions in the original image

---

## 4. The 191x100 Deprecation Bug

### 4.1 The Error

When Adopt attempts to create ads with templates containing `191x100` crop specifications on Facebook API v22+:

```
The 191x100 crop key for image ads is deprecated
```

### 4.2 Root Cause

1. **Where it starts**: Templates are stored in the database with crop specifications from when ads were created (possibly on older Facebook API versions)
2. **Where it breaks**: In `/adopt/adopt/marketing.py`, lines 356-372, the `asset_feed_spec` is copied **verbatim** from the template to the new AdCreative
3. **Why it fails now**: Facebook API v22+ (current as of February 2026) no longer accepts the `191x100` crop key for ad creation
4. **Why it's consistent**: The facebook-business SDK v22 in vlab enforces this deprecation strictly on all API calls

### 4.3 Code Path to Failure

```python
# In _create_creative() at line 356-372:
if "asset_feed_spec" in config.template:
    asset_feed = config.template["asset_feed_spec"]
    # ^^^^^^^^^^ Contains {"images": [{"image_crops": {"191x100": [...], ...}}]}

    c[AdCreative.Field.asset_feed_spec] = asset_feed
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Passed directly to Facebook API
    # When Facebook API tries to create the ad, it rejects "191x100"
```

### 4.4 Why Templates Have 191x100

The `191x100` crop specification was:
- **Valid until**: April 30, 2019 (when deprecated by Facebook)
- **Used for**: Landscape/widescreen placements (1.91:1 aspect ratio)
- **Advantages**: Broader placement compatibility on older versions
- **Legacy Status**: Templates may contain these specs if they were created before deprecation or haven't been updated since

---

## 5. Fix Strategy

### 5.1 Implementation Location

**File**: `/adopt/adopt/marketing.py`, lines 356-372

**Current Code**:
```python
# Handle asset_feed_spec (images, videos, text)
if "asset_feed_spec" in config.template:
    asset_feed = copy.deepcopy(config.template["asset_feed_spec"])
    if link and link_urls:
        asset_feed["link_urls"] = [link] + link_urls[1:]
    c[AdCreative.Field.asset_feed_spec] = asset_feed
```

**Fixed Code** (add crop key sanitization):
```python
# Handle asset_feed_spec (images, videos, text)
if "asset_feed_spec" in config.template:
    asset_feed = copy.deepcopy(config.template["asset_feed_spec"])

    # Remove deprecated crop keys before sending to Facebook API
    if "images" in asset_feed:
        for image in asset_feed["images"]:
            if "image_crops" in image:
                image["image_crops"].pop("191x100", None)  # Remove deprecated key

    if link and link_urls:
        asset_feed["link_urls"] = [link] + link_urls[1:]
    c[AdCreative.Field.asset_feed_spec] = asset_feed
```

### 5.2 Deprecated Crop Keys to Handle

Currently, only **`191x100`** is deprecated and must be removed.

Other crop keys remain valid:
- `100x100` — Square (1:1) — PRIMARY REPLACEMENT
- `100x72` — Landscape variant
- `400x150` — Landscape
- `400x500` — Vertical/portrait
- `600x360` — Landscape
- `90x160` — Vertical/portrait (Stories/Reels)

### 5.3 Migration Approach

**Short-term** (immediate fix):
1. Remove `191x100` crop specs before calling Facebook API
2. Ensure at least one valid crop key is present (e.g., `100x100`)
3. Add logging when deprecated keys are removed

**Long-term** (template cleanup):
1. Audit all templates in `study_confs` table
2. Identify which contain `191x100`
3. Replace with `100x100` or other valid crops
4. Update templates to use current best practices

### 5.4 Code Location Summary

| Component | File | Lines | Action |
|-----------|------|-------|--------|
| **Crop sanitization** | `adopt/marketing.py` | 356-372 | Add deprecation removal |
| **Image structure** | `adopt/study_conf.py` | 395-401 | No change (documents template structure) |
| **API creation** | `adopt/facebook/state.py` | 35-55 | No change (reading only, deprecation removal happens upstream) |

---

## 6. Supported Crop Keys (Current)

As of February 2026, with Facebook API v22.0 and facebook-business SDK v22:

| Crop Key | Aspect Ratio | Dimensions | Use Case | Status |
|----------|--------------|-----------|----------|--------|
| `100x100` | 1:1 (square) | 100×100 px | Feed, Instagram, Audience Network | ✅ PRIMARY |
| `100x72` | ~1.39:1 | 100×72 px | Landscape placements | ✅ Valid |
| `400x150` | ~2.67:1 | 400×150 px | Desktop feed wide | ✅ Valid |
| `400x500` | 0.8:1 | 400×500 px | Stories, Reels, vertical | ✅ Valid |
| `600x360` | 1.67:1 | 600×360 px | Large landscape | ✅ Valid |
| `90x160` | ~0.56:1 | 90×160 px | Stories/Reels (9:16) | ✅ Valid |
| `191x100` | 1.91:1 | 191×100 px | Landscape (deprecated) | ❌ DEPRECATED |

### 6.1 Image Size Recommendations

- **Minimum**: 1080 × 1080 pixels (for 1:1 ratio)
- **Maximum file size**: 30 MB
- **Formats**: JPG, PNG
- **Safe zones** (areas that won't be cropped):
  - Top: 14% minimum clearance
  - Bottom: 35% minimum clearance
  - Sides: 6% minimum clearance each

### 6.2 Best Practices for New Ads

1. **Always use `100x100`** as primary crop (square format has highest performance)
2. **Provide fallbacks** (e.g., `400x500` for Stories)
3. **Avoid `191x100`** entirely
4. **Use coordinate arrays** for precision: `"100x100": [[x1, y1], [x2, y2]]`

---

## 7. Implementation Reference

### 7.1 Key Files and Locations

| Component | File Path | Purpose |
|-----------|-----------|---------|
| **Dashboard fetch** | `/dashboard/src/helpers/api.ts` | Lines 568-613: Fetches templates from Facebook |
| **Dashboard selection** | `/dashboard/src/pages/StudyConfPage/forms/creatives/Creative.tsx` | Lines 49-58: User template selection |
| **API storage** | `/api/internal/types/studyconf.go` | Lines 255-266: CreativeConf struct |
| **Adopt config** | `/adopt/adopt/study_conf.py` | Lines 395-401: CreativeConf class |
| **Creative creation** | `/adopt/adopt/marketing.py` | Lines 281-374: Ad creative construction |
| **Asset feed handling** | `/adopt/adopt/marketing.py` | Lines 356-372: Where crop specs are passed (FIX LOCATION) |
| **Database queries** | `/adopt/adopt/campaign_queries.py` | Lines 86-99: Template loading |
| **Facebook API calls** | `/adopt/adopt/facebook/state.py` | Lines 35-55: Creative fetching |
| **Test data** | `/adopt/test/ads/image_ad_website.json` | Lines 24-35: Example with crop specs |
| **SDK type stubs** | `/adopt/stubs/facebook_business/adobjects/adassetfeedspecimage.pyi` | Image crop field definitions |

### 7.2 Type Stubs Reference

**AdAssetFeedSpecImage** (`/adopt/stubs/facebook_business/adobjects/adassetfeedspecimage.pyi`):
```python
class AdAssetFeedSpecImage(AbstractObject):
    class Field(AbstractObject.Field):
        adlabels: str        # Ad labels
        hash: str            # Image hash
        image_crops: str     # Crop specifications (dict mapping ratio → coords)
        url: str             # Image URL
        url_tags: str        # URL tracking parameters
```

**AdsImageCrops** (`/adopt/stubs/facebook_business/adobjects/adsimagecrops.pyi`):
```python
class AdsImageCrops(AbstractObject):
    class Field(AbstractObject.Field):
        field_100x100: str   # '100x100'
        field_100x72: str    # '100x72'
        field_191x100: str   # '191x100' (DEPRECATED)
        field_400x150: str   # '400x150'
        field_400x500: str   # '400x500'
        field_600x360: str   # '600x360'
        field_90x160: str    # '90x160'
```

---

## 8. Architecture Insights

### 8.1 Template Immutability with Selective Override

- Templates are loaded from the database as **immutable specifications**
- Only specific fields are **dynamically overridden** at creation time:
  - `call_to_action` — Based on destination
  - `link` — Custom landing URL
  - `page_welcome_message` — Messenger-specific
  - `url_tags` — Tracking parameters
- Image hashes and crop specifications **flow unchanged** from template
- This ensures consistency while allowing destination-specific customization

### 8.2 Crop Specifications as Part of Asset Feed

- Crops are **embedded in `asset_feed_spec.images`**, not as a separate field
- Each image can have **multiple crop specifications** for different placements
- The `image_crops` field is a **dictionary** mapping aspect ratio → coordinates
- This allows single image to serve multiple placement requirements

### 8.3 Batching and API Efficiency

From `/adopt/adopt/facebook/state.py`, lines 114-123:
```python
def get_all_ads(api: FacebookAdsApi, c: Campaign) -> List[Ad]:
    creative_ids = [ad["creative"]["id"] for ad in ads]
    # Fetch full creative details in batches of 50
    creatives = {
        c["id"]: c for cids in split(creative_ids, 50)
        for c in get_creatives(api, cids)
    }
```

- Creative details are **fetched in batches of 50** to reduce API calls
- This avoids hitting rate limits on large campaigns

### 8.4 Budget Convention (Cents)

- All Facebook budget values must be in **cents**
- Conversion at ad set creation time: `budget = round(budget * 100)`
- Prevents floating-point errors in billing

---

## 9. Troubleshooting Guide

### Error: "The 191x100 crop key for image ads is deprecated"

**Symptoms**:
- Ad creation fails when using templates with 191x100 crops
- Error occurs consistently with all affected templates
- Only happens on current API versions

**Root Cause**:
- Template contains `asset_feed_spec.images[].image_crops.191x100`
- Facebook API v22+ rejects this deprecated key

**Solution**:
1. **Immediate**: Apply the fix at `/adopt/adopt/marketing.py` lines 356-372
   - Remove `191x100` crop key before sending to API
2. **Verify**: Test with templates known to have 191x100 crops
3. **Long-term**: Audit and update templates in database

### Verifying the Fix

Test data with 191x100 crops:
```json
{
  "asset_feed_spec": {
    "images": [
      {
        "hash": "52b2b89b22981caa8f838ae91609ef1d",
        "image_crops": {
          "191x100": [[0, 212], [1080, 777]],
          "100x100": [[100, 400], [980, 780]]
        }
      }
    ]
  }
}
```

After fix, the 191x100 key is removed but 100x100 remains:
```json
{
  "asset_feed_spec": {
    "images": [
      {
        "hash": "52b2b89b22981caa8f838ae91609ef1d",
        "image_crops": {
          "100x100": [[100, 400], [980, 780]]
        }
      }
    ]
  }
}
```

---

## 10. API Version Reference

**Current** (February 2026):
- **Marketing API**: v22.0 (released January 21, 2025)
- **Facebook Business SDK**: v22
- **Minimum Required**: v22.0

**Deprecation Timeline**:
| Version | Deprecated | Status |
|---------|-----------|--------|
| v19.0 | Feb 4, 2025 | Expired |
| v20.0 | May 6, 2025 | Expired |
| v21.0 | TBD 2025 | Active (aging) |
| v22.0 | TBD 2026+ | Current/Stable |

**Recommendation**: Always target v22.0 or higher for new implementations.

---

## 11. Summary: Image Creative Flow

```
┌─────────────────────────────────┐
│   Facebook Ad Account           │
│   (Published Ads with crops)    │
└────────────┬────────────────────┘
             │ (1) Dashboard fetches
             │     (Graph API v22)
             ▼
┌─────────────────────────────────────────┐
│ Graph API: GET /{campaign}/ads          │
│ Returns: creative{                      │
│   object_story_spec (has image_hash),   │
│   asset_feed_spec (has image_crops),    │
│   ...                                   │
│ }                                       │
└────────────┬────────────────────────────┘
             │ (2) User selects template
             ▼
┌──────────────────────────────────┐
│ Dashboard Frontend               │
│ Stores: CreativeConf {           │
│   name, destination,             │
│   template: {...full object...}  │
│ }                                │
└────────────┬─────────────────────┘
             │ (3) Save to backend
             ▼
┌──────────────────────────────────┐
│ API Backend (Go)                 │
│ Database: study_confs table      │
│ Stores: {ImageHash, Name, ...}   │
│ (Extracts key fields)            │
└────────────┬─────────────────────┘
             │ (4) Adopt loads
             │ get_campaign_configs()
             ▼
┌──────────────────────────────────┐
│ Adopt Service (Python)           │
│ CreativeConf.template =          │
│   {object_story_spec, ...}       │
│   {asset_feed_spec with crops}   │
│                                  │
│ _create_creative():              │
│ - Copy template fields           │
│ - [FIX] Remove 191x100 crops     │
│ - Pass to Facebook API           │
└────────────┬─────────────────────┘
             │ (5) Create ad
             │ (Facebook API v22)
             ▼
┌──────────────────────────────────┐
│ Facebook API                     │
│ AdCreative with:                 │
│ - Valid crop specs (100x100, etc)│
│ - Image hash                     │
│ - All other fields               │
│                                  │
│ ✅ Success (deprecated keys      │
│    removed before submission)    │
└──────────────────────────────────┘
```

---

## 12. For Developers: Key Takeaways

1. **Image crops are stored in templates**, specifically in `asset_feed_spec.images[].image_crops`
2. **The deprecation bug**: 191x100 crops are passed verbatim to Facebook API v22+, causing failures
3. **The fix**: Remove `191x100` keys in `/adopt/adopt/marketing.py` before API submission
4. **Supported crops**: `100x100`, `100x72`, `400x150`, `400x500`, `600x360`, `90x160`
5. **Best practice**: Use `100x100` (square) as primary crop; provide fallbacks for specific placements
6. **No changes needed** in template data structures, only in the ad creation logic where crops are passed to Facebook

---

## 13. References

This document consolidates findings from:
- `documentation/planning/facebook-ads-crop-findings-adopt.md` — Adopt service template processing
- `documentation/planning/facebook-ads-crop-findings-dashboard.md` — Dashboard API fetch and template selection
- `documentation/planning/facebook-ads-crop-findings-api.md` — API deprecation and version timeline
- `documentation/facebook-ads-api.md` — Facebook API integration and best practices

For implementation details, refer to the specific file paths and line numbers cited throughout this document.
