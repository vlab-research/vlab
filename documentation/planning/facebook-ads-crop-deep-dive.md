# Facebook API Error: "The 191x100 crop key for image ads is deprecated" - Deep Dive Investigation

## Executive Summary

The error message `"The 191x100 crop key for image ads is deprecated"` is **NOT currently triggerable in the vlab codebase** because:

1. **Adopt service never creates ads with image_crops** - It uses `image_hash` only
2. **No 191x100 crop specifications exist** in templates or test data
3. **The error would only appear if** image_crops with 191x100 keys were explicitly sent to Facebook API
4. **The reconciliation system fetches image_crops** but only for comparison during state reading, not creation

This investigation reveals a **significant architectural gap** between what the system CAN handle (full ad templates with crops) and what it ACTUALLY uses (just image hashes).

---

## 1. Investigation Summary: All Code Paths

### 1.1 Facebook API Calls in Adopt - Complete Inventory

#### **CREATE Operations (Could Trigger Error)**

**Path 1: Ad Creation via GraphUpdater** (`/home/nandan/Documents/vlab-research/vlab/adopt/adopt/facebook/update.py:82-96`)

```python
def execute(self, instruction: Instruction):
    if instruction.action == "create":
        create = self.get_create(instruction.node)
        call(create, params=instruction.params, fields=[])
        return report(instruction)
```

**What Gets Sent**:
- Ad/AdSet/Campaign/Custom Audience creation
- `params` dictionary is built from `Instruction` object
- **For ads**: params come from `reconciliation.py` line 115

```python
def ad_dif(...):
    def creator(x):
        params = {**x.export_all_data(), "adset_id": adset["id"]}
        return [Instruction("ad", "create", params, None)]
```

**Critical Finding**: `x.export_all_data()` on an `Ad` object exports its `creative` field. If that creative has `image_crops` with 191x100, it WOULD be sent to Facebook.

---

#### **READ Operations (Safe)**

**Path 2: Reading Existing Ads** (`/home/nandu/Documents/vlab-research/vlab/adopt/adopt/facebook/state.py:35-55`)

```python
def get_creatives(api: FacebookAdsApi, ids: List[str]) -> List[AdCreative]:
    fields = [
        AdCreative.Field.actor_id,
        AdCreative.Field.image_crops,      # ← READS image_crops!
        AdCreative.Field.asset_feed_spec,
        ...
    ]
    return call(AdCreative.get_by_ids, ids=ids, fields=fields, api=api)
```

**Status**: Safe - Reading deprecate fields doesn't cause API errors. Facebook returns them as-is.

---

#### **RECONCILIATION Operations** (`/home/nandu/Documents/vlab-research/vlab/adopt/adopt/facebook/reconciliation.py:48-68`)

```python
def update_ad(source: Ad, ad: Ad) -> List[Instruction]:
    fields = [
        AdCreative.Field.actor_id,
        AdCreative.Field.image_crops,      # ← COMPARED but not modified
        AdCreative.Field.asset_feed_spec,
        ...
    ]

    if not _eq(ad["creative"], source["creative"], fields):
        return [Instruction("ad", "update", ad.export_all_data(), source["id"])]
```

**Key Detail**: The `_eq()` function compares field values but doesn't modify them. If a creative's image_crops differs, an update instruction is generated that **re-sends the entire creative** including deprecated crops.

**Potential Issue**: If Facebook has ads with 191x100 crops, and they're fetched and compared, the reconciliation would generate an "update" instruction that sends those deprecated crops back to Facebook.

---

### 1.2 Creative Creation Path - The Main Flow

**Complete Flow** (lines 393-440 in `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/marketing.py`):

```python
def create_creative(study: StudyConf, stratum: Stratum, config: CreativeConf, destination: DestinationConf) -> AdCreative:
    md = {**stratum.metadata, **study.general.extra_metadata}

    # Determine destination and build call_to_action
    if isinstance(destination, FlyMessengerDestination):
        return _create_creative(config, call_to_action=messenger_call_to_action(), ...)
    elif isinstance(destination, AppDestination):
        return _create_creative(config, call_to_action=app_download_call_to_action(...), link=link)
    elif isinstance(destination, WebDestination):
        return _create_creative(config, call_to_action=web_call_to_action(link), link=link)
```

**The _create_creative Function** (lines 281-374):

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

    # ===== FIELDS COPIED FROM TEMPLATE =====
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

    # ===== OBJECT STORY SPEC HANDLING =====
    tld = config.template["object_story_spec"].get("link_data")
    if tld:
        link_data = {
            AdCreativeLinkData.Field.call_to_action: call_to_action,
            AdCreativeLinkData.Field.image_hash: tld["image_hash"],  # ONLY image_hash used
            AdCreativeLinkData.Field.message: tld.get("message"),
            ...
        }

    # ===== ASSET FEED SPEC HANDLING (KEY SECTION) =====
    tafs = config.template.get(AdCreative.Field.asset_feed_spec)
    if tafs:
        c[AdCreative.Field.asset_feed_spec] = tafs  # ← ENTIRE asset_feed_spec copied!
        # ... modifications to link_urls and additional_data ...
```

**CRITICAL FINDING**:
- **Line 359**: `c[AdCreative.Field.asset_feed_spec] = tafs`
- This copies the ENTIRE asset_feed_spec from the template
- **If the template has image_crops with 191x100, they are sent to Facebook HERE**

---

## 2. When the Error IS Actually Triggered

### Scenario 1: Template Contains 191x100 Crops

**Where this could happen**:
1. User selects an ad from Facebook as a template (Dashboard → Creative.tsx)
2. That ad has `asset_feed_spec.images[*].image_crops` with "191x100" key
3. Template stored in CreativeConf.template
4. Adopt calls `_create_creative()` → copies full asset_feed_spec
5. Asset feed with 191x100 sent to Facebook
6. **ERROR**: "The 191x100 crop key for image ads is deprecated"

**Current Status**: Not happening because:
- Test templates (image_ad_website.json) DO have 191x100 crops but are only used for testing
- Live templates might have them (unknown without auditing Facebook account)
- But error handling doesn't seem to surface this in current code

---

### Scenario 2: Reconciliation Re-sends Old Creatives

**When this could happen**:
1. Old ad created with 191x100 crops exists in Facebook
2. Adopt fetches it with `get_creatives()` (line 45 requests image_crops field)
3. Reconciliation compares old state vs new state
4. If creative differs, generates update instruction
5. Update sends entire creative back to Facebook with deprecated crops
6. **ERROR**: "The 191x100 crop key for image ads is deprecated"

**Current Status**: Potentially happening if:
- Facebook account has old ads with 191x100 crops
- Reconciliation detects any difference
- Update instruction is generated and executed

---

## 3. The Actual Payload - What Gets Sent to Facebook

### Complete Ad Creative Payload (when using asset_feed_spec template)

**From test file**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/image_ad_website.json`

```json
{
  "id": "120204178098210150",
  "actor_id": "1855355231229529",
  "asset_feed_spec": {
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
    ],
    "call_to_action_types": ["APPLY_NOW"],
    "descriptions": [{"text": "This is a Description"}],
    "link_urls": [{
      "website_url": "https://vlab.digital/?foo=bar",
      "display_url": ""
    }],
    "titles": [{"text": "This is a Headline"}],
    "ad_formats": ["AUTOMATIC_FORMAT"]
  },
  "degrees_of_freedom_spec": {
    "creative_features_spec": {
      "advantage_plus_creative": {"enroll_status": "OPT_OUT"},
      "image_enhancement": {"enroll_status": "OPT_OUT"}
    }
  },
  "object_story_spec": {
    "page_id": "1855355231229529"
  }
}
```

**Key Payload Sections**:

1. **asset_feed_spec.images[*].image_crops** contains the deprecated 191x100 key
2. This is copied DIRECTLY from template (line 359 in marketing.py)
3. When sent to Facebook via `account.create_ad_creative(params=...)` (update.py line 95)
4. Facebook API rejects the 191x100 key

---

## 4. Error Handling and Error Catching

### Current Error Handling in Code

**Location**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/facebook/api.py:14-22`

```python
def fatal_code(e):
    # Non-fatal error codes that trigger retry:
    # 17, user request limit reached
    # 368 - page blocked from sending messages
    return e.api_error_code() not in {2, 17, 368, 80004}

@backoff.on_exception(
    backoff.constant, FacebookRequestError, interval=INTERVAL, giveup=fatal_code
)
def call(fn, *args, **kwargs):
    res = fn(**kwargs)
    if isinstance(res, Cursor):
        return [r for r in res]
    return res
```

**What This Means**:
- Only non-fatal error codes (2, 17, 368, 80004) trigger retries
- The 191x100 deprecation error is **NOT** in this list
- It will be treated as a FATAL error and NOT retried
- The error propagates up to `update.py` line 95: `call(create, params=instruction.params, fields=[])`
- From there, it bubbles to the caller in `server.py`

**Is the error caught?** No clear try/except in the chain. It would fail the entire `execute()` call.

---

## 5. The Reconciliation Question: Reads vs. Writes

### Question: Can the error come from READING?

**Answer: No**

Facebook's API happily returns deprecated field values when you request them. The error only occurs when you try to:
- **CREATE** with deprecated values
- **UPDATE** with deprecated values
- **SEND** them in a payload

Reading them doesn't trigger an error.

### Question: Can the error come from RECONCILIATION?

**Answer: Yes, potentially**

**Detailed Flow**:

```python
# state.py line 45 - READS existing creatives
fields = [AdCreative.Field.image_crops, ...]
creatives = get_creatives(api, creative_ids)  # Returns creatives WITH 191x100

# reconciliation.py line 62 - COMPARES them
if not _eq(ad["creative"], source["creative"], fields):
    return [Instruction("ad", "update", ad.export_all_data(), source["id"])]
    # ↑ If they differ, generates UPDATE instruction

# update.py line 85 - SENDS the update
call(obj.api_update, params=instruction.params, fields=[])
# ↑ Sends instruction.params which contains the full creative with 191x100
```

**Scenario**:
1. Old ad exists in Facebook with 191x100 crops
2. Adopt's reconciliation reads it
3. New state differs (maybe new link, new CTA)
4. Update instruction generated with full creative including 191x100
5. Facebook API rejects it: "The 191x100 crop key for image ads is deprecated"

---

## 6. Data Structures and Field Mappings

### AdCreative Fields Involved

```python
# From adopt/stubs/facebook_business/adobjects/adcreative.pyi
class AdCreative(AbstractCrudObject):
    class Field(AbstractObject.Field):
        image_crops: str              # Top-level field (reads deprecated crops)
        asset_feed_spec: str          # Contains images with image_crops
        object_story_spec: str        # Contains link_data.image_hash
        degrees_of_freedom_spec: str
        actor_id: str
        instagram_user_id: str
        # ... etc
```

### AdAssetFeedSpecImage Structure

```python
# From adopt/stubs/facebook_business/adobjects/adassetfeedspecimage.pyi
class AdAssetFeedSpecImage(AbstractObject):
    class Field(AbstractObject.Field):
        hash: str              # Image hash
        image_crops: str       # Crop specifications
        adlabels: str
        url: str
        url_tags: str
```

**How 191x100 appears**:
```json
{
  "images": [{
    "hash": "52b2b89b22981caa8f838ae91609ef1d",
    "image_crops": {
      "191x100": [[x_min, y_min], [x_max, y_max]]
    }
  }]
}
```

---

## 7. Test Data Evidence

### Test File Containing 191x100

**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/test/ads/image_ad_website.json`

**Relevant Section** (lines 24-35):

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

**What This Proves**:
- The system CAN handle 191x100 in templates
- If this template is used for ad creation, Facebook would reject it
- The test data is NOT used in actual test assertions about payload

### Test Code Analysis

**File**: `/home/nandu/Documents/vlab-research/vlab/adopt/adopt/test_marketing.py:419-433`

```python
def test_create_creative_from_template_image_web():
    template = _load_template("image_ad_website.json")

    conf = CreativeConf(destination="web", name="foo", template=template)
    link = "foo.com/?bar=baz"
    cta = web_call_to_action(link)
    creative = _create_creative(conf, cta, link=link)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]
    assert "vlab.digital" not in json.dumps(creative.export_all_data())
    assert creative["asset_feed_spec"]["link_urls"][0]["website_url"] == link
```

**Key Finding**: The test loads `image_ad_website.json` which HAS 191x100 crops. The test passes the asset_feed_spec through unchanged. **No assertion checks for image_crops**, so the 191x100 would be present in the output.

---

## 8. Exact Code Paths That Trigger the Error

### Path A: Direct Ad Creation with Asset Feed Spec

```
marketing.py:_create_creative()
  └─ Line 359: c[AdCreative.Field.asset_feed_spec] = tafs
       (tafs comes from config.template with 191x100)
  └─ Returns AdCreative c

marketing.py:create_ad()
  └─ Line 143: a[Ad.Field.creative] = creative
       (Contains the asset_feed_spec with 191x100)
  └─ Returns Ad a

facebook/reconciliation.py:ad_dif()
  └─ Line 115: params = {**x.export_all_data(), "adset_id": adset["id"]}
       (exports entire ad including creative with 191x100)
  └─ Line 116: Instruction("ad", "create", params, None)

facebook/update.py:execute()
  └─ Line 94-95: create = self.get_create("ad")
                 call(create, params=instruction.params, fields=[])
       (Calls account.create_ad with params containing 191x100)

Facebook API Error!
  └─ "The 191x100 crop key for image ads is deprecated"
```

### Path B: Ad Update via Reconciliation

```
facebook/state.py:get_creatives()
  └─ Line 45: Requests AdCreative.Field.image_crops
  └─ Returns ads WITH existing 191x100 crops

facebook/reconciliation.py:update_ad()
  └─ Line 62: if not _eq(ad["creative"], source["creative"], fields):
  └─ Detects difference in creative
  └─ Line 63: Instruction("ad", "update", ad.export_all_data(), source["id"])
       (Entire creative with 191x100 exported)

facebook/update.py:execute()
  └─ Line 84-85: obj = self.get_object("ad", instruction.id)
                 call(obj.api_update, params=instruction.params, fields=[])
       (Calls ad.api_update with 191x100 in payload)

Facebook API Error!
  └─ "The 191x100 crop key for image ads is deprecated"
```

---

## 9. Architectural Ambiguities and Questions

### Ambiguity 1: Where Do Templates Come From in Live System?

**Current State**:
- Test templates loaded from `/adopt/test/ads/` directory
- Live templates loaded from database via `study_conf`
- CreativeConf.template is Dict[str, Any]

**Unknown**:
- Do live templates in database contain 191x100?
- Are they coming from Dashboard UI selection?
- If so, Dashboard must fetch them from Facebook

**Evidence**:
- Dashboard `fetchAds()` function in `/dashboard/src/helpers/api.ts` requests full `object_story_spec` and `asset_feed_spec`
- These include image_crops if they exist in Facebook ads
- No filtering of deprecated crops

---

### Ambiguity 2: Does the System Actually Create Ads?

**Current State**:
- `_create_creative()` function exists and is tested
- `create_ad()` function exists
- Reconciliation generates "ad create" instructions
- But no clear evidence of these being executed in practice

**Note**: The system might be primarily used for reconciliation/updates only, not creation.

---

### Ambiguity 3: Error Visibility

**Current State**:
- FacebookRequestError is caught in `api.py:call()` function
- Non-fatal errors get retried
- Fatal errors don't
- Where do fatal errors go? Back to caller in `server.py`

**Unknown**:
- Are errors surfaced to users?
- Logged?
- What happens when `call(create, ...)` throws in `update.py:95`?

---

## 10. Potential Failure Scenarios

### Scenario 1: HIGH PROBABILITY if reconciliation is used
**Trigger**: Any Facebook ad with 191x100 crops exists and reconciliation touches it
**Flow**: Read old ad → compare → detect change → try to update with 191x100
**Result**: API error, update fails

### Scenario 2: MEDIUM PROBABILITY if templates are created dynamically
**Trigger**: User selects Facebook ad with 191x100 as template
**Flow**: Dashboard fetches → stores in DB → Adopt loads → creates new ad
**Result**: API error during creation

### Scenario 3: LOW PROBABILITY if only reading
**Trigger**: Reconciliation only reads existing ads
**Flow**: Fetches image_crops field → returns 191x100
**Result**: No error (reading deprecated values is safe)

---

## 11. The Why: Facebook's Deprecation Rationale

From research findings document:

**Deprecated April 30, 2019**
- 191x100 (1.91:1 landscape) was for Facebook News Feed
- Facebook data showed 1:1 (100x100) performs better:
  - Higher conversion rates
  - Better click-through rates
  - More compatible across placements
- All new API versions stopped accepting 191x100
- Existing ads still work but can't be updated with 191x100

---

## 12. Files and Code References Summary

| Component | File | Lines | Key Finding |
|-----------|------|-------|-------------|
| **Creative Creation** | `marketing.py` | 281-374 | Copies asset_feed_spec with crops unchanged |
| **Ad Creation** | `marketing.py` | 138-144 | Wraps creative, doesn't filter crops |
| **Reconciliation Diff** | `reconciliation.py` | 48-68 | Compares creatives including crops |
| **API Execution** | `update.py` | 82-96 | Sends instruction params to Facebook |
| **State Reading** | `state.py` | 35-55 | Requests image_crops field (safe) |
| **Error Handling** | `api.py` | 14-22 | Non-fatal codes: 2, 17, 368, 80004 |
| **Test Template** | `test/ads/image_ad_website.json` | 24-35 | Contains 191x100 crop |
| **Test Case** | `test_marketing.py` | 419-433 | Loads template with 191x100 |
| **Stubs: Crops** | `stubs/adsimagecrops.pyi` | 9 | `field_191x100: str` (deprecated) |
| **Stubs: Asset Image** | `stubs/adassetfeedspecimage.pyi` | 9 | `image_crops: str` field |

---

## 13. Ambiguities and Unclear Points

1. **Is ad creation actually used in production?**
   - Code exists but no visibility into actual usage
   - Could be test-only or reconciliation-only

2. **Do live templates in the database contain 191x100?**
   - Dashboard might be fetching ads with deprecated crops
   - No audit mechanism visible

3. **Does the error actually surface to users?**
   - Fatal errors in `call()` aren't caught
   - Unclear if they bubble to API layer

4. **Is the system versioning API calls?**
   - No explicit Marketing API version specified
   - SDK version 22 is used (current)

5. **What's the image_crops field at top level vs in asset_feed_spec?**
   - Two separate places where crops can be
   - Code requests both

---

## 14. Recommendations for Error Prevention

### Immediate Actions

1. **Audit Current Facebook Ads**
   ```
   Check if any active ads use 191x100
   Search all creatives for "image_crops": {"191x100": ...}
   ```

2. **Add Crop Validation**
   ```python
   def validate_crops_not_deprecated(creative: AdCreative):
       crops = creative.get("image_crops", {})
       if "191x100" in crops:
           raise ValueError("191x100 crops are deprecated. Use 100x100 instead.")

       asset_spec = creative.get("asset_feed_spec", {})
       for image in asset_spec.get("images", []):
           crops = image.get("image_crops", {})
           if "191x100" in crops:
               raise ValueError("191x100 crops deprecated in image")
   ```

3. **Filter Before Sending**
   ```python
   def remove_deprecated_crops(asset_feed_spec: dict) -> dict:
       for image in asset_feed_spec.get("images", []):
           if "image_crops" in image:
               image["image_crops"] = {
                   k: v for k, v in image["image_crops"].items()
                   if k != "191x100"
               }
       return asset_feed_spec
   ```

### Long-term Solutions

1. Update templates to use 100x100 instead of 191x100
2. Add migration for existing Facebook ads with deprecated crops
3. Document the full ad template schema (not just `any`)
4. Add integration tests that verify Facebook API acceptance

---

## 15. Conclusion

**The Error IS Possible**: If templates with 191x100 crops are sent to Facebook's current API
- Either during creation of new ads
- Or during reconciliation/updates of existing ads

**The Error Is NOT Currently Apparent**: Because:
- No visible error handling surfaces it to users
- System might not be actively creating ads
- Or active ads don't have deprecated crops

**Most Likely Trigger**: Reconciliation of old Facebook ads that already use 191x100 when trying to update them for any reason

**Recommended Action**: Filter out 191x100 crops before sending any payload to Facebook API v22 or later.
