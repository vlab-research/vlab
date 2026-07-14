# Facebook Extraction: Advantage+ Audience + age_min conflict

## Problem
When creating or editing adsets from a template that uses **Advantage+ Audience**
(`targeting_automation.advantage_audience`), Facebook rejects the request if the
extracted targeting includes `age_min` set to a value higher than 25.

### Example error
```
Error: Message: Call was not successful
Method: POST
Path: https://graph.facebook.com/v22.0/<adset_id>
Params: {
  targeting: '{"age_max":65,"age_min":30,"custom_audiences":[],...,"targeting_automation":{"advantage_audience":0,...}}',
  ...
}
Status: 400
Response: {
  "error": {
    "message": "Invalid parameter",
    "type": "OAuthException",
    "code": 100,
    "error_subcode": 1870188,
    "error_user_title": "With ad sets that use Advantage+ audience, the minimum age audience control can’t be set to higher than 25",
    "error_user_msg": "You can add a higher minimum age as a suggestion instead when creating or editing ad set."
  }
}
```

## When it happens
1. User selects a template adset that has `targeting_automation` enabled
   (Advantage+ Audience).
2. The dashboard extracts `age_min` (and possibly `age_max`) from the template
   adset's targeting.
3. The user saves variables and strata, then tries to recruit / create new
   adsets from those strata.
4. Facebook rejects the new adset because the combination of Advantage+ Audience
   and `age_min >= 26` is disallowed.

## Root cause
The extraction logic in `dashboard/src/pages/StudyConfPage/forms/variables/extract.ts`
currently extracts the requested properties verbatim. It does not account for
Facebook's API rules that disallow certain combinations, specifically:

- Advantage+ Audience + `age_min` > 25
- Possibly other combinations (e.g., Advantage+ Audience + explicit gender?)

## Affected files
- `dashboard/src/pages/StudyConfPage/forms/variables/extract.ts`
  - Pure extraction function. Needs to be aware of `targeting_automation` rules.
- `dashboard/src/pages/StudyConfPage/forms/variables/Variable.tsx` and
  `Level.tsx`
  - UI that displays extracted targeting. May need to show warnings or filtered
    properties.
- Any downstream code that uses `facebook_targeting` to create adsets
  (likely in `adopt/` or the recruitment pipeline).

## Possible solutions

### Option A: Filter out disallowed properties during extraction
When `targeting_automation.advantage_audience` (or similar) is present, do not
extract `age_min` / `age_max`. Show a warning in the UI that age was skipped
because of Advantage+ Audience.

Pros: Simple, keeps the extraction automatic.
Cons: User may not realize age is not being applied.

### Option B: Transform targeting before creating adsets
Keep extraction as-is, but when the recruitment pipeline creates a new adset,
strip or transform `age_min`/`age_max` based on `targeting_automation`.

Pros: Extraction remains faithful to the template.
Cons: Fixes the problem later, may surprise users if the dashboard shows one
thing and Facebook receives another.

### Option C: Warn the user and require manual fix
Detect the conflict and show a clear message: "This adset uses Advantage+
Audience, which does not allow age_min > 25. Either lower the minimum age or
disable Advantage+ Audience in Meta."

Pros: Transparent, respects Facebook's constraints.
Cons: Blocks the user until they fix it on Meta.

### Option D: Use "age suggestion" API parameter
Facebook's error message says "You can add a higher minimum age as a suggestion
instead when creating or editing an ad set." Investigate whether there is a
separate parameter for age suggestions when Advantage+ Audience is enabled.

Pros: Could preserve the user's intent.
Cons: Requires research into Facebook's ad suggestion API.

## Recommended next step
Research Facebook's current documentation for Advantage+ Audience constraints
and age suggestion parameters. Then implement Option A or D in the extraction
layer, with a visible warning in the UI.

## Related
- `dashboard/src/pages/StudyConfPage/forms/variables/extract.ts`
- `dashboard/src/pages/StudyConfPage/forms/variables/extract.test.ts`
- `dashboard/src/pages/StudyConfPage/forms/shared/TargetingSummary.tsx`
