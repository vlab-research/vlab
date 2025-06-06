import json
import random
from typing import TypeVar

import pytest
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience

from .facebook.update import Instruction
from .marketing import (
    _create_creative,
    adset_instructions,
    make_ref,
    manage_aud,
    messenger_call_to_action,
    web_call_to_action,
)
from .study_conf import (
    Audience,
    AudienceConf,
    CreativeConf,
    FlyMessengerDestination,
    InvalidConfigError,
    Lookalike,
    LookalikeAudience,
    LookalikeSpec,
    Partitioning,
)

T = TypeVar("T")


def _adobject(d, T) -> T:
    t = T()
    for k, v in d.items():
        t[k] = v
    return t


def _aud_params(name, subtype, description, origin_audience_id=None):
    return {
        "name": name,
        "subtype": subtype,
        "description": description,
        "customer_file_source": "USER_PROVIDED_ONLY",
    }


def _lookalike_aud_params(name, origin_audience_id, spec):
    return {
        "name": name,
        "subtype": "LOOKALIKE",
        "origin_audience_id": origin_audience_id,
        "lookalike_spec": spec,
    }


def test_manage_aud_creates_basic_aud_if_doesnt_exist():
    old = []
    aud = Audience(name="foo", page_ids=["page"], users=[])

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


def test_manage_aud_updates_basic_aud_if_exists():
    random.seed(1)
    old = [
        _adobject({"id": "foo", "name": "foo", "description": "bar"}, CustomAudience)
    ]

    aud = Audience(name="foo", page_ids=["page"], users=["bar"])

    instructions = manage_aud(old, aud)
    assert instructions == [_update_instruction()]


def test_manage_aud_creates_lookalike_with_lookalike_and_lookalike_does_not_exist_and_origin():
    random.seed(1)

    old = [
        _adobject(
            {"id": "foo-origin-id", "name": "foo-origin", "description": "bar"},
            CustomAudience,
        )
    ]

    origin = Audience(name="foo-origin", page_ids=["page"], users=["bar"])

    aud = LookalikeAudience(
        name="foo-lookalike",
        spec=LookalikeSpec(country="IN", ratio=0.1, starting_ratio=0.0),
        origin_audience=origin,
    )

    instructions = manage_aud(old, aud)
    assert instructions == [
        Instruction(
            "custom_audience",
            "create",
            _lookalike_aud_params(
                "foo-lookalike",
                "foo-origin-id",
                '{"country": "IN", "ratio": 0.1, "starting_ratio": 0.0}',
            ),
            None,
        )
    ]


def test_manage_aud_does_nothing_with_lookalike_when_origin_does_not_exist():
    random.seed(1)
    old = []

    origin = Audience(name="foo-origin", page_ids=["page"], users=["bar"])

    aud = LookalikeAudience(
        name="foo-lookalike",
        spec=LookalikeSpec(country="IN", ratio=0.1, starting_ratio=0.0),
        origin_audience=origin,
    )

    instructions = manage_aud(old, aud)
    assert instructions == []


def test_manage_aud_does_nothing_with_lookalike_and_lookalike_exists():
    random.seed(1)
    old = [
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

    origin = Audience(name="foo-origin", page_ids=["page"], users=["bar"])

    aud = LookalikeAudience(
        name="foo-lookalike",
        spec=LookalikeSpec(country="IN", ratio=0.1, starting_ratio=0.0),
        origin_audience=origin,
    )

    instructions = manage_aud(old, aud)
    assert instructions == []


# class FlyMessengerDestination(NamedTuple):
#     form: str  # fly only
#     welcome_message: str  # messenger only
#     button_text: str  # messenger only


# class AppDestination(NamedTuple):
#     app_id: str  # app only
#     app_install_link: str  # app only
#     deeplink_template: str


# DestinationConf = Union[FlyMessengerDestination, AppDestination]


# class CreativeConf(NamedTuple):
#     name: str
#     image_hash: str
#     image: str
#     body: str
#     link_text: str
#     destination_conf: DestinationConf


def _creative_conf(name, form):
    return CreativeConf(
        name=name,
        image_hash="foo",
        image="foo.jpg",
        body="body",
        link_text="link_text",
        destination_conf=FlyMessengerDestination(
            form=form, welcome_message="welcome", button_text="button"
        ),
    )


def test_make_ref():
    metadata = {"bar": "baz"}
    ref = make_ref("foo", metadata)
    assert ref == "creative.foo.bar.baz"

    metadata = {}
    ref = make_ref("foo", metadata)
    assert ref == "creative.foo"


def test_make_url_escapes():
    metadata = {"bar": "baz foo!"}
    ref = make_ref("foo", metadata)
    assert ref == "creative.foo.bar.baz%20foo%21"


def test_partitioning_valid_scenarios():
    Partitioning(min_users=100)
    Partitioning(min_users=100, min_days=2)
    Partitioning(min_users=10, max_users=100, max_days=2)

    with pytest.raises(InvalidConfigError):
        Partitioning(min_users=100, max_days=100)
        Partitioning(min_users=100, min_days=100, max_days=100)


def test_load_partitioning_works_with_errors():
    raw = {"min_users": 100}
    pt = Partitioning(**raw)
    assert pt == Partitioning(min_users=100)

    assert pt.scenario == {"min_users"}

    raw = {"min_users": 100, "max_days": 100}
    with pytest.raises(InvalidConfigError):
        Partitioning(**raw)


def _ac(name, subtype, **kwargs):
    return AudienceConf(name=name, subtype=subtype, **kwargs)


def test_AudienceConf_validates_config_based_on_subtype():
    _ac("foo", "CUSTOM")

    # partitioned
    _ac("foo", "PARTITIONED", partitioning=Partitioning(min_users=100))

    with pytest.raises(InvalidConfigError):
        _ac("foo", "PARTITIONED")

    with pytest.raises(InvalidConfigError):
        _ac("foo", "PARTITIONED", partitioning={"foo": "bar"})

    # lookalike
    _ac(
        "foo",
        "LOOKALIKE",
        lookalike=Lookalike(
            target=100, spec=LookalikeSpec(country="IN", ratio=0.2, starting_ratio=0.1)
        ),
    )

    with pytest.raises(InvalidConfigError):
        _ac("foo", "LOOKALIKE")

    with pytest.raises(InvalidConfigError):
        _ac("foo", "LOOKALIKE", lookalike={"foo": "bar"})


# TODO: test adset instructions, it's a mess, bound with so much.
#       maybe try adding to test_studies?
def test_adset_instructions_creates_paused_if_zero_budget():
    ...


def test_adset_instructions_creates_active_if_non_zero_budget():
    ...


# TODO: test the destination creation stuff to make sure
#       that your creatives/adsets all look dandy with different
#       destination types (app/web/messenger)


# TODO: create new campaign if none (or no??)
#

# This doesn't change - i just need to dynamically
# create the audiences
#
# 1. audiences + responses
# create audiences from responses
# sync with Facebook audiences
#
# for each Remarketing campaign.
# get partitioned audience.
# get all associeted audiences.
# For each audience, build campaign
# based on end_date.


def _load_template(filename):
    with open(f"test/ads/{filename}") as f:
        s = f.read()
        dat = json.loads(s)

    template = AdCreative()
    template.set_data(dat)
    return template


def test_create_creative_from_template_image():
    template = _load_template("image_ad_messenger.json")

    conf = CreativeConf(destination="messenger", name="foo", template=template)
    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["actor_id"] == template["actor_id"]

    assert (
        creative["object_story_spec"]["link_data"]["page_welcome_message"]
        == welcome_message
    )


def test_create_creative_from_template_without_description():
    template = _load_template("ad_no_description.json")

    conf = CreativeConf(destination="messenger", name="foo", template=template)
    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    assert (
        creative["object_story_spec"]["link_data"]["page_welcome_message"]
        == welcome_message
    )


def test_create_creative_from_template_video_messenger():
    template = _load_template("video_ad_messenger.json")

    conf = CreativeConf(destination="messenger", name="foo", template=template)
    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    assert (
        creative["asset_feed_spec"]["additional_data"]["page_welcome_message"]
        == welcome_message
    )


def test_create_creative_from_template_video_with_oss_for_message_cta():
    template = _load_template("video_ad_oss.json")

    conf = CreativeConf(destination="web", name="foo", template=template)

    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    assert (
        creative["object_story_spec"]["video_data"]["page_welcome_message"]
        == welcome_message
    )


def test_create_creative_from_template_video_with_oss_can_change_link_type():
    template = _load_template("video_ad_oss.json")

    conf = CreativeConf(destination="web", name="foo", template=template)

    link = "foo.com/?bar=baz"
    cta = web_call_to_action(link)
    creative = _create_creative(conf, cta, link=link)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    assert "page_welcome_message" not in creative["object_story_spec"]["video_data"]

    assert (
        creative["object_story_spec"]["video_data"]["call_to_action"]["value"]["link"]
        == link
    )


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


def test_create_creative_from_template_video_web():
    template = _load_template("video_ad_website.json")

    conf = CreativeConf(destination="web", name="foo", template=template)

    link = "foo.com/?bar=baz"
    cta = web_call_to_action(link)
    creative = _create_creative(conf, cta, link=link)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    assert "vlab.digital" not in json.dumps(creative.export_all_data())

    assert creative["asset_feed_spec"]["link_urls"][0]["website_url"] == link
