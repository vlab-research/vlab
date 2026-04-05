# Facebook Ads API Image Crop Deprecation - Research Findings

## Executive Summary

The "191x100" crop key for Facebook image ads was deprecated as of **April 30, 2019** when the latest Marketing API version was released. While older API versions continued to support it until their expiration, newer versions no longer allow ads to leverage this landscape aspect ratio (1.91:1).

## Current State of the Codebase

The vlab project currently uses **facebook-business SDK v22** (specified in `/home/nandan/Documents/vlab-research/vlab/adopt/pyproject.toml`), which is a relatively recent version supporting Meta's latest APIs.

The codebase references `image_crops` field in:
- `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/facebook/state.py` (line 45)
- `/home/nandan/Documents/vlab-research/vlab/adopt/adopt/facebook/reconciliation.py` (line 52)

## The 191x100 Crop Key Deprecation

### What is 191x100?

- **Format**: `field_191x100 = '191x100'`
- **Aspect Ratio**: 1.91:1 (landscape/widescreen format)
- **Purpose**: Originally used for Facebook News Feed link ads and image ads displayed in a horizontal layout
- **Pixel Example**: A 191x100 crop represents a 191-pixel-wide by 100-pixel-tall image

### Deprecation Timeline

- **Deprecation Date**: April 30, 2019
- **Current Status**: Deprecated across all latest Meta API versions
- **Legacy Support**: Previous API versions (now expired) continued to support 191x100 until their deprecation dates
- **Why Deprecated**: Facebook's testing showed that 1:1 square images had:
  - Higher conversion rates
  - Improved click-through rates (CTR)
  - Better compatibility across placements (Facebook and Instagram)

### The Deprecation Mechanism

According to Meta's approach:
1. New API versions stopped accepting the 191x100 crop key
2. Ads using 191x100 must be manually updated before parameters can be automatically added
3. Existing legacy implementations need migration paths

## Supported Image Crop Dimensions (Current)

The `AdsImageCrops` class in the facebook-business SDK v22 (from `/home/nandan/Documents/vlab-research/vlab/adopt/.venv/lib/python3.10/site-packages/facebook_business/adobjects/adsimagecrops.py`) supports the following crop dimensions:

```python
class Field(AbstractObject.Field):
    field_100x100 = '100x100'      # Square (1:1) - PRIMARY REPLACEMENT
    field_100x72 = '100x72'         # Landscape variant
    field_191x100 = '191x100'       # DEPRECATED - Still in SDK for legacy compatibility
    field_400x150 = '400x150'       # Landscape
    field_400x500 = '400x500'       # Vertical/portrait
    field_600x360 = '600x360'       # Landscape
    field_90x160 = '90x160'         # Vertical/portrait
```

All fields are typed as `'list<list>'`, expecting coordinate arrays for crop specifications.

## Replacement Approach

### Primary Replacement: 100x100 (1:1 Square)

**When to use**: For image ads, link ads, and anywhere 191x100 was previously used.

**Advantages**:
- Recommended by Facebook for broader placement compatibility
- Works across Facebook, Instagram, and Audience Network
- Better visual consistency
- No automatic cropping artifacts

**Image Size Recommendations**:
- Minimum: 1080 x 1080 pixels
- Recommended: Use the same image dimensions as your crop aspect ratio

### Secondary Alternatives by Use Case

Based on placement/format:
- **Feed posts**: 1:1 (100x100) or 4:5 (400x500)
- **Stories/Reels**: 9:16 (90x160)
- **Landscape placements**: 400x150 or 600x360
- **Carousel ads**: 100x100 primary, with fallbacks to other ratios

## API Version Context

### Facebook Business SDK Version

- **Current in vlab**: facebook-business v22
- **Last Release Checked**: v22 includes support for Meta Graph API v22.0 and Marketing API v22.0 (released January 21, 2025)

### Marketing API Versions

**Currently Supported (February 2026)**:
- Marketing API v22.0+ (latest)
- v21.0 still supported but being phased out
- v20.0 deprecated effective May 6, 2025

**Minimum Recommended**:
- Use Marketing API v22.0 or higher for any new ad creation
- Older versions should be updated by January 2026

## Implementation Details

### The `image_crops` Field Structure

In the Facebook API, image crops are specified as a JSON object mapping crop keys to coordinate arrays:

```json
{
  "image_crops": {
    "100x100": [[0, 0], [1080, 1080]],
    "400x500": [[0, 0], [400, 500]]
  }
}
```

Where each crop is specified as `[[x_start, y_start], [x_end, y_end]]`.

### Current Code Usage in vlab

The `adopt` module fetches and reconciles ad creatives with:

```python
# From state.py - line 45
fields = [
    AdCreative.Field.actor_id,
    AdCreative.Field.image_crops,    # This field includes 191x100 in metadata
    AdCreative.Field.asset_feed_spec,
    # ... other fields
]

# From reconciliation.py - line 52
fields = [
    AdCreative.Field.actor_id,
    AdCreative.Field.image_crops,    # Compared during reconciliation
    # ... other fields
]
```

## Migration Recommendations

### Immediate Action Items

1. **Audit Current Ads**: Check if any active ads in the system use 191x100 crops
   - Query the Facebook API with image_crops field
   - Filter for any crops with "191x100" key

2. **No Code Change Required (Currently)**:
   - The facebook-business SDK v22 still includes `field_191x100` in the AdsImageCrops class
   - This is for backward compatibility and reading legacy data
   - The API will reject attempts to **create** ads with 191x100 crops

3. **Future-Proof Implementation**:
   - When creating new ads via the API, explicitly use 100x100 crops instead of 191x100
   - Provide fallback crop options (100x100 primary, with alternatives)

### Code Example: Proper Image Crop Specification

Instead of specifying 191x100 crops:
```python
# OLD (will fail with current API)
image_crops = {
    "191x100": [[0, 0], [1920, 1000]]
}

# NEW (correct approach)
image_crops = {
    "100x100": [[0, 0], [1080, 1080]],
    "400x500": [[0, 0], [800, 1000]]  # Optional fallback
}
```

## Potential Issues with Current Code

### Risk Assessment: **LOW**

The codebase is currently:
- **Reading** image_crops from existing ads (safe - still supported)
- **Not creating** new ads with deprecated specs (no direct risk)
- **Reconciling** creative specs (comparing only, not modifying crop specs)

### Scenarios Where This Could Break

1. **External API Changes** (unlikely but possible):
   - If Meta removes 191x100 from responses entirely
   - Mitigation: Filter out deprecated crop keys when processing

2. **If Adopt Starts Creating Ads**:
   - If the adoption system begins creating ads with image_crops
   - Current code would need to:
     - Remove any 191x100 specifications
     - Ensure 100x100 is always included
     - Validate crops match actual image dimensions

## Facebook API Versions and Timeline

### Current Deprecation Landscape (February 2026)

| Version | Status | Key Changes |
|---------|--------|-------------|
| v24.0 | Current | Latest; media_type_automation changes for Catalog Ads |
| v22.0 | Current (Jan 2025) | Advantage+ Creative Standard Enhancements deprecation |
| v21.0 | Active but aging | Image Expansion as Standard Enhancement |
| v20.0 | Deprecated (May 6, 2025) | No longer accepting requests |
| v19.0 | Deprecated (Feb 4, 2025) | No longer accepting requests |
| Older | End of Life | Not supported |

### Recommended Action

Ensure any new API calls use **v22.0 or higher** exclusively. The facebook-business SDK v22 in vlab aligns with Marketing API v22.0, so this is already correct.

## References and Documentation

### Sources Referenced in This Research

1. **Facebook Ads Deprecation**: The 191x100 crop was deprecated April 30, 2019 when Facebook recommended transitioning to 1:1 square (100x100) aspect ratio due to performance improvements
   - Sources: Digital Information World, Feedonomics, Marpipe

2. **Current SDK Implementation**: facebook-business Python SDK v22 maintains backward compatibility by including the deprecated field but rejects its use in create operations

3. **Marketing API v21.0 and v22.0 Changes**:
   - v22.0 (Jan 21, 2025): Advantage+ Creative bundles changes
   - v21.0 (Oct 2024): Image Expansion as standard enhancement
   - Sources: ppc.land, Swipe Insight, Meta changelog

4. **Current Image Specifications**:
   - Supported crops: 100x100, 100x72, 400x150, 400x500, 600x360, 90x160
   - 191x100 no longer supported for new ads
   - Sources: Shopify, Hootsuite, Marpipe guides (2026)

## Conclusion

The vlab codebase is **well-positioned** regarding this deprecation:

1. Using a recent SDK version (v22) aligned with current APIs
2. Not creating new ads with deprecated specs
3. Maintaining backward compatibility for reading legacy data

**No immediate action required**, but the codebase should be prepared for:
- Filtering out 191x100 crops if/when they appear
- Using 100x100 crops when implementing ad creation features
- Staying current with Meta API version updates (minimum v22.0)

