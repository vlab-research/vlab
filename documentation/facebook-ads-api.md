# Facebook Ads API Integration Documentation

## Overview

This document provides guidance on integrating with Meta's (formerly Facebook's) Marketing API for ad campaign management and creative development. The vlab project uses the `facebook-business` Python SDK to interact with Facebook's advertising platform.

## Current Implementation

### SDK Version

- **Package**: `facebook-business`
- **Version**: v22 (specified in `/adopt/pyproject.toml`)
- **API Version**: Marketing API v22.0
- **Release Date**: January 21, 2025

### Usage in vlab

The codebase uses the facebook-business SDK in the `adopt` module to:
1. Query ad campaigns and their status
2. Fetch ad sets, ads, and creative specifications
3. Retrieve insights and performance metrics
4. Manage and reconcile ad account state

## Key Components

### Main Integration Files

- **State Management**: `/adopt/adopt/facebook/state.py`
  - Fetches campaigns, ad sets, ads, and creatives
  - Manages API authentication and session
  - Caches campaign state for performance

- **Reconciliation**: `/adopt/adopt/facebook/reconciliation.py`
  - Compares current state with desired state
  - Generates update instructions for ads and ad sets
  - Detects diffs in creative specifications

- **API Wrapper**: `/adopt/adopt/facebook/api.py`
  - Handles low-level API calls
  - Implements error handling and retry logic

## Image Creative Specifications

### Image Crop Keys and Aspect Ratios

Facebook supports multiple image crop specifications for different placements. The `image_crops` field in ad creatives specifies how images should be cropped for different contexts:

| Crop Key | Dimensions | Aspect Ratio | Use Case |
|----------|-----------|--------------|----------|
| `100x100` | Square | 1:1 | Feed, Instagram, Audience Network (PRIMARY) |
| `100x72` | Landscape | ~1.4:1 | Landscape placements |
| `400x150` | Landscape | ~2.67:1 | Wide landscape placements |
| `400x500` | Vertical | 0.8:1 | Stories, Reels, vertical placements |
| `600x360` | Landscape | 1.67:1 | Larger landscape placements |
| `90x160` | Vertical | 0.56:1 | Stories/Reels (9:16) |
| `191x100` | Landscape | 1.91:1 | **DEPRECATED - Do not use** |

### Deprecated Crop Key: 191x100

**Status**: Deprecated as of April 30, 2019

The 191x100 crop key (1.91:1 aspect ratio) is no longer supported for creating new ads in the latest Marketing API versions. While the facebook-business SDK v22 still includes this field for backward compatibility (reading legacy data), attempting to create or update ads with 191x100 crops will fail.

**Migration Path**: Use `100x100` (1:1 square) crops instead. Facebook's testing showed:
- Higher conversion rates with square images
- Better click-through rates
- Improved compatibility across placements

### Image Crop Format

Image crops are specified as coordinate arrays within the `image_crops` field:

```python
image_crops = {
    "100x100": [
        [x_start, y_start],
        [x_end, y_end]
    ],
    "400x500": [
        [x_start, y_start],
        [x_end, y_end]
    ]
}
```

**Example** (for a 1080x1080 image):
```python
image_crops = {
    "100x100": [[0, 0], [1080, 1080]]
}
```

### Image Dimension Recommendations

- **Minimum Image Size**: 1080 x 1080 pixels (for 1:1 ratio)
- **Maximum File Size**: 30 megabytes
- **Supported Formats**: JPG, PNG
- **Quality**: Use high-quality images to avoid automatic resizing artifacts

**Safe Zones** (what not to crop):
- Top: 14% minimum clearance
- Bottom: 35% minimum clearance
- Sides: 6% minimum clearance each

This ensures text, logos, and important creative elements aren't cut off during cropping or display.

## Ad Creative Fields

The vlab adoption system fetches the following fields from the Facebook API when retrieving ad creatives:

```python
fields = [
    AdCreative.Field.actor_id,                    # Account/page creating the ad
    AdCreative.Field.image_crops,                 # Image crop specifications
    AdCreative.Field.asset_feed_spec,             # Feed asset specifications
    AdCreative.Field.degrees_of_freedom_spec,     # Creative flexibility options
    AdCreative.Field.instagram_user_id,           # Instagram account ID
    AdCreative.Field.object_story_spec,           # Story object specifications
    AdCreative.Field.thumbnail_url,               # Creative thumbnail
    AdCreative.Field.contextual_multi_ads,        # Multi-ad context
    AdCreative.Field.url_tags,                    # URL tracking parameters
]
```

## API Version Management

### Current Version (February 2026)

- **Marketing API**: v22.0 (Current)
- **Graph API**: v22.0 (Current)
- **Minimum Required**: v22.0
- **Recommended**: Use v22.0 or higher for all new implementations

### Version Deprecation Timeline

| Version | Deprecation Date | Status |
|---------|------------------|--------|
| v19.0 | February 4, 2025 | Expired |
| v20.0 | May 6, 2025 | Expired |
| v21.0 | TBD (2025) | Active but aging |
| v22.0 | TBD (2026+) | Current/Stable |

### Migration Strategy

Ensure your implementation:
1. Uses Marketing API v22.0 or higher
2. Doesn't depend on deprecated endpoints
3. Updates image crop specifications away from 191x100
4. Monitors Meta's API changelog for breaking changes

## Authentication

### Setup

The facebook-business SDK requires:
- Facebook App ID: `FACEBOOK_APP_ID` environment variable
- Facebook App Secret: `FACEBOOK_APP_SECRET` environment variable
- Access Token: User-provided or obtained via OAuth flow

### Implementation in vlab

```python
from facebook_business.session import FacebookSession
from facebook_business.api import FacebookAdsApi

def get_api(env, token: str) -> FacebookAdsApi:
    session = FacebookSession(
        env("FACEBOOK_APP_ID"),
        env("FACEBOOK_APP_SECRET"),
        token
    )
    api = FacebookAdsApi(session)
    return api
```

## Common Operations

### Fetching Campaigns

```python
from facebook_business.adobjects.campaign import Campaign

campaigns = account.get_campaigns(
    fields=[
        Campaign.Field.name,
        Campaign.Field.objective,
        Campaign.Field.status,
        Campaign.Field.created_time,
    ]
)
```

### Fetching Ad Creatives

```python
from facebook_business.adobjects.adcreative import AdCreative

creatives = AdCreative.get_by_ids(
    ids=creative_ids,
    fields=[
        AdCreative.Field.image_crops,
        AdCreative.Field.asset_feed_spec,
        # ... other fields
    ],
    api=api
)
```

### Fetching Insights

```python
insights = adset.get_insights(
    params={
        "time_range": {"since": "2025-01-01", "until": "2025-12-31"}
    },
    fields=[
        "impressions",
        "reach",
        "spend",
        "cpm",
        "ctr",
        "actions",
    ]
)
```

## Error Handling

The facebook-business SDK can raise various exceptions:

- `FacebookRequestError`: API request failed
- `FacebookBadObjectError`: Invalid object/parameters
- `FacebookAuthError`: Authentication/authorization failed

Implement proper error handling and retry logic when calling the API, especially for rate limiting scenarios.

## Best Practices

### 1. Use Recent API Versions

- Always target v22.0 or higher
- Plan migration paths for deprecated fields
- Monitor Meta's changelog for breaking changes

### 2. Image Crop Specifications

- **Always** use explicit crop specifications
- **Prefer** 100x100 (1:1 square) for broad compatibility
- **Avoid** deprecated 191x100 crops
- **Provide** multiple crop options when possible (100x100, 400x500, etc.)

### 3. API Calls

- Batch requests where possible (get_by_ids for multiple creatives)
- Use field filtering to reduce payload size
- Implement caching for frequently accessed data
- Handle rate limiting gracefully

### 4. Performance Optimization

- Cache campaign/ad set state when possible
- Limit API calls by using targeted field selection
- Break large queries into smaller batches
- Monitor API usage to stay within rate limits

## Troubleshooting

### Common Issues

#### Image Crop Validation Errors

**Problem**: "191x100 crop key for image ads is deprecated"

**Solution**:
- Remove any 191x100 crop specifications
- Use 100x100 (1:1) square crops instead
- Ensure coordinates are within image boundaries

#### API Version Errors

**Problem**: "This field is not available in this API version"

**Solution**:
- Update to Marketing API v22.0 or higher
- Check field availability in current API documentation
- Verify facebook-business SDK version matches API requirements

#### Authentication Failures

**Problem**: "Invalid token" or "App not authorized"

**Solution**:
- Verify Facebook App ID and Secret are correct
- Ensure user token has ad account access
- Check token hasn't expired
- Verify app permissions include `ads_read`, `ads_management`

## Resources

- **Official Documentation**: https://developers.facebook.com/docs/marketing-apis
- **Python SDK Repository**: https://github.com/facebook/facebook-python-business-sdk
- **Python SDK Releases**: https://github.com/facebook/facebook-python-business-sdk/releases
- **API Changelog**: Check Meta Developers site for latest updates

## Future Considerations

1. **Image Expansion Feature** (v21.0+): Implement standard image enhancement features if using Advantage+ Creative
2. **API Deprecations**: Monitor for additional crop key deprecations or format changes
3. **SDK Updates**: Keep facebook-business SDK updated for security and feature improvements
4. **Performance**: Consider pagination strategies if handling large numbers of ads/creatives

