from datetime import datetime
from typing import TypeVar

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

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


def test_eq_still_detects_missing_key_in_source_in_subset_mode():
    # In subset mode (nested recursion), a key present in desired but missing
    # from source is a real difference.
    source = {
        "page_id": "111",
        "link_data": {"image_hash": "abc123"},
    }

    desired = {
        "page_id": "111",
        "link_data": {"image_hash": "abc123", "message": "Take our survey!"},
    }

    assert not _eq(desired, source, _subset="a")
