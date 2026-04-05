# Feasibility Analysis: Sourcing `advantage_audience` from Facebook Frontend

## Executive Summary

**Feasibility**: ⚠️ **UNCERTAIN** - Depends on whether Facebook includes `targeting_automation` in the ad set's targeting field when fetched via the Graph API.

**Current Status**: Not feasible without additional investigation of Facebook API response structure.

**Recommendation**: Check Facebook API documentation or test actual response to determine if `targeting_automation` is included.

---

## Question: Can Dashboard Fetch `advantage_audience` from Existing Facebook Ad Sets?

### Current System Capability

**Yes**, the dashboard architecture is fully capable of:
1. Fetching ad set targeting fields from Facebook
2. Extracting specific properties
3. Storing them in the database
4. Passing them to the backend

**The mechanism already exists** - it's used for all other targeting properties (age_min, genders, etc.).

### The Real Question: Does Facebook Include It?

When the dashboard fetches ad sets with:
```
GET /graph.facebook.com/campaign/adsets?fields=name,id,targeting
```

**Does the `targeting` field include `targeting_automation` with `advantage_audience` flag?**

**Unknown** - This hasn't been verified in the codebase.

---

## Technical Path: If Facebook Does Include It

If `targeting_automation` IS in the fetched targeting field, here's what would be needed:

### 1. Add to Extractable Properties (5-minute change)

**File**: `/dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx`, lines 85-94

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
  // ADD THIS:
  { name: 'targeting_automation', label: 'Targeting Automation' },
];
```

### 2. Update Level Extraction Logic (No change needed)

The extraction logic in `Level.tsx` (lines 30-45) already handles nested properties generically:

```typescript
const targeting = properties.reduce(
  (obj, key) => ({ ...obj, [key]: adset.targeting[key] }),  // Extracts ANY property
  {}
);
```

This would automatically handle `targeting_automation` even though it's a nested object.

### 3. Verify Type Definitions (Already compatible)

The type system is already flexible:

```typescript
// From /dashboard/src/types/conf.ts, line 113
facebook_targeting: any;  // Accepts any structure
```

And in the backend:

```typescript
// From /api/internal/types/studyconf.go, line 333
type FacebookTargeting map[string]interface{}  // Accepts any keys and nested structures
```

**No type definition changes needed.**

### 4. Database Already Compatible

The JSON column in the database can store nested structures:

```json
{
  "age_min": 18,
  "targeting_automation": {
    "advantage_audience": 1
  }
}
```

**No migration needed.**

### 5. Backend Must Still Handle It

The backend's `create_adset()` function in `/adopt/adopt/marketing.py` (line 98) just passes through whatever is in `facebook_targeting`:

```python
targeting = {**c.stratum.facebook_targeting}  # Passes through as-is
adset[AdSet.Field.targeting] = targeting  # Sets on ad set
```

**If `targeting_automation` is in the dict, it will be passed to Facebook.**

**This should just work.**

---

## Technical Path: If Facebook Does NOT Include It

If `targeting_automation` is **not** in the fetched targeting field, then:

### Option A: Add Backend Default

**Effort**: 5 minutes
**Location**: `/adopt/adopt/marketing.py`, after line 98

```python
def create_adset(c: AdsetConf) -> AdSet:
    name = c.stratum.id
    targeting = {**c.stratum.facebook_targeting}
    
    # Add required field if not present
    if "targeting_automation" not in targeting:
        targeting["targeting_automation"] = {"advantage_audience": 0}
    
    # Rest of function...
```

### Option B: Add User Configuration Form

**Effort**: 3-4 hours
**Changes Needed**:
1. Create new form component for targeting automation options
2. Store user's choice in Variables or Strata config
3. Pass through to backend
4. Backend retrieves it and includes in ad set creation

---

## Investigation Steps to Resolve

### Step 1: Check Facebook API Documentation
- Search: "Facebook Ads API targeting_automation" 
- Check: Is targeting_automation included in ad set's targeting field response?
- Reference: Facebook's Graph API Explorer

### Step 2: Test with Actual API Call
Run this in the dashboard and inspect the response:

```typescript
const testAdsetFetch = async () => {
  const response = await facebookRequest(
    `/act_YOUR_ACCOUNT_ID/adsets`,
    {
      queryParams: {
        fields: 'name,id,targeting',
        access_token: accessToken,
        limit: 1,
      },
      accessToken,
    }
  );
  console.log(JSON.stringify(response.data[0].targeting, null, 2));
};
```

### Step 3: Check Existing Tests
Look for test data in the codebase showing what's actually in ad set targeting fields.

### Step 4: Verify Facebook SDK Behavior
Check if the Python SDK's AdSet class includes targeting_automation when retrieving from API.

---

## Risk Analysis

### If Extracted from Facebook
- **Risk Level**: Low
- **Main Risk**: If Facebook API response changes or doesn't include the field
- **Mitigation**: Backend can add default if missing
- **Benefit**: Users get exact targeting automation settings from their existing campaigns

### If Hardcoded Backend Default
- **Risk Level**: Very Low
- **Main Risk**: Default value might not match user expectations
- **Mitigation**: Make configurable if complaints arise
- **Benefit**: Works immediately without frontend changes

---

## Recommendation Hierarchy

### If Sourcing from Facebook Is Goal

1. **First**: Investigate if Facebook includes `targeting_automation` in API response
2. **If Yes**: Add to properties list (trivial - 5 minutes)
3. **If No**: Use backend default (trivial - 5 minutes) or build UI (3-4 hours)

### If Just Need to Fix The Error

**Recommendation**: Backend default in `create_adset()` is the fastest path:
- No frontend changes required
- No UI needed
- Works immediately
- Can refine later if needed

### If Want User Control

**Recommendation**: Add form field:
- Allows per-campaign customization
- More effort but maximum flexibility
- Should be combined with backend fallback

---

## Current Blockers

**None** - the system architecture is ready. What's missing is:

1. **Knowledge**: Does Facebook include this field in the API response?
2. **Configuration**: Where should the value come from?
3. **Decision**: Backend default vs. user config vs. Facebook extraction?

---

## Implementation Checklist (If Extracting from Facebook)

- [ ] Verify Facebook API returns `targeting_automation` in ad set targeting field
- [ ] Test actual Facebook API response structure
- [ ] Add property to Variable.tsx properties list (line 85-94)
- [ ] Test end-to-end flow through strata generation
- [ ] Verify backend passes it through unchanged to Facebook API
- [ ] Test ad set creation with the field included
- [ ] Verify no breaking changes to existing targeting fields

**Estimated Time**: 1-2 hours once Facebook API behavior is confirmed

---

## Implementation Checklist (Backend Default)

- [ ] Add to `create_adset()` function in `/adopt/adopt/marketing.py` (after line 98)
- [ ] Choose default value (0 = disabled, 1 = enabled)
- [ ] Test ad set creation with field added
- [ ] Verify backward compatibility with existing ad sets
- [ ] Consider whether to make it configurable

**Estimated Time**: 30 minutes including testing

---

## Files That Would Change (If Extracting from Facebook)

1. `/dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx` (add 1 line)
2. Possibly `/dashboard/src/helpers/api.ts` (if need to update fields param)
3. No backend changes needed
4. No database schema changes needed

---

## Conclusion

**The technical architecture is ready for `targeting_automation` sourcing from Facebook.** The only blocker is confirming whether Facebook includes it in the API response. If it does, implementation takes 5 minutes. If it doesn't, the backend fallback takes 5 minutes instead.

The decision on approach (Facebook extraction vs. backend default vs. user config) should be based on:
- Business requirements
- User needs for customization
- Timeline urgency

All are feasible with the current system design.
