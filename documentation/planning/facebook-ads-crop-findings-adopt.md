# Facebook Ads Image Cropping and Template Processing - Adopt Service Findings

## Executive Summary

The `adopt` service creates Facebook ads from templates stored in the database. The process involves loading CreativeConf objects (which contain Facebook ad templates), extracting image hash values, and constructing AdCreative objects with appropriate cropping specifications. Image crops are specified using the `191x100` ratio (and other aspect ratios like `100x100`, `100x72`, `400x150`, `400x500`, `600x360`, `90x160`) and are included in the `image_crops` field within `asset_feed_spec`.

## 1. How Templates Are Read and Loaded

### Data Flow

**Database → StudyConf → CreativeConf → AdCreative**

1. **Loading from Database** (`/home/nandan/Documents/vlab-research/vlab/adopt/adopt/campaign_queries.py`, lines 86-99)
   - `get_campaign_configs(campaignid, cnf: DBConf)` queries the `study_confs` table
   - Fetches the latest configuration per `conf_type` (including creatives)
   - Returns a list of dicts with `conf_type` and `conf` keys
   - The `conf` dictionary contains the JSON-serialized template

2. **Creating StudyConf** (`/home/nandan/Documents/vlab-research/vlab/adopt/adopt/malaria.py`, lines 43-50)
   - `get_study_conf()` calls `get_campaign_configs()` to fetch raw configurations
   - Creates a dictionary `cd` mapping conf_type → conf JSON
   - Instantiates `StudyConf(**params)` with the configs
   - The Pydantic model parses creatives from the `cd['creatives']` config

3. **Stratum Hydration** (`/home/nandan/Documents/vlab-research/vlab/adopt/adopt/malaria.py`, lines 465-488)
   - `hydrate_strata()` receives `strata` (list of StratumConf) and `creatives` (list of CreativeConf)
   - Creates a lookup: `creative_lookup = {c.name: c for c in creatives}`
   - Maps stratum creative names to actual CreativeConf objects
   - Returns list of `Stratum` objects with fully resolved creative references

### CreativeConf Data Structure

(`/home/nandan/Documents/vlab-research/vlab/adopt/adopt/study_conf.py`, lines 395-401)

```python
class CreativeConf(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    destination: str                    # Name of destination (e.g., "messenger", "web")
    name: str                           # Unique creative identifier
    template: FacebookAdCreative        # Dict[str, Any] - raw Facebook ad template
    template_campaign: str | None = None  # Optional campaign association
    tags: list[str] | None = None       # Optional tags
```

The `template` field is a dictionary (type alias: `FacebookAdCreative = Dict[str, Any]`) containing the complete Facebook ad creative specification, which may include:
- `object_story_spec` - Core ad story with page_id, link_data, or video_data
- `asset_feed_spec` - Asset feed specification (images, videos, text, CTA)
- `degrees_of_freedom_spec` - Creative optimization settings
- `actor_id`, `instagram_user_id`, `thumbnail_url`, `contextual_multi_ads` - Additional fields

## 2. Image Hash and Image Crops Processing

### Image Hash Field

**Location in Templates**: `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, lines 309-326

Image hashes are extracted from template configurations and included in created ads:

```python
# For link_data creatives (lines 309-326)
tld = config.template["object_story_spec"].get("link_data")

if tld:
    link_data = {
        AdCreativeLinkData.Field.call_to_action: call_to_action,
        AdCreativeLinkData.Field.image_hash: tld["image_hash"],  # Key line
        AdCreativeLinkData.Field.message: tld.get("message"),
        AdCreativeLinkData.Field.name: tld.get("name"),
        AdCreativeLinkData.Field.description: tld.get("description"),
    }
```

Similarly for video_data (lines 328-343):
```python
tvd = config.template["object_story_spec"].get("video_data")
if tvd:
    to_copy = [
        AdCreativeVideoData.Field.image_hash,    # Used as thumbnail
        AdCreativeVideoData.Field.message,
        AdCreativeVideoData.Field.title,
        AdCreativeVideoData.Field.video_id,
    ]
    video_data = {k: tvd.get(k) for k in to_copy}
```

**Example from Test Data**:
- `/home/nandan/Documents/vlab-research/vlab/adopt/test/ads/image_ad_messenger.json` (lines 12-13)
  ```json
  "image_hash": "7fabd5c7072f2242195f6f5dbbfb512c"
  ```

### Image Crops and "191x100" Aspect Ratio

**Location in Templates**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/image_ad_website.json`, lines 24-35

Image crops are specified in the `asset_feed_spec.images` array:

```json
{
  "images": [
    {
      "hash": "52b2b89b22981caa8f838ae91609ef1d",
      "image_crops": {
        "191x100": [
          [0, 212],
          [1080, 777]
        ]
      }
    }
  ]
}
```

**Crop Specification Format**:
- Key: "191x100" - The target aspect ratio (width x height, approximately 1.91:1)
- Value: A 2-element array representing crop coordinates:
  - First element: `[x_min, y_min]` - Top-left corner of crop rectangle
  - Second element: `[x_max, y_max]` - Bottom-right corner of crop rectangle
  - In example: crops from (0, 212) to (1080, 777) in the original image

**Supported Aspect Ratios** (from Facebook Business SDK stubs):
- `/home/nandu/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/adsimagecrops.pyi`
  ```python
  class Field(AbstractObject.Field):
      field_100x100: str      # Square
      field_100x72: str       # 1.39:1 ratio
      field_191x100: str      # ~1.91:1 ratio (RIGHT_COLUMN placement)
      field_400x150: str      # ~2.67:1 ratio (desktop feed)
      field_400x500: str      # 0.8:1 ratio (feed vertical)
      field_600x360: str      # 1.67:1 ratio (feed horizontal)
      field_90x160: str       # ~0.56:1 ratio (stories/reels)
  ```

### Image Crops in AdAssetFeedSpecImage

**Data Structure** (from `/home/nandu/Documents/vlab-research/vlab/adopt/stubs/facebook_business/adobjects/adassetfeedspecimage.pyi`):

```python
class AdAssetFeedSpecImage(AbstractObject):
    class Field(AbstractObject.Field):
        adlabels: str         # Labels for ad customization
        hash: str             # Image hash
        image_crops: str      # Crop specifications (JSON string)
        url: str              # Image URL
        url_tags: str         # URL parameters for tracking
```

The `image_crops` field accepts a dictionary where:
- Keys are aspect ratio strings (e.g., "191x100")
- Values are coordinate arrays [[x1, y1], [x2, y2]]

## 3. Ad Creation Process and Facebook API Calls

### Creative Creation Workflow

**Main Function**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, lines 393-440

```python
def create_creative(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
) -> AdCreative:
```

**Flow**:
1. Loads metadata from stratum and study
2. Determines destination type (Messenger, App, Web)
3. Constructs appropriate call_to_action based on destination
4. Calls `_create_creative()` with template and parameters
5. Returns AdCreative object ready to be saved to Facebook

### _create_creative Implementation

**Location**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, lines 281-374

Key operations:

1. **Initialize AdCreative** (line 288)
   ```python
   c = AdCreative()
   ```

2. **Copy Template Fields** (lines 295-305)
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

3. **Process Version Spec** (lines 306-307)
   - `convert_version(c)` removes deprecated "standard_enhancements" if present

4. **Construct Link Data** (lines 309-326)
   - Extracts from template's `object_story_spec.link_data`
   - Injects call_to_action, link, and optional page_welcome_message
   - **Preserves image_hash from template**

5. **Construct Video Data** (lines 328-343)
   - Extracts from template's `object_story_spec.video_data`
   - Copies image_hash, message, title, video_id
   - Injects call_to_action and optional page_welcome_message

6. **Handle Asset Feed Spec** (lines 356-372)
   - Copies entire asset_feed_spec from template (includes image_crops)
   - **Replaces link_urls** with new link parameter if provided
   - Adds page_welcome_message to additional_data if needed

### Ad Set and Ad Creation

**AdSet Creation** (`/home/nandu/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, lines 96-120):

```python
def create_adset(c: AdsetConf) -> AdSet:
    adset = AdSet()
    adset[AdSet.Field.end_time] = midnight + timedelta(hours=c.hours)
    adset[AdSet.Field.targeting] = targeting
    adset[AdSet.Field.status] = c.status
    adset[AdSet.Field.daily_budget] = c.budget  # In cents!
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

**Important**: Budget is converted to cents before sending to Facebook (line 487):
```python
budget = round(budget * 100)
```

**Ad Creation** (`/home/nandu/Documents/vlab-research/vlab/adopt/adopt/marketing.py`, lines 138-144):

```python
def create_ad(adset: AdSet, creative: AdCreative, status: str) -> Ad:
    a = Ad()
    a[Ad.Field.name] = creative["name"]
    a[Ad.Field.status] = status
    a[Ad.Field.adset_id] = adset["id"]
    a[Ad.Field.creative] = creative
    return a
```

## 4. Facebook API Integration Points

### Fetching Creatives from Facebook

**Location**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/facebook/state.py`, lines 35-55

```python
def get_creatives(api: FacebookAdsApi, ids: List[str]) -> List[AdCreative]:
    fields = [
        AdCreative.Field.actor_id,
        AdCreative.Field.image_crops,           # Fetches crop specs
        AdCreative.Field.asset_feed_spec,       # Includes image_crops
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.object_story_spec,
        AdCreative.Field.thumbnail_url,
        AdCreative.Field.contextual_multi_ads,
        AdCreative.Field.url_tags,
    ]
    return call(AdCreative.get_by_ids, ids=ids, fields=fields, api=api)
```

**Note**: Fetches both top-level `image_crops` field AND `asset_feed_spec` which contains images with their crop specifications.

### Retrieving Full Ad State

**Location**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/facebook/state.py`, lines 114-123

```python
def get_all_ads(api: FacebookAdsApi, c: Campaign) -> List[Ad]:
    ads = [a for a in get_ads(c)]
    creative_ids = [ad["creative"]["id"] for ad in ads]

    # Fetch full creative details in batches of 50
    creatives = {
        c["id"]: c for cids in split(creative_ids, 50)
        for c in get_creatives(api, cids)
    }
    for cid, ad in zip(creative_ids, ads):
        ad["creative"] = creatives[cid]
    return ads
```

### Facebook SDK Type Stubs

**AdCreative Field Definitions** (partial):
```
- image_crops: str (top-level creative field)
- asset_feed_spec: str (contains nested image_crops)
```

## 5. Test Examples

### Example 1: Image Ad with Website Destination

**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/image_ad_website.json`

**Key Components**:
- **Actor ID**: "1855355231229529" (Facebook page)
- **Page ID**: "1855355231229529"
- **Asset Feed Spec**: Contains images with crop specifications
- **Image with Crops** (lines 23-35):
  ```json
  {
    "hash": "52b2b89b22981caa8f838ae91609ef1d",
    "image_crops": {
      "191x100": [[0, 212], [1080, 777]]
    }
  }
  ```
- **Degrees of Freedom**: Spec with opt-in/opt-out for features like image_enhancement, image_templates, image_touchups

### Example 2: Image Ad with Messenger Destination

**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/image_ad_messenger.json`

**Key Components**:
- **Link Data** with image_hash: "7fabd5c7072f2242195f6f5dbbfb512c"
- **Call to Action**: `{"type": "MESSAGE_PAGE", "value": {"app_destination": "MESSENGER"}}`
- **Page Welcome Message**: Contains embedded JSON with visual editor configuration

### Example 3: Video Ad

**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/video_ad_website.json`

**Key Components**:
- **Asset Feed Spec**: Contains videos array instead of images
- **Video Element**: `{"video_id": "...", "thumbnail_url": "..."}`
- **Degrees of Freedom**: Includes "video_auto_crop" feature with OPT_OUT status

## 6. Data Structures and Field Mappings

### AdCreative Fields Used in Create Operations

```
AdCreative.Field.name                       # Creative name (string)
AdCreative.Field.actor_id                   # Page ID (for post ownership)
AdCreative.Field.url_tags                   # UTM/tracking parameters
AdCreative.Field.degrees_of_freedom_spec    # Creative optimization settings
AdCreative.Field.instagram_user_id          # Instagram creator account
AdCreative.Field.thumbnail_url              # Preview image URL
AdCreative.Field.contextual_multi_ads       # Contextual variation settings
AdCreative.Field.object_story_spec          # Core ad story spec
AdCreative.Field.asset_feed_spec            # Asset feed (images/videos with crops)
```

### AdCreativeLinkData Fields

```
AdCreativeLinkData.Field.call_to_action     # Button action
AdCreativeLinkData.Field.image_hash         # Image identifier (from template)
AdCreativeLinkData.Field.message            # Primary text
AdCreativeLinkData.Field.name               # Headline
AdCreativeLinkData.Field.description        # Description text
AdCreativeLinkData.Field.link               # Destination URL
AdCreativeLinkData.Field.page_welcome_message  # Messenger welcome message
```

### AdSet Fields

```
AdSet.Field.name                            # Stratum ID
AdSet.Field.targeting                       # Audience targeting (dict)
AdSet.Field.status                          # ACTIVE or PAUSED
AdSet.Field.daily_budget                    # Budget in cents
AdSet.Field.start_time                      # Activation time
AdSet.Field.end_time                        # Deactivation time
AdSet.Field.campaign_id                     # Parent campaign ID
AdSet.Field.optimization_goal               # e.g., REACH, CONVERSIONS
AdSet.Field.destination_type                # e.g., EXTERNAL_URL, MESSENGER
AdSet.Field.billing_event                   # IMPRESSIONS
AdSet.Field.bid_strategy                    # LOWEST_COST_WITHOUT_CAP
AdSet.Field.promoted_object                 # App install destination (optional)
```

## 7. Architectural Patterns and Key Insights

### 1. Template Immutability with Selective Override
- Template creatives are loaded from the database as immutable specifications
- Only specific fields are overridden at creation time: link, call_to_action, welcome_message
- Image hashes and crop specifications flow through unchanged from template
- This ensures consistency while allowing dynamic destination customization

### 2. Crop Specifications as Part of Asset Feed
- Crops are embedded in the asset_feed_spec.images array, not separately
- Each image can have multiple crop specifications for different placements
- The "191x100" aspect ratio is commonly used for right-column desktop placements

### 3. Batching and API Efficiency
- Creative fetches are batched in groups of 50 to reduce API calls
- Split utility function handles pagination: `split(creative_ids, 50)`

### 4. Budget in Cents Convention
- All Facebook budget values are internally stored in cents
- Conversion happens at ad set creation time (line 487): `budget = round(budget * 100)`
- This prevents floating-point errors in billing

### 5. Metadata Injection Through References
- Creative references are tracked in stratum.metadata
- Metadata is used to create "ref" strings for form tracking
- These refs encode stratum ID and other parameters for survey response attribution

### 6. Version Management
- `convert_version()` function removes deprecated fields from degrees_of_freedom_spec
- Specifically removes "standard_enhancements" which may be deprecated in newer Facebook API versions

## 8. Files and Line References Summary

| Component | File Path | Lines |
|-----------|-----------|-------|
| CreativeConf definition | `adopt/study_conf.py` | 395-401 |
| Creative creation logic | `adopt/marketing.py` | 281-374 |
| Adset creation | `adopt/marketing.py` | 96-120 |
| Ad creation | `adopt/marketing.py` | 138-144 |
| Stratum hydration | `adopt/malaria.py` | 465-488 |
| Database loading | `adopt/campaign_queries.py` | 86-99 |
| Facebook API fetching | `adopt/facebook/state.py` | 35-55, 114-123 |
| Test: Image with crops | `test/ads/image_ad_website.json` | 24-35 |
| Test: Messenger | `test/ads/image_ad_messenger.json` | 1-21 |
| AdsImageCrops stub | `stubs/facebook_business/adobjects/adsimagecrops.pyi` | 1-14 |
| AdAssetFeedSpecImage stub | `stubs/facebook_business/adobjects/adassetfeedspecimage.pyi` | 1-12 |

## 9. Important Notes and Potential Gotchas

1. **Image Hash Management**: Image hashes come directly from the template. They must reference images already uploaded to the ad account or they will fail during ad creation.

2. **Crop Coordinate System**: Crop coordinates are absolute pixel positions, not percentages. The coordinate system appears to be [x, y] where origin is top-left.

3. **Aspect Ratio Flexibility**: Not all aspect ratios need to be specified. Facebook will automatically generate crops for unspecified ratios based on the specified ones.

4. **Budget in Cents**: Easy to miss - all amounts passed to Facebook API must be in cents. The code correctly converts at line 487 of marketing.py.

5. **Template Campaign Association**: CreativeConf has an optional `template_campaign` field that maps creatives to specific campaigns, allowing for campaign-specific creative variations (not currently heavily used).

6. **Degrees of Freedom Spec**: Contains Facebook's Creative Optimization settings. Removing "standard_enhancements" suggests API version compatibility work has been done.

7. **Asset Customization Rules**: In asset_feed_spec, `asset_customization_rules` array allows different creative variations for different placements and demographics - these are preserved from template and critical for multi-placement campaigns.

## 10. API Version References

- **Facebook Business SDK Version**: Not explicitly versioned in code, but stubs suggest recent SDK
- **Graph API Endpoint**: Uses `facebook_business.adobjects` module (current production)
- **Fields Requested**: Modern fields include degrees_of_freedom_spec, contextual_multi_ads (recent features)
- **No API Version Explicit**: Code does not pin or reference specific Graph API versions (e.g., v18.0)

## 11. Recommendations for Future Work

1. **Document Image Hash Sources**: Add comments about where image hashes come from and validation steps
2. **Crop Spec Validation**: Consider adding validation for crop coordinates (must be within image bounds)
3. **Template Versioning**: Current system doesn't version templates - consider tracking template versions with creatives
4. **Error Handling**: Add specific error messages for common failures (invalid image hash, out-of-bounds crops)
5. **Crop Testing**: Add unit tests specifically for crop spec validation and coordinate transformation
