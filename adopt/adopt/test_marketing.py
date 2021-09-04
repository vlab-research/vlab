import random
from typing import TypeVar

from facebook_business.adobjects.customaudience import CustomAudience

from .marketing import (Audience, CreativeConf, Instruction, Lookalike,
                        LookalikeSpec, StratumConf, make_ref, manage_aud)

T = TypeVar("T")


def _adobject(d, T) -> T:
    t = T()
    for k, v in d.items():
        t[k] = v
    return t


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
