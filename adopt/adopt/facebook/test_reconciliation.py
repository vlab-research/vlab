import logging
from datetime import datetime
from typing import TypeVar

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet

from . import field_contract
from .reconciliation import _eq, ad_dif, adset_dif, update_adset
from .update import Instruction

T = TypeVar("T")


def _adobject(d, T) -> T:
    t = T()
    for k, v in d.items():
        t[k] = v
    return t


def test_eq_with_all_same():
    a, b = _adobject({"id": "foo", "name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"id": "foo", "name": "bar", "foo": "baz"}, AdSet
    )
    assert _eq(a, b)


def test_eq_with_fields_ignores_extra_keys():
    # Top-level reconciliation passes a field list, so server-generated keys
    # like id that are not in the desired object are ignored.
    a, b = _adobject({"name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"id": "foo", "name": "bar", "foo": "baz"}, AdSet
    )
    assert _eq(a, b, fields=["name", "foo"])


def test_eq_without_fields_is_strictly_symmetric():
    # Nested comparisons (e.g. object_story_spec) have no field list, so extra
    # keys in either object must be treated as a difference.
    a, b = _adobject({"name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"id": "foo", "name": "bar", "foo": "baz"}, AdSet
    )
    assert not _eq(a, b)


def test_eq_without_fields_detects_different_values():
    a, b = _adobject({"id": "bar", "name": "foo", "foo": "baz"}, AdSet), _adobject(
        {"name": "bar", "foo": "baz"}, AdSet
    )
    assert not _eq(a, b)


def test_nested_creative_equal_despite_top_level_ad_differences():
    # update_ad compares only the creative sub-object with a field list, so
    # top-level ad differences (id, adset_id) are irrelevant.
    a = {
        "id": "23846326646590518",
        "creative": {
            "id": "23846327900110518",
            "url_tags": "ref=form.extrabasehin.stratumid.07853f76",
            "actor_id": "102998371752603",
            "object_story_spec": {
                "page_id": "102998371752603",
                "link_data": {
                    "image_hash": "3181666208161582c277488a2c2b5fdb",
                },
            },
        },
        "adset_id": "23846317632290518",
        "status": "ACTIVE",
        "name": "vlab-mnm-mother-daughter-voice-be-heard",
    }

    b = {
        "name": "vlab-mnm-mother-daughter-voice-be-heard",
        "status": "ACTIVE",
        "creative": {
            "name": "vlab-mnm-mother-daughter-voice-be-heard",
            "url_tags": "ref=form.extrabasehin.stratumid.07853f76",
            "actor_id": "102998371752603",
            "object_story_spec": {
                "link_data": {
                    "image_hash": "3181666208161582c277488a2c2b5fdb",
                },
                "page_id": "102998371752603",
            },
        },
    }

    assert _eq(a["creative"], b["creative"], fields=[
        "actor_id",
        "image_crops",
        "asset_feed_spec",
        "degrees_of_freedom_spec",
        "instagram_user_id",
        "object_story_spec",
        "contextual_multi_ads",
        "thumbnail_url",
        "url_tags",
    ])


def test_nested_with_dif_name_not_equal():
    a = {
        "id": "23846326646590518",
        "creative": {
            "name": "foo",
            "id": "23846327900110518",
            "url_tags": "ref=form.extrabasehin.stratumid.07853f76",
            "actor_id": "102998371752603",
            "object_story_spec": {
                "page_id": "102998371752603",
                "link_data": {
                    "image_hash": "3181666208161582c277488a2c2b5fdb",
                },
            },
        },
        "adset_id": "23846317632290518",
        "status": "ACTIVE",
        "name": "vlab-mnm-mother-daughter-voice-be-heard",
    }

    b = {
        "name": "vlab-mnm-mother-daughter-voice-be-heard",
        "status": "ACTIVE",
        "creative": {
            "name": "vlab-mnm-mother-daughter-voice-be-heard",
            "url_tags": "ref=form.extrabasehin.stratumid.07853f76",
            "actor_id": "102998371752603",
            "object_story_spec": {
                "link_data": {
                    "image_hash": "3181666208161582c277488a2c2b5fdb",
                },
                "page_id": "102998371752603",
            },
        },
    }

    assert not _eq(a, b)


def _ad(c, adset):
    a = Ad()
    a[Ad.Field.adset_id] = adset["id"]
    a["name"] = c["name"]
    a["creative"] = c
    a["status"] = "ACTIVE"
    return a


def _adset(d):
    d = {
        "name": "foo",
        **d,
        "end_time": "",
        "targeting": {},
        "daily_budget": 1,
        "optimization_goal": "REPLIES",
    }
    return _adobject(d, AdSet)


def test_update_adset_returns_none_if_equal():
    now = datetime.utcnow()

    source = {"status": "active", "daily_budget": 100, "end_time": now, "targeting": {}}
    adset = {"status": "active", "daily_budget": 100, "end_time": now, "targeting": {}}

    instructions = update_adset(_adobject(source, AdSet), _adobject(adset, AdSet))
    assert instructions == []


def test_update_adset_returns_instruction_if_not_equal():
    now = datetime.utcnow()

    source = {
        "status": "active",
        "daily_budget": 50,
        "end_time": now,
        "targeting": {},
        "id": "foo",
    }

    adset = _adset(
        {"status": "active", "daily_budget": 100, "end_time": now}
    ).export_all_data()

    instructions = update_adset(_adobject(source, AdSet), _adobject(adset, AdSet))
    assert instructions == [Instruction("adset", "update", adset, "foo")]


def _conv(adset):
    exp = adset.export_all_data()
    exp = {k: v for k, v in exp.items()}
    return exp


def test_adset_dif_runs_if_paused_and_creates():
    old_adsets = [
        (
            _adset({"id": "foo", "name": "foo", "status": "PAUSED"}),
            [
                _adobject(
                    {
                        "id": "fooad",
                        "adset_id": "foo",
                        "status": "PAUSED",
                        "name": "bar",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                )
            ],
        )
    ]

    new_adsets = [
        (
            _adset({"name": "foo", "status": "ACTIVE"}),
            [
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "bar",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                ),
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "qux",
                        "creative": {"foo": "qux"},
                    },
                    Ad,
                ),
            ],
        ),
        (
            _adset({"name": "bar", "status": "ACTIVE"}),
            [
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "baz",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                )
            ],
        ),
    ]

    instructions = adset_dif(old_adsets, new_adsets)

    assert instructions == [
        Instruction("adset", "update", _conv(new_adsets[0][0]), "foo"),
        Instruction("ad", "update", {"status": "ACTIVE"}, "fooad"),
        Instruction(
            "ad",
            "create",
            {**new_adsets[0][1][1].export_all_data(), "adset_id": "foo"},
            None,
        ),
        Instruction("adset", "create", new_adsets[1][0].export_all_data(), None),
    ]


def test_ad_dif_creates_when_no_running_ads():
    adset = {"id": "ad"}
    running_ads = []
    creatives = [{"name": "newhindi", "actor_id": "111", "url_tags": "123"}]

    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == [
        Instruction(
            "ad",
            "create",
            {
                "adset_id": "ad",
                "name": "newhindi",
                "creative": creatives[0],
                "status": "ACTIVE",
            },
            None,
        ),
    ]


def test_ad_dif_leaves_alone_if_already_running():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "status": "ACTIVE",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        }
    ]

    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "111"}]
    running_ads = [_adobject(d, Ad) for d in running_ads]
    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == []


def test_ad_dif_updates_if_same_name_but_different_creative():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "status": "ACTIVE",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        }
    ]

    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "222"}]
    running_ads = [_adobject(d, Ad) for d in running_ads]
    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions != []


def test_ad_dif_activates_if_currently_paused():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "status": "PAUSED",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        }
    ]

    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "111"}]
    running_ads = [_adobject(d, Ad) for d in running_ads]
    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == [Instruction("ad", "update", {"status": "ACTIVE"}, "foo")]


def test_ad_dif_handles_many():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "name": "hindi",
            "status": "ACTIVE",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        },
        {
            "id": "baz",
            "name": "odia",
            "status": "ACTIVE",
            "creative": {
                "name": "odia",
                "id": "qux",
                "actor_id": "111",
                "url_tags": "123",
            },
        },
    ]

    creatives = [
        {"name": "odia", "actor_id": "111", "url_tags": "123"},
        {"name": "newfoo", "actor_id": "111", "url_tags": "124"},
    ]
    running_ads = [_adobject(d, Ad) for d in running_ads]
    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == [
        Instruction(
            "ad",
            "create",
            {
                "adset_id": "ad",
                "name": "newfoo",
                "creative": creatives[1],
                "status": "ACTIVE",
            },
            None,
        ),
        Instruction("ad", "delete", {}, "foo"),
    ]


def test_ad_dif_leaves_many_alone_if_nothing_to_be_done():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "status": "ACTIVE",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        },
        {
            "id": "baz",
            "status": "ACTIVE",
            "name": "odia",
            "creative": {
                "name": "odia",
                "id": "qux",
                "actor_id": "111",
                "url_tags": "123",
            },
        },
    ]

    running_ads = [_adobject(d, Ad) for d in running_ads]

    creatives = [
        {"name": "hindi", "actor_id": "111", "url_tags": "111"},
        {"name": "odia", "actor_id": "111", "url_tags": "123"},
    ]

    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == []


def test_ad_dif_removes_duplicate_ads_and_updates_other():
    adset = {"id": "ad"}
    running_ads = [
        {
            "id": "foo",
            "status": "ACTIVE",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        },
        {
            "id": "bar",
            "status": "ACTIVE",
            "name": "hindi",
            "creative": {
                "name": "hindi",
                "id": "bar",
                "actor_id": "111",
                "url_tags": "111",
            },
        },
    ]

    running_ads = [_adobject(d, Ad) for d in running_ads]

    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "222"}]

    instructions = ad_dif(adset, running_ads, [_ad(c, adset) for c in creatives])

    assert instructions == [
        Instruction("ad", "delete", {}, "bar"),
        Instruction("ad", "update", _ad(creatives[0], adset).export_all_data(), "foo"),
    ]


def test_ad_dif_updates_when_object_story_spec_format_changes():
    # Regression: photo_data templates are converted to link_data by
    # marketing._create_creative, so the optimizer must detect when an existing
    # ad still uses the old photo_data format.
    adset = {"id": "adset"}

    photo_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "object_story_spec": {
            "page_id": "111",
            "instagram_user_id": "222",
            "photo_data": {
                "caption": "Take our survey!",
                "image_hash": "abc123",
            },
        },
    }

    link_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "object_story_spec": {
            "page_id": "111",
            "instagram_user_id": "222",
            "link_data": {
                "call_to_action": {"type": "MESSAGE_PAGE"},
                "image_hash": "abc123",
                "message": "Take our survey!",
                "link": "https://fb.com/messenger_doc/",
            },
        },
    }

    running_ads = [
        _adobject(
            {
                "id": "foo",
                "status": "ACTIVE",
                "name": "hindi",
                "creative": photo_creative,
            },
            Ad,
        )
    ]

    instructions = ad_dif(adset, running_ads, [_ad(link_creative, adset)])
    assert len(instructions) == 1
    assert instructions[0].node == "ad"
    assert instructions[0].action == "update"
    assert instructions[0].id == "foo"


# ---------------------------------------------------------------------------
# Tests for the subset comparison fix.
#
# Live Facebook data has server-generated keys inside nested structures that
# the desired creative does not have. _eq's field-list mode now propagates
# _subset="a" through recursion, so nested comparisons only check keys present
# in the desired object and ignore extra server-generated keys in the source.
#
# Root cause from production logs (v0.1.72): degrees_of_freedom_spec.
# creative_features_spec had ~70 extra OPT_OUT keys from Facebook that the
# desired creative didn't set, causing 62 false-positive ad updates per run.
# ---------------------------------------------------------------------------

# Field list used by update_ad() — mirrors the real production list.
_CREATIVE_FIELDS = [
    "actor_id",
    "image_crops",
    "asset_feed_spec",
    "degrees_of_freedom_spec",
    "instagram_user_id",
    "object_story_spec",
    "contextual_multi_ads",
    "thumbnail_url",
    "url_tags",
]


def test_eq_creative_equal_with_live_facebook_nested_keys():
    # The source creative (from Facebook) has extra server-generated keys
    # inside link_data that the desired creative does not have. The meaningful
    # content (image_hash, link, message, call_to_action, page_id, actor_id,
    # url_tags) is identical.
    source_creative = {
        "id": "23846327900110518",
        "name": "vlab-mnm-survey",
        "url_tags": "ref=form.survey.stratumid.abc123",
        "actor_id": "102998371752603",
        "object_story_spec": {
            "page_id": "102998371752603",
            "link_data": {
                "image_hash": "3181666208161582c277488a2c2b5fdb",
                "link": "https://fb.com/messenger_doc/",
                "message": "Take our survey!",
                "call_to_action": {"type": "MESSAGE_PAGE"},
                "branded_content": {"sponsor_id": "123"},
                "image_crops": {"191x100": [[0, 0], [100, 100]]},
            },
        },
    }

    desired_creative = {
        "name": "vlab-mnm-survey",
        "url_tags": "ref=form.survey.stratumid.abc123",
        "actor_id": "102998371752603",
        "object_story_spec": {
            "page_id": "102998371752603",
            "link_data": {
                "image_hash": "3181666208161582c277488a2c2b5fdb",
                "link": "https://fb.com/messenger_doc/",
                "message": "Take our survey!",
                "call_to_action": {"type": "MESSAGE_PAGE"},
            },
        },
    }

    assert _eq(desired_creative, source_creative, _CREATIVE_FIELDS)


def test_ad_dif_no_recreate_when_only_nested_extra_keys_differ():
    adset = {"id": "adset"}

    # Source ad from Facebook — creative has extra server-generated keys in
    # object_story_spec.link_data
    source_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {
                "image_hash": "abc123",
                "link": "https://fb.com/msg/",
                "message": "Take our survey!",
                "call_to_action": {"type": "MESSAGE_PAGE"},
                "branded_content": {"sponsor_id": "999"},
            },
        },
    }

    desired_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {
                "image_hash": "abc123",
                "link": "https://fb.com/msg/",
                "message": "Take our survey!",
                "call_to_action": {"type": "MESSAGE_PAGE"},
            },
        },
    }

    running_ads = [
        _adobject(
            {
                "id": "foo",
                "status": "ACTIVE",
                "name": "hindi",
                "creative": source_creative,
            },
            Ad,
        )
    ]

    instructions = ad_dif(adset, running_ads, [_ad(desired_creative, adset)])

    # Should be a no-op — the creative content is identical, only
    # server-generated extra keys differ.
    assert instructions == []


def test_eq_creative_equal_with_fb_creative_features_spec_defaults():
    # Mirrors the production bug: Facebook returns ~70 creative_features_spec
    # keys (all OPT_OUT) that the desired creative only sets ~13 of.  Before
    # the _subset="a" fix, the key-set mismatch in strict symmetric mode
    # caused every ad to be flagged as "creative mismatch".
    fb_extra_features = {
        "adapt_to_placement": {"enroll_status": "OPT_OUT"},
        "add_text_overlay": {"enroll_status": "OPT_OUT"},
        "ads_with_benefits": {"enroll_status": "OPT_OUT"},
        "audio": {"enroll_status": "OPT_OUT"},
        "auto_promotion_tag": {"enroll_status": "OPT_OUT"},
        "biz_ai": {"enroll_status": "OPT_OUT"},
        "carousel_to_video": {"enroll_status": "OPT_OUT"},
        "catalog_feed_tag": {"enroll_status": "OPT_OUT"},
        "creative_stickers": {"enroll_status": "OPT_OUT"},
        "customize_product_recommendation": {"enroll_status": "OPT_OUT"},
        "description_automation": {"enroll_status": "OPT_OUT"},
        "dha_optimization": {"enroll_status": "OPT_OUT"},
        "dynamic_cta_text": {"enroll_status": "OPT_OUT"},
        "dynamic_partner_content": {"enroll_status": "OPT_OUT"},
        "enable_ncs_testimonials": {"enroll_status": "OPT_OUT"},
        "fb_feed_tag": {"enroll_status": "OPT_OUT"},
        "fb_reels_tag": {"enroll_status": "OPT_OUT"},
        "fb_story_tag": {"enroll_status": "OPT_OUT"},
        "feed_caption_optimization": {"enroll_status": "OPT_OUT"},
        "generate_cta": {"enroll_status": "OPT_OUT"},
        "hide_price": {"enroll_status": "OPT_OUT"},
        "hyperlink_formatting": {"enroll_status": "OPT_OUT"},
        "ig_feed_tag": {"enroll_status": "OPT_OUT"},
        "ig_glados_feed": {"enroll_status": "OPT_OUT"},
        "ig_reels_tag": {"enroll_status": "OPT_OUT"},
        "ig_stream_tag": {"enroll_status": "OPT_OUT"},
        "ig_video_native_subtitle": {"enroll_status": "OPT_OUT"},
        "image_auto_crop": {"enroll_status": "OPT_OUT"},
        "image_background_gen": {"enroll_status": "OPT_OUT"},
        "image_banner": {"enroll_status": "OPT_OUT"},
        "image_end_card": {"enroll_status": "OPT_OUT"},
        "image_enhancement": {"enroll_status": "OPT_OUT"},
        "image_text_translation": {"enroll_status": "OPT_OUT"},
        "image_uncrop": {"enroll_status": "OPT_OUT"},
        "local_store_extension": {"enroll_status": "OPT_OUT"},
        "media_liquidity_animated_image": {"enroll_status": "OPT_OUT"},
        "media_order": {"enroll_status": "OPT_OUT"},
        "media_type_automation": {"enroll_status": "OPT_OUT"},
        "multi_creative_post_carousel": {"enroll_status": "OPT_OUT"},
        "multi_photo_to_video": {"enroll_status": "OPT_OUT"},
        "music_generation": {"enroll_status": "OPT_OUT"},
        "pac_genai_recomposition": {"enroll_status": "OPT_OUT"},
        "product_browsing": {"enroll_status": "OPT_OUT"},
        "product_extensions": {"enroll_status": "OPT_OUT"},
        "product_metadata_automation": {"enroll_status": "OPT_OUT"},
        "product_tags": {"enroll_status": "OPT_OUT"},
        "profile_card": {"enroll_status": "OPT_OUT"},
        "profile_extension": {"enroll_status": "OPT_OUT"},
        "replace_media_text": {"enroll_status": "OPT_OUT"},
        "show_summary": {"enroll_status": "OPT_OUT"},
        "site_extensions": {"enroll_status": "OPT_OUT"},
        "standard_enhancements_catalog": {"enroll_status": "OPT_OUT"},
        "text_extraction_for_headline": {"enroll_status": "OPT_OUT"},
        "text_extraction_for_tap_target": {"enroll_status": "OPT_OUT"},
        "text_formatting_optimization": {"enroll_status": "OPT_OUT"},
        "text_generation": {"enroll_status": "OPT_OUT"},
        "text_overlay_translation": {"enroll_status": "OPT_OUT"},
        "translate_voiceover": {"enroll_status": "OPT_OUT"},
        "video_auto_crop": {"enroll_status": "OPT_OUT"},
        "video_filtering": {"enroll_status": "OPT_OUT"},
        "video_highlight": {"enroll_status": "OPT_OUT"},
        "video_highlights": {"enroll_status": "OPT_OUT"},
        "video_to_image": {"enroll_status": "OPT_OUT"},
        "video_uncrop": {"enroll_status": "OPT_OUT"},
        "video_uncrop_9x16_to_9x18": {"enroll_status": "OPT_OUT"},
        "wa_mm_image_filtering": {"enroll_status": "OPT_OUT"},
        "wa_mm_text_truncation_length": {"enroll_status": "OPT_OUT"},
    }

    desired_features = {
        "advantage_plus_creative": {"enroll_status": "OPT_IN"},
        "cv_transformation": {"enroll_status": "OPT_IN"},
        "enhance_cta": {
            "enroll_status": "OPT_IN",
            "customizations": {"text_extraction": {"enroll_status": "OPT_IN"}},
        },
        "image_animation": {"enroll_status": "OPT_IN"},
        "image_brightness_and_contrast": {"enroll_status": "OPT_IN"},
        "image_templates": {"enroll_status": "OPT_IN"},
        "image_touchups": {"enroll_status": "OPT_IN"},
        "inline_comment": {"enroll_status": "OPT_IN"},
        "pac_recomposition": {"enroll_status": "OPT_OUT"},
        "pac_relaxation": {"enroll_status": "OPT_OUT"},
        "reveal_details_over_time": {"enroll_status": "OPT_IN"},
        "show_destination_blurbs": {"enroll_status": "OPT_IN"},
        "text_optimizations": {
            "enroll_status": "OPT_IN",
            "customizations": {"text_extraction": {"enroll_status": "OPT_IN"}},
        },
        "text_translation": {"enroll_status": "OPT_OUT"},
    }

    # Facebook merges desired + defaults; the values for shared keys match.
    source_features = {**fb_extra_features, **desired_features}

    source_creative = {
        "id": "123",
        "name": "Ad1",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "degrees_of_freedom_spec": {"creative_features_spec": source_features},
    }

    desired_creative = {
        "name": "Ad1",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "degrees_of_freedom_spec": {"creative_features_spec": desired_features},
    }

    assert _eq(desired_creative, source_creative, _CREATIVE_FIELDS)


def test_eq_still_detects_real_creative_difference_in_subset_mode():
    # Even in subset mode, a value difference in a key that exists in both
    # desired and source must be detected.
    source_creative = {
        "name": "Ad1",
        "actor_id": "111",
        "url_tags": "ref=old",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {
                "image_hash": "abc123",
                "branded_content": {"sponsor_id": "999"},
            },
        },
    }

    desired_creative = {
        "name": "Ad1",
        "actor_id": "111",
        "url_tags": "ref=new",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {"image_hash": "abc123"},
        },
    }

    assert not _eq(desired_creative, source_creative, _CREATIVE_FIELDS)


def test_eq_still_detects_undeclared_key_missing_from_source():
    # An undeclared key present in desired but missing from source stays a
    # difference. It has to: a real change (photo_data -> link_data) looks
    # exactly like a field Facebook silently drops, and only a human can say
    # which one it is. See test_ad_dif_updates_when_object_story_spec_format_changes.
    source = {
        "page_id": "111",
        "link_data": {"image_hash": "abc123"},
    }

    desired = {
        "page_id": "111",
        "link_data": {"image_hash": "abc123", "message": "Take our survey!"},
    }

    assert not _eq(desired, source, _subset="a")


def test_eq_warns_about_undeclared_drop(caplog):
    # Never silent: an undeclared drop is what an endless rewrite loop looks
    # like on its first run, so it names itself and the command that fixes it.
    source = {"link_data": {"image_hash": "abc123"}}
    desired = {"link_data": {"image_hash": "abc123", "surprise": "new"}}

    with caplog.at_level(logging.WARNING):
        assert not _eq(desired, source, _subset="a")

    assert "undeclared drop at .link_data.surprise" in caplog.text
    assert "adopt-probe" in caplog.text


def test_update_adset_ignores_server_added_fields_on_the_live_adset():
    # The reason the desired object must be _eq's first argument: Facebook
    # decorates what it returns with fields we never set. Compared the other
    # way round those extras look like differences and every adset is
    # rewritten forever.
    common = {
        "name": "s1",
        "targeting": {"age_min": 36},
        "status": "ACTIVE",
        "daily_budget": 2585,
        "optimization_goal": "CONVERSATIONS",
    }
    live = _adobject(
        {
            **common,
            "daily_budget": "2585",
            "id": "srv-1",
            "created_time": "2026-08-01T00:00:00+0000",
            "targeting": {"age_min": 36, "brand_safety_content_filter_levels": ["X"]},
        },
        AdSet,
    )
    desired = _adobject(common, AdSet)

    assert update_adset(live, desired) == []


def test_update_adset_ignores_empty_values_facebook_elides():
    # add_audience_targeting always sets custom_audiences, to [] when the study
    # has none, and Facebook omits the key entirely rather than echoing [].
    # Asking for nothing and being shown nothing is agreement.
    live = _adobject({"name": "s1", "targeting": {"age_min": 36}}, AdSet)
    desired = _adobject(
        {"name": "s1", "targeting": {"age_min": 36, "custom_audiences": []}}, AdSet
    )

    assert update_adset(live, desired) == []


def test_update_adset_still_applies_a_newly_added_audience():
    # The other side of that rule: asking for something non-empty and not
    # seeing it is a real difference. Adding an audience to an adset that has
    # none must still be applied.
    # update_adset builds its params from every compared field, so the desired
    # adset must carry all of them — create_adset always does.
    base = {
        "name": "s1",
        "status": "ACTIVE",
        "daily_budget": 2585,
        "optimization_goal": "CONVERSATIONS",
        "end_time": datetime(2026, 8, 3, 0, 0),
    }
    live = _adobject({**base, "targeting": {"age_min": 36}}, AdSet)
    desired = _adobject(
        {**base, "targeting": {"age_min": 36, "custom_audiences": [{"id": "aud-1"}]}},
        AdSet,
    )

    instructions = update_adset(live, desired)

    assert len(instructions) == 1
    assert instructions[0].params["targeting"]["custom_audiences"] == [{"id": "aud-1"}]


def test_eq_treats_facebook_string_budget_as_equal_to_our_int():
    # Facebook returns daily_budget as a string, create_adset sets an int.
    # Same number, so the adset must not be rewritten. Without normalising,
    # '2585' != 2585 and EVERY adset is rewritten on EVERY run forever.
    live = _adobject({"name": "s1", "daily_budget": "2585"}, AdSet)
    desired = _adobject({"name": "s1", "daily_budget": 2585}, AdSet)

    assert _eq(live, desired, ["name", "daily_budget"])


def test_eq_still_detects_a_real_budget_change():
    # Normalising must not blind us to the optimizer actually moving money.
    live = _adobject({"name": "s1", "daily_budget": "2585"}, AdSet)
    desired = _adobject({"name": "s1", "daily_budget": 3000}, AdSet)

    assert not _eq(live, desired, ["name", "daily_budget"])


def test_eq_treats_equivalent_end_times_as_equal():
    # Facebook returns an ISO string in the ad account's timezone; create_adset
    # sets a naive UTC datetime. 02:00+0200 is 00:00 UTC — the same instant.
    live = _adobject({"name": "s1", "end_time": "2026-08-03T02:00:00+0200"}, AdSet)
    desired = _adobject({"name": "s1", "end_time": datetime(2026, 8, 3, 0, 0)}, AdSet)

    assert _eq(live, desired, ["name", "end_time"])


def test_eq_still_detects_a_real_end_time_change():
    live = _adobject({"name": "s1", "end_time": "2026-08-03T02:00:00+0200"}, AdSet)
    desired = _adobject({"name": "s1", "end_time": datetime(2026, 8, 5, 0, 0)}, AdSet)

    assert not _eq(live, desired, ["name", "end_time"])


def test_update_adset_no_ops_when_only_representation_differs():
    # End-to-end: the live adset and the desired one mean the same thing and
    # differ only in how Facebook renders them. No instruction may be emitted.
    common = {
        "name": "gender:men,geography:country",
        "targeting": {"age_min": 36, "age_max": 65},
        "status": "ACTIVE",
        "optimization_goal": "CONVERSATIONS",
    }
    live = _adobject(
        {**common, "daily_budget": "2585", "end_time": "2026-08-03T02:00:00+0200"},
        AdSet,
    )
    desired = _adobject(
        {**common, "daily_budget": 2585, "end_time": datetime(2026, 8, 3, 0, 0)},
        AdSet,
    )

    assert update_adset(live, desired) == []


def test_eq_tolerates_a_whole_top_level_field_missing_from_source(caplog):
    # Deliberate asymmetry with the nested rule above, and long-standing
    # behaviour: a top-level field absent from Facebook's response is not
    # something we can act on, so it is skipped rather than rewritten every
    # run. It still warns when undeclared. See _declared_drop.
    source = {"actor_id": "111"}
    desired = {"actor_id": "111", "url_tags": "ref=foo"}

    with caplog.at_level(logging.WARNING):
        assert _eq(desired, source, _CREATIVE_FIELDS)

    assert "undeclared drop at .url_tags" in caplog.text


def test_eq_declared_drop_is_not_a_difference():
    # The production case: we send image_text_translation, Facebook returns
    # ~82 creative_features_spec keys and never that one. Declared, so equal.
    source = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "standard_enhancements": {"enroll_status": "OPT_OUT"},
            }
        }
    }
    desired = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "image_text_translation": {"enroll_status": "OPT_IN"},
            }
        }
    }

    assert _eq(desired, source, _CREATIVE_FIELDS)


def test_eq_declared_drop_does_not_warn(caplog):
    # The real production case: image_text_translation is declared in
    # field_contract.DROPPED, so it is expected and stays quiet.
    path = "degrees_of_freedom_spec.creative_features_spec.image_text_translation"
    assert path in field_contract.DROPPED, "fixture depends on this declaration"

    source = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "standard_enhancements": {"enroll_status": "OPT_OUT"},
            }
        }
    }
    desired = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "image_text_translation": {"enroll_status": "OPT_IN"},
            }
        }
    }

    with caplog.at_level(logging.WARNING):
        assert _eq(desired, source, _CREATIVE_FIELDS)

    assert "undeclared drop" not in caplog.text


def test_ad_dif_converges_when_facebook_drops_a_declared_field():
    # End-to-end version of the production bug: the ONLY difference between
    # desired and live is a field Facebook never echoes back. This must
    # produce no instruction at all, otherwise the ad is rewritten every run.
    creative = {
        "name": "Ad1",
        "actor_id": "111",
        "url_tags": "ref=creative.Ad1.form.hpvintrotriple",
        "object_story_spec": {"page_id": "111"},
    }

    live_creative = {
        **creative,
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                # Facebook's own defaults, minus the key we sent.
                "standard_enhancements": {"enroll_status": "OPT_OUT"},
                "text_generation": {"enroll_status": "OPT_OUT"},
            }
        },
    }

    desired_creative = {
        **creative,
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "image_text_translation": {"enroll_status": "OPT_IN"},
            }
        },
    }

    source = _adobject(
        {"id": "1", "name": "Ad1", "status": "ACTIVE", "creative": live_creative}, Ad
    )
    desired = _adobject(
        {"name": "Ad1", "status": "ACTIVE", "creative": desired_creative}, Ad
    )

    assert ad_dif("adset-1", [source], [desired]) == []


def test_contract_field_names_match_the_facebook_sdk():
    # The contract keys are plain strings; make sure they are the real field
    # names the SDK uses, so a typo cannot silently drop a field from
    # comparison altogether.
    for f in field_contract.COMPARED_AD:
        assert hasattr(AdCreative.Field, f), f
    for f in field_contract.COMPARED_ADSET:
        assert hasattr(AdSet.Field, f), f


# ---------------------------------------------------------------------------
# Tests for list sorting and intersection mode (_subset="both").
#
# Production logs (v0.1.73) showed two remaining false-positive sources:
#   1. thumbnail_url: Facebook regenerates CDN URLs on every read (160 ad
#      updates per run). Fixed by removing thumbnail_url from update_ad's
#      field list.
#   2. targeting.excluded_custom_audiences: Facebook returns audience refs
#      in a different order and may strip the `name` field from some entries.
#      Fixed by sorting lists in _eq and using _subset="both" (intersection
#      mode) for list elements so only keys both sides have are compared.
# ---------------------------------------------------------------------------


def test_eq_list_comparison_is_order_independent():
    a = [{"id": "123", "name": "foo"}, {"id": "456", "name": "bar"}]
    b = [{"id": "456", "name": "bar"}, {"id": "123", "name": "foo"}]
    assert _eq(a, b, _subset="a")


def test_eq_list_comparison_ignores_missing_metadata_in_elements():
    # Facebook may strip `name` from some audience entries. With
    # _subset="both" (intersection mode), only keys both sides have are
    # compared — the `id` is what matters for targeting.
    a = [{"id": "123", "name": "foo"}, {"id": "456", "name": "bar"}]
    b = [{"id": "456", "name": "bar"}, {"id": "123"}]
    assert _eq(a, b, _subset="a")


def test_eq_list_comparison_detects_different_ids():
    a = [{"id": "123"}, {"id": "456"}]
    b = [{"id": "123"}, {"id": "789"}]
    assert not _eq(a, b, _subset="a")


def test_eq_list_comparison_detects_length_mismatch():
    a = [{"id": "123"}, {"id": "456"}]
    b = [{"id": "123"}]
    assert not _eq(a, b, _subset="a")


def test_eq_list_comparison_via_field_list_handles_audience_order():
    # Mirrors the production bug: update_adset compares targeting which
    # contains excluded_custom_audiences as a list of {id, name} dicts.
    # Facebook returns them in a different order and may strip `name`.
    source_adset = {
        "id": "foo",
        "name": "test",
        "end_time": "2026-07-17",
        "status": "ACTIVE",
        "daily_budget": 100,
        "optimization_goal": "CONVERSATIONS",
        "targeting": {
            "age_max": 65,
            "age_min": 30,
            "genders": [2],
            "geo_locations": {"countries": ["NG"]},
            "excluded_custom_audiences": [
                {"id": "B", "name": "audience_b"},
                {"id": "A"},  # Facebook stripped name
            ],
        },
    }

    desired_adset = {
        "name": "test",
        "end_time": "2026-07-17",
        "status": "ACTIVE",
        "daily_budget": 100,
        "optimization_goal": "CONVERSATIONS",
        "targeting": {
            "age_max": 65,
            "age_min": 30,
            "genders": [2],
            "geo_locations": {"countries": ["NG"]},
            "excluded_custom_audiences": [
                {"id": "A", "name": "audience_a"},
                {"id": "B", "name": "audience_b"},
            ],
        },
    }

    fields = [
        "end_time", "targeting", "status",
        "daily_budget", "optimization_goal", "name",
    ]

    assert _eq(desired_adset, source_adset, fields)


def test_ad_dif_ignores_thumbnail_url_difference():
    # thumbnail_url is a Facebook-generated CDN URL that changes on every
    # read. It should not trigger an ad update.
    adset = {"id": "ad"}

    source_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "thumbnail_url": "https://cdn-old.fbcdn.net/image/123",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {"image_hash": "abc123"},
        },
    }

    desired_creative = {
        "name": "hindi",
        "actor_id": "111",
        "url_tags": "ref=foo",
        "thumbnail_url": "https://cdn-new.fbcdn.net/image/456",
        "object_story_spec": {
            "page_id": "111",
            "link_data": {"image_hash": "abc123"},
        },
    }

    running_ads = [
        _adobject(
            {
                "id": "foo",
                "status": "ACTIVE",
                "name": "hindi",
                "creative": source_creative,
            },
            Ad,
        )
    ]

    instructions = ad_dif(adset, running_ads, [_ad(desired_creative, adset)])
    assert instructions == []


# ---------------------------------------------------------------------------
# Tests for ad-ID attribution provenance plumbing (A1).
#
# `Instruction` gained a 5th, optional, defaulted `provenance` field, and
# `ad_dif`/`adset_dif` gained a trailing optional `provenance` param -- a
# `ProvenanceLookup` dict keyed by (adset name, ad name), i.e.
# (stratum id, creative name). `ad_dif`'s creator stamps that provenance onto
# every "ad"/"create" instruction it emits, so that once Facebook returns the
# new ad's id, the imperative shell can write the ad -> stratum mapping row.
# Only creates carry it: updates and deletes act on ads that already have a
# mapping row, so there is nothing new to attribute.
# ---------------------------------------------------------------------------


def test_ad_dif_stamps_provenance_onto_create():
    adset = {"id": "adset-id", "name": "stratum-1"}
    creatives = [{"name": "Smiling", "actor_id": "111", "url_tags": "123"}]
    provenance = {
        ("stratum-1", "Smiling"): {"stratum_id": "stratum-1", "creative_name": "Smiling"}
    }

    instructions = ad_dif(adset, [], [_ad(c, adset) for c in creatives], provenance)

    assert len(instructions) == 1
    assert instructions[0].node == "ad"
    assert instructions[0].action == "create"
    assert instructions[0].provenance == {
        "stratum_id": "stratum-1",
        "creative_name": "Smiling",
    }


def test_ad_dif_without_provenance_arg_defaults_to_none():
    # Backwards compatibility: every pre-existing call site -- this one
    # included -- omits provenance entirely, and the resulting Instruction
    # must equal a plain 4-argument Instruction() by NamedTuple equality
    # precisely because the new field defaults to None.
    adset = {"id": "ad"}
    creatives = [{"name": "newhindi", "actor_id": "111", "url_tags": "123"}]

    instructions = ad_dif(adset, [], [_ad(c, adset) for c in creatives])

    assert instructions == [
        Instruction(
            "ad",
            "create",
            {
                "adset_id": "ad",
                "name": "newhindi",
                "creative": creatives[0],
                "status": "ACTIVE",
            },
            None,
        ),
    ]


def test_ad_dif_matches_provenance_per_ad_not_blanket():
    adset = {"id": "adset-id", "name": "stratum-1"}
    creatives = [
        {"name": "Smiling", "actor_id": "111", "url_tags": "123"},
        {"name": "Serious", "actor_id": "111", "url_tags": "124"},
    ]
    provenance = {
        ("stratum-1", "Smiling"): {"stratum_id": "stratum-1", "creative_name": "Smiling"}
    }

    instructions = ad_dif(adset, [], [_ad(c, adset) for c in creatives], provenance)

    by_name = {i.params["name"]: i for i in instructions}
    assert by_name["Smiling"].provenance == {
        "stratum_id": "stratum-1",
        "creative_name": "Smiling",
    }
    assert by_name["Serious"].provenance is None


def test_ad_dif_provenance_keyed_on_adset_avoids_cross_stratum_collision():
    # The important case: identical creative names in different strata must
    # not collide. A bug here silently attributes respondents to the wrong
    # stratum.
    adset = {"id": "adset-id", "name": "stratum-2"}
    creatives = [{"name": "Smiling", "actor_id": "111", "url_tags": "123"}]
    provenance = {
        ("stratum-1", "Smiling"): {"stratum_id": "stratum-1", "creative_name": "Smiling"},
        ("stratum-2", "Smiling"): {"stratum_id": "stratum-2", "creative_name": "Smiling"},
    }

    instructions = ad_dif(adset, [], [_ad(c, adset) for c in creatives], provenance)

    assert len(instructions) == 1
    assert instructions[0].provenance == {
        "stratum_id": "stratum-2",
        "creative_name": "Smiling",
    }


def test_ad_dif_update_and_delete_carry_no_provenance():
    # Only creates learn a new id, so only creates need provenance.
    adset = {"id": "adset-id", "name": "stratum-1"}
    running_ads = [
        _adobject(
            {
                "id": "foo",
                "status": "ACTIVE",
                "name": "hindi",
                "creative": {
                    "name": "hindi",
                    "id": "bar",
                    "actor_id": "111",
                    "url_tags": "111",
                },
            },
            Ad,
        ),
        _adobject(
            {
                "id": "baz",
                "status": "ACTIVE",
                "name": "oldad",
                "creative": {
                    "name": "oldad",
                    "id": "qux",
                    "actor_id": "111",
                    "url_tags": "123",
                },
            },
            Ad,
        ),
    ]

    # "hindi" matches by name but has a different creative -> update.
    # "oldad" is no longer desired -> delete.
    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "222"}]
    provenance = {
        ("stratum-1", "hindi"): {"stratum_id": "stratum-1", "creative_name": "hindi"},
        ("stratum-1", "oldad"): {"stratum_id": "stratum-1", "creative_name": "oldad"},
    }

    instructions = ad_dif(
        adset, running_ads, [_ad(c, adset) for c in creatives], provenance
    )

    assert len(instructions) == 2
    assert {(i.node, i.action) for i in instructions} == {
        ("ad", "update"),
        ("ad", "delete"),
    }
    for i in instructions:
        assert i.provenance is None


def test_ad_dif_delete_still_emitted_with_id_when_provenance_present():
    # The reconciliation half of the append-only invariant: the mapping row
    # must outlive the ad, so deletes must keep working normally and must not
    # be suppressed by the provenance change.
    adset = {"id": "adset-id", "name": "stratum-1"}
    running_ads = [
        _adobject(
            {
                "id": "gone-id",
                "status": "ACTIVE",
                "name": "retired",
                "creative": {
                    "name": "retired",
                    "id": "c1",
                    "actor_id": "111",
                    "url_tags": "111",
                },
            },
            Ad,
        )
    ]
    provenance = {
        ("stratum-1", "retired"): {"stratum_id": "stratum-1", "creative_name": "retired"}
    }

    instructions = ad_dif(adset, running_ads, [], provenance)

    assert instructions == [Instruction("ad", "delete", {}, "gone-id")]


def test_adset_dif_threads_provenance_down_to_ad_creates():
    old_adsets = [
        (
            _adset({"id": "foo", "name": "foo", "status": "PAUSED"}),
            [
                _adobject(
                    {
                        "id": "fooad",
                        "adset_id": "foo",
                        "status": "PAUSED",
                        "name": "bar",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                )
            ],
        )
    ]

    new_adsets = [
        (
            _adset({"name": "foo", "status": "ACTIVE"}),
            [
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "bar",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                ),
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "qux",
                        "creative": {"foo": "qux"},
                    },
                    Ad,
                ),
            ],
        ),
        (
            # A brand-new adset -- its "adset"/"create" instruction is not an
            # ad and must get no mapping-row provenance.
            _adset({"name": "newadset", "status": "ACTIVE"}),
            [
                _adobject(
                    {
                        "adset_id": None,
                        "status": "ACTIVE",
                        "name": "baz",
                        "creative": {"foo": "bar"},
                    },
                    Ad,
                )
            ],
        ),
    ]

    provenance = {("foo", "qux"): {"stratum_id": "foo", "creative_name": "qux"}}

    instructions = adset_dif(old_adsets, new_adsets, provenance)

    creates = [i for i in instructions if i.action == "create"]
    ad_create = next(i for i in creates if i.node == "ad")
    adset_create = next(i for i in creates if i.node == "adset")

    assert ad_create.provenance == {"stratum_id": "foo", "creative_name": "qux"}
    assert adset_create.provenance is None


def test_ad_dif_missing_provenance_warns_but_still_creates(caplog):
    # An unmapped ad is a real defect (its respondents can never be
    # attributed and there is no backfill path), so it must be visible -- but
    # refusing to create the ad would be worse.
    adset = {"id": "adset-id", "name": "stratum-1"}
    creatives = [{"name": "Smiling", "actor_id": "111", "url_tags": "123"}]
    provenance = {
        ("stratum-1", "SomeOtherAd"): {
            "stratum_id": "stratum-1",
            "creative_name": "SomeOtherAd",
        }
    }

    with caplog.at_level(logging.WARNING):
        instructions = ad_dif(
            adset, [], [_ad(c, adset) for c in creatives], provenance
        )

    assert len(instructions) == 1
    assert instructions[0].action == "create"
    assert instructions[0].provenance is None
    assert "no provenance" in caplog.text


# ---------------------------------------------------------------------------
# promoted_object and adset reconciliation (A9).
#
# A9 makes promoted_object non-None for a whole destination type. The danger is
# not the new functionality, it is that a newly-populated field could make
# update_adset see every existing adset as drifted and rewrite live adsets
# across every running study. These tests pin that it cannot.
# ---------------------------------------------------------------------------


def test_promoted_object_is_not_part_of_the_adset_comparison():
    """The structural reason A9 is safe.

    update_adset compares only field_contract.COMPARED_ADSET, and builds its
    update params from the same list. So promoted_object is neither compared
    nor sent on an update -- it rides only on adset *creates*, which is exactly
    where Meta needs it.

    If someone adds it to COMPARED_ADSET later, this test fails and should be
    read as a warning: Facebook normalises promoted_object on read, so
    comparing it is a strong candidate for the endless-rewrite loop described
    in field_contract's own docstring.
    """
    assert "promoted_object" not in field_contract.COMPARED_ADSET


def test_a_live_adset_without_promoted_object_is_not_rewritten_when_we_start_sending_one():
    """The property that protects every running study.

    Before A9 a WhatsApp/app adset was created without promoted_object, or the
    study did not exist. Either way Facebook's copy has no promoted_object and
    ours now does. That must not read as drift.
    """
    now = datetime.utcnow()
    common = {
        "status": "ACTIVE",
        "daily_budget": 100,
        "end_time": now,
        "targeting": {},
        "optimization_goal": "REPLIES",
        "name": "stratum-1",
    }

    live = _adobject(dict(common), AdSet)
    desired = _adobject(
        {
            **common,
            "promoted_object": {
                "page_id": "page-123",
                "whatsapp_phone_number": "15419202635",
            },
        },
        AdSet,
    )

    assert update_adset(live, desired) == []


def test_an_unchanged_study_still_produces_no_instructions():
    """Reconciliation over a study nothing changed in must stay a no-op.

    The whole-run version of the test above: same adset, same ads, both sides.
    """
    adset = _adset({"id": "foo", "name": "stratum-1", "status": "ACTIVE"})
    creative = {"name": "Smiling", "actor_id": "111", "url_tags": "ref=x"}
    ads = [_ad(creative, adset)]

    desired_adset = _adset({"name": "stratum-1", "status": "ACTIVE"})
    desired_adset["promoted_object"] = {
        "page_id": "page-123",
        "whatsapp_phone_number": "15419202635",
    }

    instructions = adset_dif([(adset, ads)], [(desired_adset, ads)])

    assert instructions == []


def test_promoted_object_is_absent_from_a_generated_adset_update():
    """An update carries only COMPARED_ADSET fields, so it cannot clear or
    change a live adset's promoted_object as a side effect of a budget bump."""
    now = datetime.utcnow()
    live = _adobject(
        {
            "id": "adset-1",
            "status": "ACTIVE",
            "daily_budget": 100,
            "end_time": now,
            "targeting": {},
            "optimization_goal": "REPLIES",
            "name": "stratum-1",
        },
        AdSet,
    )
    desired = _adobject(
        {
            "status": "ACTIVE",
            "daily_budget": 999,  # the only real change
            "end_time": now,
            "targeting": {},
            "optimization_goal": "REPLIES",
            "name": "stratum-1",
            "promoted_object": {"page_id": "page-123"},
        },
        AdSet,
    )

    instructions = update_adset(live, desired)

    assert len(instructions) == 1
    assert instructions[0].action == "update"
    assert "promoted_object" not in instructions[0].params
    assert instructions[0].params["daily_budget"] == 999


def test_a_live_adset_with_a_different_destination_type_is_not_rewritten():
    """The guard on moving destination_type from the conf to a derivation.

    `destination_type` is absent from COMPARED_ADSET, so it rides only on ad-set
    creates. That is what makes the derivation safe to land: a live study whose
    stored recruitment destination_type disagrees with what its destinations now
    imply -- two production studies were configured exactly that way -- keeps
    its existing ad sets untouched rather than having every one of them
    rewritten on the next reconciliation run.

    It is also why a running study can never change channel. Ad sets are matched
    by name and the name is the stratum id, so they persist for the study's
    lifetime. If anyone ever adds destination_type to COMPARED_ADSET, this test
    fails and that trade-off gets made deliberately.
    """
    now = datetime.utcnow()
    common = {
        "status": "ACTIVE",
        "daily_budget": 100,
        "end_time": now,
        "targeting": {},
        "optimization_goal": "REPLIES",
        "name": "stratum-1",
    }
    live = _adobject({"id": "adset-1", **common, "destination_type": "WEB"}, AdSet)
    desired = _adobject({**common, "destination_type": "MESSENGER"}, AdSet)

    assert update_adset(live, desired) == []


def test_a_destination_type_change_cannot_ride_along_on_a_budget_update():
    """Even when something else legitimately changed, the update is built from
    COMPARED_ADSET alone, so destination_type is never in the params."""
    now = datetime.utcnow()
    common = {
        "status": "ACTIVE",
        "end_time": now,
        "targeting": {},
        "optimization_goal": "REPLIES",
        "name": "stratum-1",
    }
    live = _adobject(
        {"id": "adset-1", **common, "daily_budget": 100, "destination_type": "WEB"},
        AdSet,
    )
    desired = _adobject(
        {**common, "daily_budget": 999, "destination_type": "MESSENGER"}, AdSet
    )

    instructions = update_adset(live, desired)

    assert len(instructions) == 1
    assert "destination_type" not in instructions[0].params
    assert instructions[0].params["daily_budget"] == 999
