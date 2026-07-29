import json
import random
from datetime import datetime
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
    pair_creatives_with_destinations,
    web_call_to_action,
)
from .study_conf import (
    Audience,
    AudienceConf,
    CreativeConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    GeneralConf,
    InvalidConfigError,
    Lookalike,
    LookalikeAudience,
    LookalikeSpec,
    Partitioning,
    Stratum,
    StudyConf,
    UserInfo,
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


def test_create_creative_preserves_link_from_template_link_data():
    template = _load_template("image_ad_messenger.json")

    conf = CreativeConf(destination="messenger", name="foo", template=template)
    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["object_story_spec"]["link_data"]["link"] == (
        template["object_story_spec"]["link_data"]["link"]
    )


def test_create_creative_from_template_photo_messenger():
    template = _load_template("photo_ad_messenger.json")

    conf = CreativeConf(destination="messenger", name="foo", template=template)
    cta = messenger_call_to_action()
    welcome_message = '{"foo": ""welcome message"}'
    creative = _create_creative(conf, cta, welcome_message)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    # Photo-only templates must be converted to link_data so the messenger
    # CTA and welcome message can be attached, and Facebook's required link
    # field can be supplied.
    assert "photo_data" not in creative["object_story_spec"]
    link_data = creative["object_story_spec"]["link_data"]
    assert link_data["call_to_action"].export_all_data() == cta
    assert link_data["image_hash"] == template["object_story_spec"]["photo_data"]["image_hash"]
    assert link_data["message"] == template["object_story_spec"]["photo_data"]["caption"]
    assert link_data["page_welcome_message"] == welcome_message
    assert link_data["link"] == "https://fb.com/messenger_doc/"


def test_create_creative_from_template_photo_web():
    template = _load_template("photo_ad_messenger.json")

    conf = CreativeConf(destination="web", name="foo", template=template)
    link = "foo.com/?bar=baz"
    cta = web_call_to_action(link)
    creative = _create_creative(conf, cta, link=link)

    assert creative["actor_id"] == template["actor_id"]
    assert creative["instagram_user_id"] == template["instagram_user_id"]

    # Photo templates are converted to link_data so the destination CTA can be
    # attached and the required link field is present.
    assert "photo_data" not in creative["object_story_spec"]
    link_data = creative["object_story_spec"]["link_data"]
    assert link_data["call_to_action"].export_all_data() == cta
    assert link_data["image_hash"] == template["object_story_spec"]["photo_data"]["image_hash"]
    assert link_data["message"] == template["object_story_spec"]["photo_data"]["caption"]
    assert link_data["link"] == link


# ---------------------------------------------------------------------------
# Destination experiments: every creative must get its OWN destination.
#
# Regression cover for the pairing bug introduced in 4ec9eff6 (Feb 2024) and
# found in production in Jul 2026: the creatives were filtered per arm but the
# destinations were not, and zip() truncated to the shorter list. Every arm
# after the leading one silently published with the leading arm's shortcode.
# ---------------------------------------------------------------------------


def _messenger_dest(name, shortcode):
    return FlyMessengerDestination(
        type="messenger",
        name=name,
        initial_shortcode=shortcode,
        welcome_message="Welcome!",
        button_text="OK",
    )


def _creative(name, destination):
    return CreativeConf(destination=destination, name=name, template={})


def _destination_experiment_study(destinations, creatives):
    return StudyConf(
        id="study-1",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=destinations,
        audiences=[],
        creatives=creatives,
        strata=[],
        recruitment=DestinationRecruitmentExperiment(
            ad_campaign_name_base="test-campaign",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="CONVERSATIONS",
            destination_type="MESSENGER",
            min_budget=1,
            budget_per_arm=100,
            max_sample_per_arm=100,
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 8, 1),
            destinations=[d.name for d in destinations],
        ),
    )


def _stratum(creatives):
    return Stratum(
        id="stratum-1",
        quota=1.0,
        creatives=creatives,
        facebook_targeting={},
        metadata={},
    )


def _shortcodes(pairs):
    return [d.initial_shortcode for _, d in pairs]


def test_pairing_each_arm_gets_own_destination_when_arms_are_contiguous():
    """The exact production scenario (OWIS Nigeria, Jul 2026).

    Four arm-A creatives occupy positions 0-3 and four arm-B creatives
    positions 4-7. Under the bug, arm B's campaign zipped its 4 creatives
    against destinations[0:4] -- all arm A -- and published every ad with
    arm A's shortcode. Arm A looked correct purely by ordering luck.
    """
    dest_a = _messenger_dest("Arm A", "shortcode_a")
    dest_b = _messenger_dest("Arm B", "shortcode_b")

    creatives = [_creative(f"a{i}", "Arm A") for i in range(4)]
    creatives += [_creative(f"b{i}", "Arm B") for i in range(4)]

    study = _destination_experiment_study([dest_a, dest_b], creatives)
    stratum = _stratum(creatives)

    pairs_b = pair_creatives_with_destinations(study, stratum, "test-campaign-Arm B")
    assert [c.name for c, _ in pairs_b] == ["b0", "b1", "b2", "b3"]
    assert _shortcodes(pairs_b) == ["shortcode_b"] * 4

    pairs_a = pair_creatives_with_destinations(study, stratum, "test-campaign-Arm A")
    assert [c.name for c, _ in pairs_a] == ["a0", "a1", "a2", "a3"]
    assert _shortcodes(pairs_a) == ["shortcode_a"] * 4


def test_pairing_is_independent_of_creative_ordering():
    """Interleaved ordering (the Ghana pilots) must pair correctly too.

    With arms interleaved the bug scrambled BOTH arms rather than
    collapsing one, so ordering must not influence the result at all.
    """
    dest_a = _messenger_dest("Arm A", "shortcode_a")
    dest_b = _messenger_dest("Arm B", "shortcode_b")

    creatives = []
    for i in range(4):
        creatives.append(_creative(f"a{i}", "Arm A"))
        creatives.append(_creative(f"b{i}", "Arm B"))

    study = _destination_experiment_study([dest_a, dest_b], creatives)
    stratum = _stratum(creatives)

    for name, shortcode in [("Arm A", "shortcode_a"), ("Arm B", "shortcode_b")]:
        pairs = pair_creatives_with_destinations(
            study, stratum, f"test-campaign-{name}"
        )
        assert len(pairs) == 4
        assert _shortcodes(pairs) == [shortcode] * 4
        assert all(c.destination == name for c, _ in pairs)


def test_pairing_holds_when_arms_have_different_creative_counts():
    """Unequal arm sizes are where a truncating zip does the most damage."""
    dest_a = _messenger_dest("Arm A", "shortcode_a")
    dest_b = _messenger_dest("Arm B", "shortcode_b")

    creatives = [_creative(f"a{i}", "Arm A") for i in range(6)]
    creatives += [_creative(f"b{i}", "Arm B") for i in range(2)]

    study = _destination_experiment_study([dest_a, dest_b], creatives)
    stratum = _stratum(creatives)

    pairs_b = pair_creatives_with_destinations(study, stratum, "test-campaign-Arm B")
    assert _shortcodes(pairs_b) == ["shortcode_b"] * 2

    pairs_a = pair_creatives_with_destinations(study, stratum, "test-campaign-Arm A")
    assert _shortcodes(pairs_a) == ["shortcode_a"] * 6


def test_pairing_raises_when_campaign_matches_no_destination():
    dest_a = _messenger_dest("Arm A", "shortcode_a")
    creatives = [_creative("a0", "Arm A")]
    study = _destination_experiment_study([dest_a], creatives)
    stratum = _stratum(creatives)

    with pytest.raises(Exception, match="Could not find destination"):
        pair_creatives_with_destinations(study, stratum, "campaign-with-no-arm")
