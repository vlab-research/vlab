import random
from datetime import datetime
from typing import TypeVar

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.customaudience import CustomAudience

from .marketing import (Audience, CreativeConf, Instruction, Lookalike,
                        LookalikeSpec, StratumConf, _eq, ad_dif, adset_dif,
                        make_ref, manage_aud, update_adset)


def test_eq_with_all_same():
    a, b = _adobject({"id": "foo", "name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"id": "foo", "name": "bar", "foo": "baz"}, AdSet
    )
    assert _eq(a, b)


def test_eq_with_subset_a():
    a, b = _adobject({"name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"id": "foo", "name": "bar", "foo": "baz"}, AdSet
    )
    assert _eq(a, b)


def test_eq_with_subset_b():
    a, b = _adobject({"id": "bar", "name": "bar", "foo": "baz"}, AdSet), _adobject(
        {"name": "bar", "foo": "baz"}, AdSet
    )
    assert _eq(a, b)


def test_eq_with_subset_a_not_true():
    a, b = _adobject({"id": "bar", "name": "foo", "foo": "baz"}, AdSet), _adobject(
        {"name": "bar", "foo": "baz"}, AdSet
    )
    assert not _eq(a, b)


def test_nested_without_name():
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

    assert _eq(a, b)


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


T = TypeVar("T")


def _adobject(d, T) -> T:
    t = T()
    for k, v in d.items():
        t[k] = v
    return t


def _ad(c, adset):
    a = Ad()
    a[Ad.Field.adset_id] = adset["id"]
    a["name"] = c["name"]
    a["creative"] = c
    a["status"] = "ACTIVE"
    return a


def _adset(d):
    d = {
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
    exp = {k: v for k, v in exp.items() if k not in ["name"]}
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

    running_ads = [_adobject(d, Ad) for d in running_ads]
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
        Instruction("ad", "update", {"status": "PAUSED"}, "foo"),
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
            "status": "PAUSED",
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

    creatives = [{"name": "hindi", "actor_id": "111", "url_tags": "111"}]

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


def _aud_params(name, subtype, description):
    return {
        "name": name,
        "subtype": subtype,
        "description": description,
        "customer_file_source": "USER_PROVIDED_ONLY",
    }


def test_manage_aud_creates_if_doesnt_exist():
    old = []
    aud = Audience(name="foo", subtype="CUSTOM", pageid="page", users=[])

    instructions = manage_aud(old, aud)

    assert instructions == [
        Instruction(
            "custom_audience",
            "create",
            _aud_params("foo", "CUSTOM", "virtual lab auto-generated audience"),
            None,
        )
    ]

    aud = Audience(name="foo", subtype="LOOKALIKE", pageid="page", users=[])
    instructions = manage_aud(old, aud)
    assert instructions == [
        Instruction(
            "custom_audience",
            "create",
            _aud_params("foo", "CUSTOM", "virtual lab auto-generated audience"),
            None,
        )
    ]


def _update_instruction(id_=140892):
    return Instruction(
        "custom_audience",
        "add_users",
        {
            "payload": {
                "schema": ["PAGEUID"],
                "is_raw": True,
                "page_ids": ["page"],
                "data": [["bar"]],
            },
            "session": {
                "session_id": id_,
                "batch_seq": 1,
                "last_batch_flag": True,
                "estimated_num_total": 1,
            },
        },
        "foo",
    )


def test_manage_aud_updates_if_exists():
    random.seed(1)
    old = [
        _adobject({"id": "foo", "name": "foo", "description": "bar"}, CustomAudience)
    ]
    aud = Audience(name="foo", subtype="CUSTOM", pageid="page", users=["bar"])
    instructions = manage_aud(old, aud)

    assert instructions == [_update_instruction()]


def test_manage_aud_only_updates_if_no_lookalike_target_reached():
    random.seed(1)
    old = [
        _adobject(
            {"id": "foo", "name": "foo", "description": "bar", "approximate_count": 10},
            CustomAudience,
        )
    ]

    lookalike = Lookalike("foo-lookalike", 100, LookalikeSpec("IN", 0.1, 0.0))
    aud = Audience(
        name="foo",
        subtype="LOOKALIKE",
        pageid="page",
        users=["bar"],
        lookalike=lookalike,
    )
    instructions = manage_aud(old, aud)

    assert instructions == [_update_instruction()]


def test_manage_aud_only_updates_if_lookalike_and_lookalike_exists():
    random.seed(1)
    old = [
        _adobject(
            {
                "id": "foo",
                "name": "foo",
                "description": "bar",
                "approximate_count": 200,
            },
            CustomAudience,
        ),
        _adobject(
            {
                "id": "foo-lookalike",
                "name": "foo-lookalike",
                "description": "bar",
                "approximate_count": 200,
            },
            CustomAudience,
        ),
    ]

    lookalike = Lookalike("foo-lookalike", 100, LookalikeSpec("IN", 0.1, 0.0))
    aud = Audience(
        name="foo",
        subtype="LOOKALIKE",
        pageid="page",
        users=["bar"],
        lookalike=lookalike,
    )
    instructions = manage_aud(old, aud)
    assert instructions == [_update_instruction()]


def test_manage_aud_creates_lookalike_if_target_passed():
    random.seed(1)
    old = [
        _adobject(
            {
                "id": "foo",
                "name": "foo",
                "description": "bar",
                "approximate_count": 200,
            },
            CustomAudience,
        )
    ]

    lookalike = Lookalike("foo-lookalike", 100, LookalikeSpec("IN", 0.1, 0.0))
    aud = Audience(
        name="foo",
        subtype="LOOKALIKE",
        pageid="page",
        users=["bar"],
        lookalike=lookalike,
    )

    instructions = manage_aud(old, aud)

    spec = '{"country": "IN", "ratio": 0.1, "starting_ratio": 0.0}'
    assert instructions == [
        _update_instruction(),
        Instruction(
            "custom_audience",
            "create",
            {
                "name": "foo-lookalike",
                "subtype": "LOOKALIKE",
                "origin_audience_id": "foo",
                "lookalike_spec": spec,
            },
            None,
        ),
    ]


def _creative_conf(name, form):
    return CreativeConf(
        name, "foo", "foo.jpg", "body", "welcome", "link_text", "button", form
    )


def test_make_ref():
    stratum = StratumConf("foo", 10, "foo", [], [], [], [], {}, metadata={"bar": "baz"})
    creative = _creative_conf("foo", "form1")
    ref = make_ref(creative, stratum)
    assert ref == "form.form1.creative.foo.bar.baz"

    stratum = StratumConf("foo", 10, "foo", [], [], [], [], {}, metadata={})
    ref = make_ref(creative, stratum)
    assert ref == "form.form1.creative.foo"


def test_make_url_escapes():
    stratum = StratumConf(
        "foo", 10, "foo", [], [], [], [], {}, metadata={"bar": "baz foo!"}
    )
    creative = _creative_conf("foo", "form1")
    ref = make_ref(creative, stratum)
    assert ref == "form.form1.creative.foo.bar.baz%20foo%21"


# test
# create new campaign if none (or no??)
#
