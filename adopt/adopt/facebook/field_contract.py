"""What we compare against Facebook, and why.

`reconciliation._eq` decides whether a live ad or adset still matches what the
study config says it should be. Anything listed in COMPARED_AD / COMPARED_ADSET
is part of that decision; anything else Facebook returns is ignored.

Adding a field here is not free. If Facebook does not echo a field back exactly
as we sent it, every run will see a difference and rewrite the object — forever.
That is not hypothetical: `image_text_translation` did precisely this, costing
~360 no-op ad writes a day against a single ad account until 2026-07-30, and
contributing to `code 17 / Ad Account Has Too Many API Calls` throttling. See
planning/field-contract.md.

Keep this file honest with `adopt-probe`, which compares these declarations
against live ads and tells you what changed.
"""

from typing import Dict

# Ad creative fields we compare. The ad's referral `ref` — which decides
# which survey a respondent enters — lives in three of them, so drift here
# is not cosmetic.
COMPARED_AD: Dict[str, str] = {
    "object_story_spec": (
        "Holds page_welcome_message, whose quick-reply payload carries the "
        "referral ref. Wrong value recruits people into the wrong survey."
    ),
    "asset_feed_spec": (
        "Ad copy variants, plus additional_data.page_welcome_message — the "
        "same ref again for Advantage+ delivery."
    ),
    "url_tags": "The ref as a click parameter (ref=creative.<name>....).",
    "degrees_of_freedom_spec": (
        "Advantage+ creative opt-ins. Which enhancements Facebook may apply "
        "to our creative changes what respondents actually see."
    ),
    "actor_id": "The Facebook page the ad posts as.",
    "instagram_user_id": "The Instagram account the ad runs under.",
    "image_crops": "Crop spec for the creative image.",
    "contextual_multi_ads": "Opt-in for contextual multi-ads placement.",
}

# Adset fields we compare.
COMPARED_ADSET: Dict[str, str] = {
    "targeting": "Who the stratum recruits — the study design itself.",
    "daily_budget": "Set every run by the optimizer; drift means overspend.",
    "end_time": "Flight end, from the study's recruitment window.",
    "status": "ACTIVE vs PAUSED — a paused stratum recruits nobody.",
    "optimization_goal": "What Facebook optimizes delivery for.",
    "name": "The stratum id. Adsets are matched to strata by this.",
}


# Fields Facebook accepts on write but never echoes back on read.
#
# These must not count as differences. We send the field, Facebook stores it
# (or silently ignores it) but omits it from the response, we see it missing,
# we write again — every run, forever.
#
# Paths are dotted, relative to the compared object (the creative for ads, the
# adset for adsets), matching the paths `_eq` walks.
#
# Managed by `adopt-probe --update`. Edit by hand if you like; the tool
# rewrites everything between the markers below.
#
# BEGIN DROPPED (managed by adopt-probe)
DROPPED: Dict[str, str] = {
    "degrees_of_freedom_spec.creative_features_spec.image_animation": (
        "Sent by adopt, absent from Facebook's response. Confirmed live 2026-08-01 "
        "by adopt-probe."
    ),
    "degrees_of_freedom_spec.creative_features_spec.image_brightness_and_contrast": (
        "Sent by adopt, absent from Facebook's response. Confirmed live 2026-08-01 "
        "by adopt-probe."
    ),
    "degrees_of_freedom_spec.creative_features_spec.image_templates": (
        "Sent by adopt, absent from Facebook's response. Confirmed live 2026-08-01 "
        "by adopt-probe."
    ),
    "degrees_of_freedom_spec.creative_features_spec.image_text_translation": (
        "We send enroll_status OPT_IN; Facebook returns ~82 creative_features_spec "
        "keys and this is never among them. Confirmed live 2026-07-30."
    ),
    "degrees_of_freedom_spec.creative_features_spec.image_touchups": (
        "Sent by adopt, absent from Facebook's response. Confirmed live 2026-08-01 "
        "by adopt-probe."
    ),
    "degrees_of_freedom_spec.creative_features_spec.text_optimizations": (
        "Sent by adopt, absent from Facebook's response. Confirmed live 2026-08-01 "
        "by adopt-probe."
    ),
}
# END DROPPED (managed by adopt-probe)


def is_dropped(path: str) -> bool:
    """True if Facebook is known not to echo `path` back.

    `_eq` builds paths with a leading dot (".degrees_of_freedom_spec..."),
    so normalise before looking up.
    """
    return path.lstrip(".") in DROPPED
