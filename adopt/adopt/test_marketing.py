import json
import random
import re
from datetime import datetime
from typing import TypeVar
from unittest.mock import patch
from urllib.parse import unquote

import pytest
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience

from .facebook.field_contract import COMPARED_ADSET
from .ref_encoding import decode_recruitment_ref, encoded_ref
from .facebook.reconciliation import ad_dif
from .facebook.update import Instruction
from .marketing import (
    assert_ref_tokens_unique,
    _create_creative,
    ad_provenance,
    adset_destination_type,
    adset_instructions,
    ad_ref_token,
    adset_promoted_object,
    create_ad,
    create_creative,
    creative_metadata,
    destination_shortcode,
    dotted_ref,
    make_multi_welcome_message,
    make_ref,
    manage_aud,
    messenger_call_to_action,
    pair_creatives_with_destinations,
    ref_metadata,
    shortcode_ref,
    web_call_to_action,
    whatsapp_autofill,
    whatsapp_ref,
)
from .study_conf import (
    InvalidConfigError,
    AppDestination,
    Audience,
    AudienceConf,
    CreativeConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    GeneralConf,
    InvalidConfigError,
    Lookalike,
    LookalikeAudience,
    LookalikeSpec,
    Partitioning,
    Stratum,
    StudyConf,
    UserInfo,
    WebDestination,
    destination_type_for,
    ref_value,
    whatsapp_ref_token_safe,
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


def _messenger_dest(name, shortcode, ref_mode=None):
    return FlyMessengerDestination(
        type="messenger",
        name=name,
        initial_shortcode=shortcode,
        welcome_message="Welcome!",
        button_text="OK",
        ref_mode=ref_mode,
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


# ---------------------------------------------------------------------------
# Ad-ID attribution (A1): the frozen metadata blob.
#
# vlab is taking over the ad -> stratum join from the dotted ref string. The
# blob frozen into ad_attributions.metadata has to be exactly what the ref
# carried -- if the two ever drift, a respondent resolves to no stratum, which
# does not error, it miscounts, and the optimizer reallocates budget away from
# a stratum that is actually recruiting fine. These tests are the guard.
# ---------------------------------------------------------------------------


def _parse_ref(ref: str) -> dict:
    """Parse a ref the way fly does, so this is a real round trip.

    Mirrors getMetadata in replybot/lib/typewheels/utils.js:75-105:
    split on ".", URL-decode every token, then pair them up. Deliberately a
    re-implementation of the *consumer's* grammar rather than an inverse of
    make_ref -- an inverse written from make_ref would agree with make_ref by
    construction and prove nothing.
    """
    tokens = [unquote(t) for t in ref.split(".")]
    return dict(zip(tokens[::2], tokens[1::2]))


def _web_dest(name, url_template="https://survey.example/?r={ref}", ref_mode=None):
    return WebDestination(
        type="web", name=name, url_template=url_template, ref_mode=ref_mode
    )


def _study(destinations, creatives, extra_metadata=None):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
            extra_metadata=extra_metadata or {},
        ),
        destinations=destinations,
        audiences=[],
        creatives=creatives,
        strata=[],
        recruitment=DestinationRecruitmentExperiment(
            ad_campaign_name_base="test-campaign",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="CONVERSATIONS",
            min_budget=1,
            budget_per_arm=100,
            max_sample_per_arm=100,
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 8, 1),
            destinations=[d.name for d in destinations],
        ),
    )


def _stratum_with_md(id_, creatives, metadata):
    return Stratum(
        id=id_,
        quota=1.0,
        creatives=creatives,
        facebook_targeting={},
        metadata=metadata,
    )


# Shaped like production: stratum keys with spaces and mixed case, exactly the
# sort of thing seen in fly's responses table (Age/Region/creative/form).
PRODUCTION_METADATA = {
    "Age": "Like Parents",
    "Region": "South East",
    "gender": "women",
}


def test_frozen_metadata_equals_the_parsed_ref():
    """THE invariant. The blob we freeze == what the ref would have delivered.

    If this ever fails, the ad-ID join and the ref-based join disagree, and
    every study straddling the two produces two different stratum assignments
    for the same respondent.
    """
    dest = _messenger_dest("messenger", "mnchweek")
    creative = _creative("Static English - Girls", "messenger")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    assert _parse_ref(make_ref(creative.name, md)) == frozen


def test_frozen_metadata_carries_creative_and_form_which_stratum_metadata_lacks():
    """The specific way this goes wrong: freezing stratum.metadata instead.

    `creative` is prepended by make_ref and `form` is added by
    create_creative, so neither is in the stratum conf. An extraction conf
    asking for either would silently match nobody.
    """
    dest = _messenger_dest("messenger", "mnchweek")
    creative = _creative("Static English - Girls", "messenger")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    frozen = ref_metadata(creative.name, creative_metadata(study, stratum, dest))

    assert frozen["creative"] == "Static English - Girls"
    assert frozen["form"] == "mnchweek"

    # ...and both are absent from the thing it would be tempting to freeze.
    assert "creative" not in stratum.metadata
    assert "form" not in stratum.metadata
    assert frozen != stratum.metadata


def test_frozen_metadata_round_trips_for_a_web_destination():
    """Web destinations get no `form` key, and the round trip still holds."""
    dest = _web_dest("web")
    creative = _creative("Smiling", "web")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    assert "form" not in frozen
    assert _parse_ref(make_ref(creative.name, md)) == frozen


def test_frozen_metadata_includes_extra_and_additional_metadata():
    """extra_metadata (study-wide) and additional_metadata (per-destination).

    Both are folded in before make_ref runs, so both must be in the blob.
    """
    dest = FlyMessengerDestination(
        type="messenger",
        name="messenger",
        initial_shortcode="mnchweek",
        welcome_message="Welcome!",
        button_text="OK",
        additional_metadata={"wave": "2"},
    )
    creative = _creative("Smiling", "messenger")
    study = _study([dest], [creative], extra_metadata={"country": "NG"})
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    assert frozen["country"] == "NG"
    assert frozen["wave"] == "2"
    assert _parse_ref(make_ref(creative.name, md)) == frozen


def test_frozen_metadata_resolves_a_creative_key_collision_the_way_the_ref_does():
    """A stratum that declares its own `creative` key.

    make_ref writes `creative.<name>` first and the metadata pair second, so a
    dot-pair parser keeps the *later* one. `{"creative": name, **md}` keeps the
    later one too. Pathological, but the two must agree even here.
    """
    dest = _web_dest("web")
    creative = _creative("Smiling", "web")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"creative": "declared"})

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    assert frozen["creative"] == "declared"
    assert _parse_ref(make_ref(creative.name, md)) == frozen


def test_the_round_trip_closes_for_a_dotted_value():
    """This test used to assert the corruption. Now it asserts the fix.

    `quote()` never escapes `.`, so a dotted value used to split into extra
    tokens and the ref parsed back to garbage, silently mis-pairing every
    key/value after it. `ref_value` now encodes it as %2E, and `_parse_ref` --
    which reimplements fly's own decode-then-pair rather than inverting
    make_ref -- puts it back. Still a genuine inverse, not an agreement by
    construction.
    """
    dest = _web_dest("web")
    creative = _creative("Smiling", "web")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"city": "St. Louis"})

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    # The blob is untouched: it always held the raw value and still does.
    assert frozen["city"] == "St. Louis"

    ref = make_ref(creative.name, md)
    assert "St%2E%20Louis" in ref
    assert _parse_ref(ref) == frozen


def test_destination_shortcode_only_for_fly_destinations():
    assert destination_shortcode(_messenger_dest("m", "mnchweek")) == "mnchweek"
    assert destination_shortcode(_web_dest("web")) is None


def test_ad_provenance_is_keyed_by_stratum_and_creative_name():
    """The key must match how reconciliation identifies an ad.

    adset name == stratum.id (create_adset) and ad name == creative.name
    (create_ad). If this key drifts, provenance silently stops matching and
    ads get created with no mapping row.
    """
    dest = _messenger_dest("messenger", "mnchweek")
    creatives = [_creative("Smiling", "messenger"), _creative("Serious", "messenger")]
    study = _study([dest], creatives)
    strata = [
        _stratum_with_md("stratum-1", creatives, {"gender": "women"}),
        _stratum_with_md("stratum-2", creatives, {"gender": "men"}),
    ]

    prov = ad_provenance(study, "test-campaign-messenger", strata)

    assert set(prov.keys()) == {
        ("stratum-1", "Smiling"),
        ("stratum-1", "Serious"),
        ("stratum-2", "Smiling"),
        ("stratum-2", "Serious"),
    }


def test_ad_provenance_row_contents():
    dest = _messenger_dest("messenger", "mnchweek")
    creative = _creative("Smiling", "messenger")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"gender": "women"})

    prov = ad_provenance(study, "test-campaign-messenger", [stratum])

    assert prov[("stratum-1", "Smiling")] == {
        "study_id": "00000000-0000-0000-0000-000000000001",
        "stratum_id": "stratum-1",
        "creative_name": "Smiling",
        "shortcode": "mnchweek",
        "metadata": {
            "gender": "women",
            "form": "mnchweek",
            "creative": "Smiling",
        },
        "resolved_from": "ad_id",
        # None under every ref mode but "encoded": this destination's ref
        # carries no token, which is a fact about the ad rather than a gap.
        "ref_token": None,
    }


def test_ad_provenance_agrees_with_the_ref_the_ad_actually_ships():
    """End-to-end: the provenance blob vs. the ref inside the real creative.

    create_creative puts the ref in two places for a messenger destination --
    url_tags and the welcome-message quick-reply payload. Both are pulled back
    out here and parsed, so this catches drift between ad_provenance and
    create_creative even if creative_metadata is refactored away.
    """
    dest = _messenger_dest("messenger", "mnchweek")
    creative_conf = _creative("Smiling", "messenger")
    study = _study([dest], [creative_conf])
    stratum = _stratum_with_md("stratum-1", [creative_conf], PRODUCTION_METADATA)

    template = _load_template("image_ad_messenger.json")
    creative_conf = CreativeConf(
        destination="messenger", name="Smiling", template=template
    )

    ad_creative = create_creative(study, stratum, creative_conf, dest)
    prov = ad_provenance(study, "test-campaign-messenger", [stratum])
    frozen = prov[("stratum-1", "Smiling")]["metadata"]

    shipped_ref = ad_creative["url_tags"].removeprefix("ref=")
    assert _parse_ref(shipped_ref) == frozen

    payload = json.loads(
        json.loads(ad_creative["object_story_spec"]["link_data"]["page_welcome_message"])
        ["message"]["quick_replies"][0]["payload"]
    )
    assert _parse_ref(payload["referral"]["ref"]) == frozen


def test_ad_provenance_touches_no_database():
    """Purity guard: generation stays in the functional core.

    The write belongs in run_instructions. If anyone ever reaches for the DB
    from here, every _dif test becomes an integration test.
    """
    dest = _messenger_dest("messenger", "mnchweek")
    creative = _creative("Smiling", "messenger")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"gender": "women"})

    def _explode(*args, **kwargs):
        raise AssertionError("ad_provenance must not open a database connection")

    with patch("adopt.db._connect", _explode):
        prov = ad_provenance(study, "test-campaign-messenger", [stratum])

    assert len(prov) == 1


# ---------------------------------------------------------------------------
# Click-to-WhatsApp destinations (A8).
#
# A CTWA referral carries no advertiser-settable `ref` -- url_tags was measured
# not to reach WhatsApp at all -- so fly recovers the shortcode from the ad's
# autofill text, which prefills the respondent's first message. fly matches that
# text against an anchored, full-match pattern, and anything that fails it is
# not an error: no conversation_started is derived and the arrival falls through
# to FALLBACK_FORM, a real survey whose users look like completions. So these
# tests assert against the real pattern, copied verbatim.
# ---------------------------------------------------------------------------

# Copied verbatim from WHATSAPP_ENTRY_REF in fly's
# replybot/lib/event-normalizer.js at replybot-v0.0.221 -- the tag deployed in
# vprod and vstag, read off the tag rather than off any checkout on 2026-08-26.
# Kept as a literal rather than imported (different repo, different language).
#
# THIS COPY HAS NOW GONE STALE TWICE, both times one fly widening behind:
#
#   v0.0.218   `form.` must LEAD; token alphabet [A-Za-z0-9_-]
#   v0.0.219   `form.` must LEAD; alphabet widened to accept %XX octets
#   v0.0.220   the `form` PAIR MAY APPEAR ANYWHERE in the pair list
#   v0.0.221   unchanged from v0.0.220; currently deployed
#
# The copy sat at v0.0.219 while v0.0.221 ran. Nothing detected it, in either
# direction, in either repo. `test_ref_encoding_contract.py` now does: it runs
# this pattern against gate vectors measured on the deployed tag, so the next
# widening fails a test rather than aging quietly inside this comment.
#
# Both drifts happened to be in the safe direction -- this copy was STRICTER
# than production, so adopt refused refs fly would have accepted, a false
# negative on deliverability rather than a misroute. That is a fact about the
# last two changes, not a property of the arrangement.
WHATSAPP_ENTRY_REF = re.compile(
    r"^(?:start\s+)?"
    r"((?:(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+"
    r"\.(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+\.)*)"
    r"form\.((?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+)"
    r"((?:\.(?:[A-Za-z0-9_-]|%[0-9A-Fa-f]{2})+)*)$",
    re.IGNORECASE,
)


# The second anchor, copied verbatim from WHATSAPP_ENTRY_REF_ENCODED in the same
# file at fly@feature/recruitment-arrival-health 341be39a.
#
# A distinct anchor rather than a widening of the first, deliberately: `form.` is
# always dot-pairs and `r.` is always opaque, so fly never has to guess which
# grammar it is looking at. Note the capture group preserves case -- base64url is
# case-significant, so a gate that lowercased the token would corrupt every
# encoded ref while appearing to accept it.
WHATSAPP_ENTRY_REF_ENCODED = re.compile(
    r"^(?:start\s+)?r\.([A-Za-z0-9_-]+)$",
    re.IGNORECASE,
)


def _fly_would_accept(text: str) -> bool:
    """What fly's _refFromText does: full match on the trimmed body.

    Either anchor, since fly tries the encoded pattern first and falls back to
    the dotted one -- that is a choice between two *grammars*, made by what the
    text starts with, not a fallback between attribution mechanisms.
    """
    text = text.strip()
    return bool(
        WHATSAPP_ENTRY_REF_ENCODED.match(text) or WHATSAPP_ENTRY_REF.match(text)
    )


def _whatsapp_dest(shortcode="mnchweek", additional=None, ref_mode=None):
    return FlyWhatsAppDestination(
        type="whatsapp",
        name="whatsapp",
        initial_shortcode=shortcode,
        welcome_message="Tap send to start",
        whatsapp_phone_number="+1-541-920-2635",
        additional_metadata=additional,
        ref_mode=ref_mode,
    )


def _whatsapp_study(destinations, creatives, extra_metadata=None):
    return _study(destinations, creatives, extra_metadata)


def test_the_autofill_head_alone_is_accepted_by_fly():
    """The head is what routes, and it always parses."""
    assert shortcode_ref("mnchweek") == "form.mnchweek"
    assert _fly_would_accept(shortcode_ref("mnchweek"))


def test_the_autofill_head_survives_underscores_and_hyphens():
    for shortcode in ["mnch_week", "mnch-week-2", "MNCHweek2"]:
        assert _fly_would_accept(shortcode_ref(shortcode)), shortcode


def test_full_ref_with_pattern_safe_values_is_accepted_by_fly():
    md = {"creative": "Smiling", "gender": "women", "form": "mnchweek"}
    autofill = whatsapp_autofill("mnchweek", md)

    assert autofill == "form.mnchweek.creative.Smiling.gender.women"
    assert _fly_would_accept(autofill)


def test_the_deployed_gate_no_longer_rejects_make_ref_output():
    """The disjointness this design was built on has been REMOVED under us.

    Until replybot-v0.0.219 fly's WhatsApp pattern anchored on `form.` while
    `make_ref` leads with `creative.`, so a Messenger ref could not match it
    whatever its values were. That structural fact is what
    `whatsapp_autofill`'s separate form-first serialisation was justified by,
    and it is what `documentation/ad-attributions.md` recorded as "verified
    directly against that regex".

    replybot-v0.0.220 widened the pattern so the `form` PAIR may appear
    anywhere in the pair list, and v0.0.221 -- what runs -- carries that. Since
    `creative.<name>` is itself two tokens and every metadata entry adds two
    more, `form` always lands on a pair boundary, so `make_ref`'s output now
    matches the deployed gate ALWAYS rather than never.

    Nothing breaks: `whatsapp_ref` still emits form-first, every live ad
    carries that, and this test does not license changing it. What changes is
    the *reason* -- form-first is now the serialisation vlab ships, not the
    only one fly can read. Asserted rather than deleted so the next person does
    not rediscover the old claim in a docstring and trust it.
    """
    md = {"creative": "Smiling", "gender": "women", "form": "mnchweek"}
    assert _fly_would_accept(make_ref("Smiling", md))

    # Still rejected, and this is the part that stayed structural: a ref with
    # no `form` pair at all cannot route. That is what a web or app
    # destination's ref looks like -- `creative_metadata` folds `form` in for
    # fly destinations only.
    assert not _fly_would_accept(make_ref("Smiling", {"gender": "women"}))


def test_full_ref_round_trips_back_to_the_frozen_blob():
    """The autofill and ad_attributions.metadata describe the same thing.

    Parsing the autofill's dot-pairs must give exactly the blob frozen at ad
    creation -- the same invariant make_ref has on Messenger, so a study can use
    either channel and get identical strata.
    """
    dest = _whatsapp_dest()
    creative = _creative("Smiling", "whatsapp")
    study = _whatsapp_study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"gender": "women"})

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)
    autofill = whatsapp_autofill(dest.initial_shortcode, frozen)

    assert _fly_would_accept(autofill)
    assert _parse_ref(autofill) == frozen


def test_whatsapp_creative_metadata_folds_in_form_like_messenger_does():
    """Keeps the frozen blob consistent across both fly channels.

    A study using `location: "ad"` must read the same keys whether its
    respondents arrived by Messenger or WhatsApp.
    """
    dest = _whatsapp_dest(additional={"wave": "2"})
    creative = _creative("Smiling", "whatsapp")
    study = _whatsapp_study([dest], [creative], extra_metadata={"country": "NG"})
    stratum = _stratum_with_md("stratum-1", [creative], {"gender": "women"})

    md = creative_metadata(study, stratum, dest)

    assert md["form"] == "mnchweek"
    assert md["country"] == "NG"
    assert md["wave"] == "2"
    assert md["gender"] == "women"


def test_whatsapp_destination_has_a_shortcode():
    assert destination_shortcode(_whatsapp_dest()) == "mnchweek"


def test_whatsapp_creative_uses_the_whatsapp_cta_and_carries_no_url_tags():
    """url_tags was measured never to reach WhatsApp, so it must not be set.

    Setting it would be dead weight that reads like a working carrier.
    """
    dest = _whatsapp_dest()
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="whatsapp", name="Smiling", template=template)
    study = _whatsapp_study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})

    creative = create_creative(study, stratum, config, dest)

    link_data = creative["object_story_spec"]["link_data"]
    assert link_data["call_to_action"].export_all_data() == {
        "type": "WHATSAPP_MESSAGE",
        "value": {"app_destination": "WHATSAPP"},
    }
    assert link_data["link"] == "https://api.whatsapp.com/send"
    assert "url_tags" not in creative


def test_whatsapp_creative_prefills_the_form_first_ref():
    dest = _whatsapp_dest()
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="whatsapp", name="Smiling", template=template)
    study = _whatsapp_study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, dest)

    welcome = json.loads(
        creative["object_story_spec"]["link_data"]["page_welcome_message"]
    )
    autofill = welcome["text_format"]["message"]["autofill_message"]["content"]

    # The stratum here has spaces in its values, which the widened gate accepts
    # percent-encoded.
    assert autofill.startswith("form.mnchweek.")
    assert _fly_would_accept(autofill)
    assert welcome["text_format"]["message"]["text"] == "Tap send to start"


def test_existing_destinations_are_untouched_by_the_whatsapp_branch():
    """Messenger and Web must be bit-for-bit what they were.

    A8 is greenfield, but it edits create_creative, which every live study's
    creative flows through -- and changing a creative rewrites every ad.
    """
    template = _load_template("image_ad_messenger.json")

    messenger = _messenger_dest("messenger", "mnchweek")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    study = _study([messenger], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, messenger)
    md = creative_metadata(study, stratum, messenger)

    # Still the Messenger CTA, still url_tags carrying the full quoted ref.
    assert creative["url_tags"] == f"ref={make_ref('Smiling', md)}"
    assert creative["object_story_spec"]["link_data"][
        "call_to_action"
    ].export_all_data() == {
        "type": "MESSAGE_PAGE",
        "value": {"app_destination": "MESSENGER"},
    }

    web = _web_dest("web")
    web_config = CreativeConf(destination="web", name="Smiling", template=template)
    web_study = _study([web], [web_config])
    web_creative = create_creative(web_study, stratum, web_config, web)
    assert destination_shortcode(web) is None
    assert "whatsapp" not in json.dumps(web_creative.export_all_data()).lower()


# ---------------------------------------------------------------------------
# Adset promoted_object (A9).
#
# Meta will not accept a WHATSAPP destination_type ad set without a
# promoted_object naming the Page and the number. promoted_object is an ad set
# field while destinations are per-creative, so this is also where the standing
# `# TODO: assert all destinations are the same` lived -- flagged in
# planning/click-to-whatsapp-ads.md as a latent bug to fix rather than inherit.
# ---------------------------------------------------------------------------


def _template_with_page(page_id="page-123"):
    return {"object_story_spec": {"page_id": page_id, "link_data": {}}}


def _app_dest(name="app", ref_mode=None):
    return AppDestination(
        type="app",
        name=name,
        ref_mode=ref_mode,
        facebook_app_id="app-1",
        app_install_link="https://play.example/app",
        deeplink_template="myapp://start?ref={ref}",
        app_install_state="installed",
        user_device=["Android_Smartphone"],
        user_os=["Android"],
    )


def test_whatsapp_promoted_object_names_the_page_and_the_number():
    dest = _whatsapp_dest()
    config = CreativeConf(
        destination="whatsapp", name="Smiling", template=_template_with_page()
    )

    assert adset_promoted_object([(config, dest)]) == {
        "page_id": "page-123",
        # Digits only: the promoted-object reference types this as a numeric
        # string, while the conf may carry the display form.
        "whatsapp_phone_number": "15419202635",
    }


def test_whatsapp_promoted_object_takes_its_page_from_the_creative_template():
    """Same source _create_creative uses for object_story_spec.page_id.

    If these two ever named different Pages the ad set and its creative would
    disagree, so they read the same field.
    """
    dest = _whatsapp_dest()
    config = CreativeConf(
        destination="whatsapp", name="Smiling", template=_template_with_page("page-999")
    )

    assert adset_promoted_object([(config, dest)])["page_id"] == "page-999"


def test_whatsapp_without_a_page_id_in_the_template_fails_loudly():
    dest = _whatsapp_dest()
    config = CreativeConf(destination="whatsapp", name="Smiling", template={})

    with pytest.raises(Exception, match="page_id"):
        adset_promoted_object([(config, dest)])


def test_messenger_and_web_still_need_no_promoted_object():
    messenger = _messenger_dest("messenger", "mnchweek")
    web = _web_dest("web")
    m_config = CreativeConf(destination="messenger", name="A", template={})
    w_config = CreativeConf(destination="web", name="B", template={})

    assert adset_promoted_object([(m_config, messenger)]) is None
    assert adset_promoted_object([(w_config, web)]) is None
    # Mixing them is still fine: neither wants one, so there is nothing to
    # disagree about, and this is exactly what live studies do today.
    assert adset_promoted_object([(m_config, messenger), (w_config, web)]) is None


def test_app_promoted_object_is_byte_identical_to_what_it_always_was():
    dest = _app_dest()
    config = CreativeConf(destination="app", name="A", template={})

    assert adset_promoted_object([(config, dest)]) == {
        "application_id": "app-1",
        "object_store_url": "https://play.example/app",
    }


def test_several_creatives_agreeing_produce_one_promoted_object():
    dest = _whatsapp_dest()
    pairs = [
        (
            CreativeConf(
                destination="whatsapp", name=n, template=_template_with_page()
            ),
            dest,
        )
        for n in ["A", "B", "C"]
    ]

    assert adset_promoted_object(pairs) == {
        "page_id": "page-123",
        "whatsapp_phone_number": "15419202635",
    }


def test_creatives_that_disagree_raise_instead_of_silently_picking_one():
    """The latent bug, fixed.

    The old code read destinations[0], so a stratum mixing an app creative with
    anything else published half its ads under the wrong promoted object and
    said nothing.
    """
    app = _app_dest()
    messenger = _messenger_dest("messenger", "mnchweek")
    a_config = CreativeConf(destination="app", name="A", template={})
    m_config = CreativeConf(destination="messenger", name="B", template={})

    with pytest.raises(Exception, match="different ad set promoted"):
        adset_promoted_object([(a_config, app), (m_config, messenger)])


def test_two_whatsapp_numbers_in_one_stratum_raise():
    a = _whatsapp_dest()
    b = FlyWhatsAppDestination(
        type="whatsapp",
        name="other",
        initial_shortcode="mnchweek",
        welcome_message="Hi",
        whatsapp_phone_number="+1-555-000-1111",
    )
    config = CreativeConf(
        destination="whatsapp", name="A", template=_template_with_page()
    )

    with pytest.raises(Exception, match="different ad set promoted"):
        adset_promoted_object([(config, a), (config, b)])


def test_empty_pairs_produce_no_promoted_object():
    assert adset_promoted_object([]) is None


class _FakeCampaignState:
    """Just enough CampaignState for adset_instructions: a name and a campaign."""

    def __init__(self, campaign_name):
        self.campaign_name = campaign_name
        self.campaign = {"id": "campaign-1"}


def _adset_for(destination, template, campaign_suffix):
    """No destination_type argument: the ad set's value is derived from the
    destination, which is the whole point of the field being gone from the
    recruitment conf. Each caller asserts the derived value."""
    config = CreativeConf(
        destination=destination.name, name="Smiling", template=template
    )
    study = _study([destination], [config])
    stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})
    state = _FakeCampaignState(f"test-campaign-{campaign_suffix}")

    adset, _ = adset_instructions(study, state, stratum, 10.0)
    return adset.export_all_data()


def test_messenger_adsets_are_unchanged_and_carry_no_promoted_object():
    """Asserted directly, not inferred. Every live study runs through here."""
    data = _adset_for(
        _messenger_dest("messenger", "mnchweek"), _template_with_page(), "messenger"
    )

    assert "promoted_object" not in data
    assert data["destination_type"] == "MESSENGER"


def test_web_adsets_are_unchanged_and_carry_no_promoted_object():
    data = _adset_for(_web_dest("web"), _template_with_page(), "web")

    assert "promoted_object" not in data
    assert data["destination_type"] == "WEBSITE"


def test_app_adsets_keep_exactly_the_promoted_object_they_always_had():
    data = _adset_for(_app_dest("app"), _template_with_page(), "app")

    assert data["promoted_object"] == {
        "application_id": "app-1",
        "object_store_url": "https://play.example/app",
    }


def test_whatsapp_adsets_get_the_promoted_object_meta_requires():
    """Without this, Meta rejects the ad set outright and the destination type
    is a conf class that cannot produce a working ad."""
    data = _adset_for(_whatsapp_dest(), _template_with_page(), "whatsapp")

    assert data["promoted_object"] == {
        "page_id": "page-123",
        "whatsapp_phone_number": "15419202635",
    }
    assert data["destination_type"] == "WHATSAPP"


# ---------------------------------------------------------------------------
# The ref mode: what an ad's ref carries.
#
# A ref either carries the stratum inline or carries a token that resolves to
# it. The payoff of the second is that vlab stops shipping its whole stratum
# vocabulary to the survey platform inside every message, and the ref does only
# the job it cannot delegate: routing. Attribution comes from the frozen
# ad_attributions row instead.
#
# The hazard is that "what the ref carries" and "what gets frozen" are computed
# from the same dict. They must not move together.
# ---------------------------------------------------------------------------


def _messenger_dest_mode(shortcode="mnchweek", ref_mode=None):
    return FlyMessengerDestination(
        type="messenger",
        name="messenger",
        initial_shortcode=shortcode,
        welcome_message="Welcome!",
        button_text="OK",
        ref_mode=ref_mode,
    )


def _welcome_payload_ref(creative):
    """Dig the ref back out of the quick-reply payload."""
    welcome = json.loads(
        creative["object_story_spec"]["link_data"]["page_welcome_message"]
    )
    payload = json.loads(welcome["message"]["quick_replies"][0]["payload"])
    return payload["referral"]["ref"]


def test_ref_mode_does_not_change_what_gets_frozen():
    """THE guard on the project's core invariant.

    Two destinations identical but for the ref mode, over the same stratum,
    freeze exactly the same blob. The mode picks a serialisation; it never
    touches the metadata computation.

    For an encoded study that frozen row is the only attribution it will ever
    have. If the mode leaked into creative_metadata, such a study would freeze
    rows holding nothing but `form`, every lookup conf would resolve to nothing,
    every stratum would count zero, and the optimizer would reallocate on empty
    data -- silently, and unrecoverably, since the blob is frozen at creation.
    """
    full = _messenger_dest_mode()
    encoded = _messenger_dest_mode(ref_mode="encoded")
    creative = _creative("Smiling", "messenger")

    study_full = _study([full], [creative])
    study_encoded = _study([encoded], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    md_full = creative_metadata(study_full, stratum, full)
    md_encoded = creative_metadata(study_encoded, stratum, encoded)

    assert md_full == md_encoded

    frozen_full = ref_metadata(creative.name, md_full)
    frozen_encoded = ref_metadata(creative.name, md_encoded)

    assert frozen_full == frozen_encoded

    # ...and it is still the complete blob, not a shrunken one.
    assert frozen_encoded["creative"] == "Smiling"
    assert frozen_encoded["form"] == "mnchweek"
    for key, value in PRODUCTION_METADATA.items():
        assert frozen_encoded[key] == value


def test_ad_provenance_is_identical_under_both_ref_modes():
    """The same invariant one layer up, at what actually reaches the database.

    Only `ref_token` differs, which is the point of the mode: an encoded ad
    carries a join key and a metadata ad does not.
    """
    creative = _creative("Smiling", "messenger")
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    provenances = []
    for mode in [None, "encoded"]:
        dest = _messenger_dest_mode(ref_mode=mode)
        study = _study([dest], [creative])
        provenances.append(ad_provenance(study, "test-campaign-messenger", [stratum]))

    without_token = [
        {k: v for k, v in entry.items() if k != "ref_token"}
        for provenance in provenances
        for entry in provenance.values()
    ]

    assert without_token[0] == without_token[1]


def test_an_encoded_ad_emits_the_same_token_on_both_carriers():
    """Messenger ships the ref twice and a respondent can arrive by either.

    Emitting different refs on the two paths would mean one ad describing two
    different people depending on how they tapped it.
    """
    dest = _messenger_dest_mode(ref_mode="encoded")
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, dest)

    token = ad_ref_token(study, stratum, config, dest)
    expected = encoded_ref("mnchweek", token)

    assert creative["url_tags"] == f"ref={expected}"
    assert _welcome_payload_ref(creative) == expected


def test_shortcode_ref_routes_in_fly():
    """fly parses referral.ref as dot-pairs and routes on `md.form`.

    `form.<shortcode>` is the head of the WhatsApp autofill, and the minimum
    that survives that parse: getMetadata falls back to FALLBACK_FORM when
    `form` is absent, and the fallback is a real survey, so a ref that loses
    `form` recruits people into the wrong study without erroring.
    """
    assert _parse_ref(shortcode_ref("mnchweek")) == {"form": "mnchweek"}


def test_the_metadata_mode_is_the_default_so_stored_confs_are_unaffected():
    # An existing destinations conf has no such key. It must resolve to the
    # behaviour it has today, without anyone rewriting stored JSON.
    dest = FlyMessengerDestination(
        type="messenger",
        name="messenger",
        initial_shortcode="mnchweek",
        welcome_message="Welcome!",
        button_text="OK",
    )
    assert dest.ref_mode is None
    assert dest.resolved_ref_mode == "metadata"


def test_every_destination_type_carries_a_ref_mode():
    """Web and app included. What a ref carries is a property of the ref, not
    of the channel carrying it, so nothing asking `resolved_ref_mode` needs a
    type check."""
    destinations = [
        _messenger_dest_mode(),
        _whatsapp_dest(),
        _multi_dest(),
        _web_dest("web"),
        _app_dest("app"),
    ]

    assert [d.resolved_ref_mode for d in destinations] == ["metadata"] * 5


def test_messenger_creatives_are_byte_identical_when_the_mode_is_unset():
    """Asserted directly. Every live study runs through this path.

    `make_ref` is untouched, so pinning both carriers to its exact output is
    what "unchanged" means here.
    """
    dest = FlyMessengerDestination(
        type="messenger",
        name="messenger",
        initial_shortcode="mnchweek",
        welcome_message="Welcome!",
        button_text="OK",
    )
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, dest)
    md = creative_metadata(study, stratum, dest)
    expected = make_ref("Smiling", md)

    assert creative["url_tags"] == f"ref={expected}"
    assert _welcome_payload_ref(creative) == expected

    # The full dotted form, with its percent-encoding, exactly as before.
    assert expected.startswith("creative.Smiling.")
    assert "%20" in expected


def test_dotted_ref_selects_only_the_serialisation():
    md = {"creative": "Smiling", "gender": "women", "form": "mnchweek"}
    token = "a1b2c3d4e5"

    full = dotted_ref("Smiling", md, _messenger_dest_mode())
    encoded = dotted_ref("Smiling", md, _messenger_dest_mode(ref_mode="encoded"), token)

    assert full == make_ref("Smiling", md)
    assert encoded == encoded_ref("mnchweek", token)


def test_a_destination_without_a_shortcode_encodes_to_the_bare_token():
    """A web or app destination's template already points at the survey, so
    nothing decodes its ref -- and swoosh compares the extracted value to
    ad_attributions.ref_token verbatim. Wrapping it in the `r.` envelope would
    make it a string no reader unwraps, and encode_recruitment_ref needs a
    shortcode of 1..255 bytes it does not have."""
    md = {"creative": "Smiling", "gender": "women"}
    token = "a1b2c3d4e5"

    web = _web_dest("web", ref_mode="encoded")
    app = _app_dest("app", ref_mode="encoded")

    assert dotted_ref("Smiling", md, web, token) == token
    assert dotted_ref("Smiling", md, app, token) == token


def test_an_encoded_web_destination_interpolates_the_token_into_its_url():
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="web", name="Smiling", template=template)
    dest = _web_dest("web", ref_mode="encoded")
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})

    creative = create_creative(study, stratum, config, dest)

    token = ad_ref_token(study, stratum, config, dest)
    assert token is not None
    assert token in json.dumps(creative.export_all_data())


def test_flipping_one_study_does_not_touch_another():
    """Flipping the mode rewrites that study's ads -- and only that study's.

    Changing the ref changes the creative, and update_ad compares creatives via
    field_contract.COMPARED_AD, so a flip is a deliberate per-study rewrite.
    Containment is structural (each study is reconciled from its own conf), and
    this pins it: the study nobody touched produces no instructions at all.
    """
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)
    adset = {"id": "adset-1", "name": "stratum-1"}

    def creative_for(mode):
        dest = _messenger_dest_mode(ref_mode=mode)
        return create_creative(_study([dest], [config]), stratum, config, dest)

    live = creative_for(None)

    # Study A flips to encoded: its ad is rewritten in place.
    live_ad = create_ad(adset, live, "ACTIVE")
    live_ad["id"] = "ad-1"
    flipped = ad_dif(
        adset, [live_ad], [create_ad(adset, creative_for("encoded"), "ACTIVE")]
    )
    assert [(i.node, i.action) for i in flipped] == [("ad", "update")]

    # And crucially it is an update against the SAME ad id, not a
    # delete-and-recreate. The ad id is the attribution key, so a flip that
    # minted a new id would strand every ad_attributions row the study already
    # has and leave its past respondents unattributable. Reconciliation matches
    # ads by name, and the name (the creative name) does not change here.
    assert flipped[0].id == "ad-1"

    # Study B, untouched, reconciles to nothing.
    untouched = ad_dif(
        adset,
        [create_ad(adset, live, "ACTIVE")],
        [create_ad(adset, creative_for(None), "ACTIVE")],
    )
    assert untouched == []


def test_web_and_app_destinations_default_to_the_full_ref():
    """Same default as every other type: a conf that states no mode resolves to
    the behaviour it has today."""
    template = _load_template("image_ad_messenger.json")
    stratum_md = {"gender": "women"}

    web = _web_dest("web")
    web_config = CreativeConf(destination="web", name="Smiling", template=template)
    web_study = _study([web], [web_config])
    web_stratum = _stratum_with_md("stratum-1", [web_config], stratum_md)
    web_md = creative_metadata(web_study, web_stratum, web)
    web_creative = create_creative(web_study, web_stratum, web_config, web)

    expected_web = make_ref("Smiling", web_md)
    assert expected_web in json.dumps(web_creative.export_all_data())

    app = _app_dest("app")
    app_config = CreativeConf(destination="app", name="Smiling", template=template)
    app_study = _study([app], [app_config])
    app_stratum = _stratum_with_md("stratum-1", [app_config], stratum_md)
    app_md = creative_metadata(app_study, app_stratum, app)
    app_creative = create_creative(app_study, app_stratum, app_config, app)

    expected_app = make_ref("Smiling", app_md)
    assert expected_app in json.dumps(app_creative.export_all_data())


# ---------------------------------------------------------------------------
# Ref encoding (D2), and the widened WhatsApp gate (D1).
#
# `quote()` never escapes `.` `-` `_` `~` -- they are in urllib's _ALWAYS_SAFE
# and `safe=''` does not override it. Two of those corrupt a dotted ref, and
# the creative name was not passed through `quote()` at all.
# ---------------------------------------------------------------------------


def test_quote_alone_does_not_escape_the_dangerous_characters():
    """The premise, asserted rather than trusted.

    If a future Python changes this, ref_value's double-escape becomes
    redundant and this test says so.
    """
    from urllib.parse import quote as _quote

    assert _quote("a.b") == "a.b"
    assert _quote("x~y") == "x~y"
    assert _quote("a.b", safe="") == "a.b"
    assert _quote("x~y", safe="") == "x~y"


def test_ref_value_encodes_only_what_breaks_the_ref():
    assert ref_value("St. Louis") == "St%2E%20Louis"
    assert ref_value("x~y") == "x%7Ey"
    # separator-safe and inside fly's gate alphabet -- deliberately untouched
    assert ref_value("a-b_c") == "a-b_c"
    assert ref_value("plain") == "plain"
    # a literal % is escaped first, so no . or ~ can hide inside an escape
    assert ref_value("100%") == "100%25"
    assert ref_value("a%2Eb") == "a%252Eb"


def test_refs_without_dots_or_tildes_are_byte_identical():
    """Containment. Only already-broken studies see their ads rewritten.

    These are the real production values on record; every one comes out
    character for character as it always did.
    """
    unchanged = [
        ("Smiling", {"gender": "women"}),
        ("Static English - Girls", {"State": "Bauchi State"}),
        ("3B", {"Age": "Like Parents", "Region": "South East"}),
        ("gelangchoice", {"form": "mnchweek", "creative": "3B"}),
    ]

    for name, md in unchanged:
        expected = "creative." + name.replace(" ", "%20")
        for k, v in md.items():
            expected += f".{k}.{v.replace(' ', '%20')}"
        assert make_ref(name, md) == expected, name


def test_a_dotted_creative_name_used_to_misroute_and_now_round_trips():
    """The creative name was interpolated completely raw -- no quote() at all.

    A dotted *value* shifts the pairs after it, so the respondent is
    mis-attributed. A dotted *name* shifts everything after it including
    `form`, so fly routes them into the wrong survey. Study
    `unicef-immunization-kyrg` ran creative names ending `.png` for about nine
    hours in January 2023.
    """
    md = {"gender": "women", "form": "mnchweek"}
    frozen = ref_metadata("house_help_kids.png", md)

    ref = make_ref("house_help_kids.png", md)

    assert ref.startswith("creative.house_help_kids%2Epng.")
    assert _parse_ref(ref) == frozen
    # the routing key survives in the right place, which is the whole point
    assert _parse_ref(ref)["form"] == "mnchweek"


def test_the_ad_name_is_not_encoded():
    """Encoding is a ref concern only.

    create_ad uses the raw creative name as the Facebook ad name, and
    reconciliation matches ads by name. Encoding it there would orphan every
    live ad and mint new ids -- the ad_attributions-stranding failure A4
    guards against.
    """
    template = _load_template("image_ad_messenger.json")
    config = CreativeConf(
        destination="messenger", name="house_help_kids.png", template=template
    )
    dest = _messenger_dest("messenger", "mnchweek")
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})

    creative = create_creative(study, stratum, config, dest)
    ad = create_ad({"id": "adset-1"}, creative, "ACTIVE")

    assert creative["name"] == "house_help_kids.png"
    assert ad["name"] == "house_help_kids.png"
    assert "%2E" not in ad["name"]


def test_the_frozen_blob_holds_raw_values_not_encoded_ones():
    """The blob holds truth; only transport is encoded.

    A study's ad_attributions.metadata must be identical before and after this
    change, or the encoding would have leaked into attribution.
    """
    md = {"city": "St. Louis", "note": "x~y", "gender": "women"}
    frozen = ref_metadata("banner.png", md)

    assert frozen == {
        "creative": "banner.png",
        "city": "St. Louis",
        "note": "x~y",
        "gender": "women",
    }
    for value in frozen.values():
        assert "%" not in value


# --- D1: the widened WhatsApp gate -----------------------------------------

# The old gate, kept only to measure what changed.
WHATSAPP_ENTRY_REF_OLD = re.compile(
    r"^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$", re.IGNORECASE
)

# The production stratum values recorded in planning/ad-id-attribution.md.
PRODUCTION_VALUES = [
    "3B",
    "gelangchoice",
    "women",
    "Smiling",
    "location",
    "Static English - Girls",
    "Bauchi State",
    "Like Parents",
    "South East",
]


def test_the_widened_gate_recovers_every_recorded_production_value():
    """The re-measurement. 5 of 9 -> 9 of 9.

    Under the old gate a raw value with a space failed, and encoding it failed
    too because `%` was not in the alphabet either. fly now accepts
    percent-encoded octets, so encoding is both correct and sufficient.
    """
    old_ok = sum(
        1 for v in PRODUCTION_VALUES
        if WHATSAPP_ENTRY_REF_OLD.match(f"form.sc.k.{v}")
    )
    new_ok = sum(
        1 for v in PRODUCTION_VALUES
        if WHATSAPP_ENTRY_REF.match(f"form.sc.k.{ref_value(v)}")
    )

    assert old_ok == 5
    assert new_ok == 9

    # the four that were undeliverable, named
    for v in ["Static English - Girls", "Bauchi State", "Like Parents", "South East"]:
        assert not WHATSAPP_ENTRY_REF_OLD.match(f"form.sc.k.{v}")
        assert WHATSAPP_ENTRY_REF.match(f"form.sc.k.{ref_value(v)}")


def test_whatsapp_deliverability_is_now_judged_on_the_encoded_form():
    assert whatsapp_ref_token_safe("Bauchi State")
    assert whatsapp_ref_token_safe("St. Louis")
    assert whatsapp_ref_token_safe("x~y")
    # the one residual: quote() keeps "/" literal by default and the gate
    # does not accept it
    assert not whatsapp_ref_token_safe("North/South")


def test_a_whatsapp_autofill_with_spaces_now_passes_flys_gate():
    dest = _whatsapp_dest()
    creative = _creative("Smiling", "whatsapp")
    study = _whatsapp_study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)
    autofill = whatsapp_autofill(dest.initial_shortcode, frozen)

    assert _fly_would_accept(autofill)
    assert _parse_ref(autofill) == frozen


# ---------------------------------------------------------------------------
# Ad-set destination_type derivation, and multi-destination (type: "multi").
#
# Two changes, one of which is a prerequisite for the other.
#
# `destination_type` used to be ONE string on the recruitment conf consumed by
# every ad set of every arm. It is now derived from each stratum's actual
# (creative, destination) pairs, beside the promoted_object agreement check that
# already existed. That closes two silent misroutes and is what makes both
# "Messenger vs WhatsApp as an experiment arm" and "Messenger + WhatsApp as one
# ad" expressible at all.
#
# On top of that, FlyMultiDestination: one ad whose Messenger arm and WhatsApp
# arm each read their own sub-structure out of a single page_welcome_message
# blob. The Messenger half of that is MEASURED (ad 120254903561240150,
# 2026-08-17). The WhatsApp half is INFERRED from that result by symmetry and
# has never been observed directly.
# ---------------------------------------------------------------------------


def _multi_dest(shortcode="mnchweek", additional=None, name="multi", ref_mode=None):
    return FlyMultiDestination(
        type="multi",
        name=name,
        initial_shortcode=shortcode,
        welcome_message="Tap below or send to start",
        button_text="Start survey",
        whatsapp_phone_number="+1-541-920-2635",
        additional_metadata=additional,
        ref_mode=ref_mode,
    )


def _multi_study(destinations, creatives, extra_metadata=None):
    # No destination_type: a FlyMultiDestination derives
    # MESSAGING_MESSENGER_WHATSAPP on its own.
    return _study(destinations, creatives, extra_metadata)


def _probe_welcome_combined(greeting, button, ref, autofill):
    payload = json.dumps({"referral": {"ref": ref}})
    return json.dumps(
        {
            "type": "VISUAL_EDITOR",
            "version": 2,
            "landing_screen_type": "welcome_message",
            "media_type": "text",
            "text_format": {
                "customer_action_type": "autofill_message",
                "message": {
                    "autofill_message": {"content": autofill},
                    "quick_replies": [
                        {
                            "content_type": "text",
                            "title": button,
                            "payload": payload,
                        }
                    ],
                    "text": greeting,
                },
            },
        },
        sort_keys=True,
    )


def test_the_multi_welcome_blob_is_byte_identical_to_the_probes():
    assert make_multi_welcome_message(
        "Tap below or send to start", "Start survey", "form.mnchweek", "form.mnchweek"
    ) == _probe_welcome_combined(
        "Tap below or send to start", "Start survey", "form.mnchweek", "form.mnchweek"
    )


def _multi_creative(dest, metadata=None, template=None):
    template = template if template is not None else _load_template(
        "image_ad_messenger.json"
    )
    config = CreativeConf(destination=dest.name, name="Smiling", template=template)
    study = _multi_study([dest], [config])
    stratum = _stratum_with_md(
        "stratum-1", [config], PRODUCTION_METADATA if metadata is None else metadata
    )
    return create_creative(study, stratum, config, dest), study, stratum, config


def _welcome(creative, where="object_story_spec"):
    if where == "object_story_spec":
        blob = creative["object_story_spec"]["link_data"]["page_welcome_message"]
    else:
        blob = creative["asset_feed_spec"]["additional_data"]["page_welcome_message"]
    return json.loads(blob)


def test_a_multi_creative_emits_both_carriers_in_one_blob():
    """THE structural claim multi-destination rests on.

    One page_welcome_message string holding both a `quick_replies` array
    (Messenger's carrier for 68% of ad entrants, and their only one) and an
    `autofill_message` (WhatsApp's only carrier of any kind), with
    customer_action_type naming only the latter. Meta stores both -- confirmed
    by reading the creative back -- and delivers the Messenger half.
    """
    dest = _multi_dest()
    creative, _, _, _ = _multi_creative(dest)

    message = _welcome(creative)["text_format"]["message"]

    assert "autofill_message" in message
    assert "quick_replies" in message
    assert message["text"] == "Tap below or send to start"
    assert message["quick_replies"][0]["title"] == "Start survey"


def test_the_blob_goes_on_both_link_data_and_asset_feed_spec():
    """Both, because adopt sets both and a blank welcome screen on only one
    would have a placement explanation rather than a Meta explanation.

    The first multi probe omitted the asset_feed_spec copy, which meant a blank
    welcome screen there would have been misread as "Meta dropped the blob".
    """
    dest = _multi_dest()
    creative, _, _, _ = _multi_creative(dest)

    assert (
        creative["object_story_spec"]["link_data"]["page_welcome_message"]
        == creative["asset_feed_spec"]["additional_data"]["page_welcome_message"]
    )


def test_the_multi_creative_matches_what_the_probe_builds():
    """End to end against the probe's own serialisation, not just its shape."""
    dest = _multi_dest()
    creative, study, stratum, config = _multi_creative(dest)

    md = creative_metadata(study, stratum, dest)
    ref = dotted_ref(config.name, md, dest)
    autofill = whatsapp_ref(config.name, md, dest)

    assert creative["object_story_spec"]["link_data"][
        "page_welcome_message"
    ] == _probe_welcome_combined(
        dest.welcome_message, dest.button_text, ref, autofill
    )


def test_the_multi_creative_carries_url_tags_and_the_messenger_fallback_cta(
):
    """url_tags stays: it is Messenger's other carrier, the 32% floor.

    And the single-valued CTA stays MESSAGE_PAGE, which is Meta's documented
    fallback for a multi-destination creative -- the real destination array
    lives on asset_feed_spec.
    """
    dest = _multi_dest()
    creative, study, stratum, config = _multi_creative(dest)

    md = creative_metadata(study, stratum, dest)
    assert creative["url_tags"] == f"ref={dotted_ref(config.name, md, dest)}"

    assert creative["object_story_spec"]["link_data"][
        "call_to_action"
    ].export_all_data() == {
        "type": "MESSAGE_PAGE",
        "value": {"app_destination": "MESSENGER"},
    }


def test_the_asset_feed_spec_carries_the_destination_array():
    dest = _multi_dest()
    creative, _, _, _ = _multi_creative(dest)

    afs = creative["asset_feed_spec"]
    assert afs["optimization_type"] == "DOF_MESSAGING_DESTINATION"
    assert afs["call_to_actions"] == [
        {
            "type": "MESSAGE_PAGE",
            "value": {
                "app_destination": "MESSENGER",
                "link": "https://fb.com/messenger_doc/",
            },
        },
        {
            "type": "WHATSAPP_MESSAGE",
            "value": {
                "app_destination": "WHATSAPP",
                "link": "https://api.whatsapp.com/send",
            },
        },
    ]


def test_a_template_that_already_has_an_asset_feed_spec_fails_loudly():
    """asset_feed_spec holds one optimization_type, so the two cannot both apply.

    Merging would silently drop either the destination array (the ad only ever
    opens Messenger) or the template's creative variants (respondents see
    something different). Neither is inferable from here.
    """
    dest = _multi_dest()
    template = {
        "object_story_spec": {"page_id": "page-123", "link_data": {"image_hash": "h"}},
        "asset_feed_spec": {"optimization_type": "DEGREES_OF_FREEDOM"},
    }

    with pytest.raises(Exception, match="already carries one"):
        _multi_creative(dest, template=template)


# --- both tokens round-trip to the same metadata ---------------------------


def test_both_tokens_round_trip_to_the_same_metadata_dict():
    """The two arms describe the same respondent in two grammars.

    Messenger's token is parsed the way fly's getMetadata does (split on ".",
    decode, pair up); WhatsApp's is first checked against fly's anchored entry
    pattern and then parsed the same way. Both must land on exactly the blob
    frozen into ad_attributions.metadata -- otherwise one ad describes two
    different people depending on which arm Meta happened to pick.
    """
    dest = _multi_dest()
    creative, study, stratum, config = _multi_creative(
        dest, metadata={"gender": "women", "Region": "South East"}
    )

    frozen = ref_metadata(config.name, creative_metadata(study, stratum, dest))

    message = _welcome(creative)["text_format"]["message"]
    messenger_token = json.loads(message["quick_replies"][0]["payload"])["referral"][
        "ref"
    ]
    whatsapp_token = message["autofill_message"]["content"]

    # Messenger: creative-led, order-free.
    assert messenger_token.startswith("creative.")
    assert _parse_ref(messenger_token) == frozen

    # WhatsApp: form-first, and it must actually pass fly's gate.
    assert whatsapp_token.startswith("form.")
    assert _fly_would_accept(whatsapp_token)
    assert _parse_ref(whatsapp_token) == frozen

    # ...and url_tags carries the Messenger one too.
    assert _parse_ref(creative["url_tags"].removeprefix("ref=")) == frozen


def test_the_two_grammars_stay_two():
    """multi's two arms carry DIFFERENT strings, and that is what matters.

    This used to assert that multi's Messenger token could not pass fly's
    WhatsApp gate -- true until replybot-v0.0.219, false on the deployed
    v0.0.221, which lets the `form` pair float (see
    `test_the_deployed_gate_no_longer_rejects_make_ref_output`).

    The property worth pinning was never really "one of them is rejected". It
    is that the two arms are two distinct strings built by two serialisers, so
    a row in `chatroach.messages` says which arm delivered it -- the whole
    reason the 2026-08-17 CTWA probe could tell Messenger delivery from
    WhatsApp delivery at all. Reusing one string across both arms would have
    made that unanswerable.
    """
    dest = _multi_dest()
    creative, _, _, _ = _multi_creative(dest)

    message = _welcome(creative)["text_format"]["message"]
    messenger_token = json.loads(message["quick_replies"][0]["payload"])["referral"][
        "ref"
    ]
    whatsapp_token = message["autofill_message"]["content"]

    assert messenger_token != whatsapp_token
    assert messenger_token.startswith("creative.")
    assert whatsapp_token.startswith("form.")


def test_an_encoded_multi_ad_carries_one_token_on_both_arms():
    """One mode drives both arms, so they cannot disagree about how much they
    disclose -- which matters here because the WhatsApp arm's token sits in the
    respondent's compose box, visible and editable."""
    dest = _multi_dest(ref_mode="encoded")
    creative, study, stratum, config = _multi_creative(dest)

    expected = encoded_ref("mnchweek", ad_ref_token(study, stratum, config, dest))
    message = _welcome(creative)["text_format"]["message"]

    assert message["autofill_message"]["content"] == expected
    assert (
        json.loads(message["quick_replies"][0]["payload"])["referral"]["ref"]
        == expected
    )
    assert creative["url_tags"] == f"ref={expected}"


# --- invariant 1: the frozen blob does not depend on the destination type ---


def test_the_frozen_blob_is_identical_across_destination_types():
    """INVARIANT. A multi destination and a Messenger destination with identical
    strata must freeze byte-identical ad_attributions.metadata.

    That blob is the only attribution a thin-ref study will ever have, and it is
    frozen at ad creation and never refreshed. If a destination type leaked into
    creative_metadata, the mapping rows would lose `creative`/`form`, every
    `location: "ad"` conf would resolve to nothing, every stratum would count
    zero, and the optimizer would reallocate on empty data -- silently and
    unrecoverably.

    Channel is decided by Meta at click time on a multi ad, so the blob could
    not depend on it even in principle: one ad, one ad id, one row.
    """
    creative = _creative("Smiling", "d")
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    messenger = _messenger_dest("d", "mnchweek")
    whatsapp = FlyWhatsAppDestination(
        type="whatsapp",
        name="d",
        initial_shortcode="mnchweek",
        welcome_message="Tap send to start",
        whatsapp_phone_number="+1-541-920-2635",
    )
    multi = _multi_dest(name="d")

    frozen = []
    for dest, dt in [
        (messenger, "MESSENGER"),
        (whatsapp, "WHATSAPP"),
        (multi, "MESSAGING_MESSENGER_WHATSAPP"),
    ]:
        study = _study([dest], [creative])
        frozen.append(
            ref_metadata(creative.name, creative_metadata(study, stratum, dest))
        )

    assert frozen[0] == frozen[1] == frozen[2]
    assert frozen[0]["form"] == "mnchweek"
    assert frozen[0]["creative"] == "Smiling"
    for key, value in PRODUCTION_METADATA.items():
        assert frozen[0][key] == value


def test_the_ref_mode_does_not_change_the_multi_blob_either():
    """The same guard as Messenger's, on the new type."""
    creative = _creative("Smiling", "multi")
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    blobs = []
    for mode in [None, "encoded"]:
        dest = _multi_dest(ref_mode=mode)
        study = _multi_study([dest], [creative])
        blobs.append(
            ref_metadata(creative.name, creative_metadata(study, stratum, dest))
        )

    assert blobs[0] == blobs[1]


def test_multi_ad_provenance_names_the_shortcode():
    dest = _multi_dest()
    creative = _creative("Smiling", "multi")
    study = _multi_study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"gender": "women"})

    prov = ad_provenance(study, "test-campaign-multi", [stratum])

    assert prov[("stratum-1", "Smiling")]["shortcode"] == "mnchweek"
    assert prov[("stratum-1", "Smiling")]["resolved_from"] == "ad_id"


# --- destination_type derivation -------------------------------------------


def test_each_destination_implies_its_own_destination_type():
    assert destination_type_for(_messenger_dest("m", "sc")) == "MESSENGER"
    assert destination_type_for(_whatsapp_dest()) == "WHATSAPP"
    assert destination_type_for(_multi_dest()) == "MESSAGING_MESSENGER_WHATSAPP"

    # Total: Web and App name their own Meta enum value too. They used to
    # return None and let the recruitment conf's stored string govern, which is
    # how `WEB` -- not a value Meta defines -- reached three production studies.
    assert destination_type_for(_web_dest("web")) == "WEBSITE"
    assert destination_type_for(_app_dest()) == "APP"


def _pair(destination, name="A"):
    return (
        CreativeConf(
            destination=destination.name, name=name, template=_template_with_page()
        ),
        destination,
    )


def test_derivation_returns_the_token_the_stratums_destinations_imply():
    assert (
        adset_destination_type([_pair(_messenger_dest("m", "sc"))])
        == "MESSENGER"
    )
    assert adset_destination_type([_pair(_whatsapp_dest())]) == "WHATSAPP"
    assert (
        adset_destination_type([_pair(_multi_dest())])
        == "MESSAGING_MESSENGER_WHATSAPP"
    )


def test_web_and_app_derive_their_own_type_with_nothing_to_fall_back_on():
    """There is no recruitment default any more, so there is nothing to fall
    back to. Web and App name their own token.

    The four studies this used to protect (`WEB` x3, `WEBSITE` x1, plus a
    `WEBSITE` sibling) all ended in 2024 and can never rebuild -- adopt only
    touches a study where start_date < now < end_date -- so the compatibility
    the fallback bought had no one left to buy it for.
    """
    assert adset_destination_type([_pair(_web_dest("web"))]) == "WEBSITE"
    assert adset_destination_type([_pair(_app_dest())]) == "APP"


def test_an_adset_with_no_pairs_raises_rather_than_guessing():
    """The one case the recruitment default silently covered.

    An ad set with no creative/destination pairs used to take the study-wide
    string; now it is what it is -- a stratum naming no creative, which cannot
    produce an ad.
    """
    with pytest.raises(Exception, match="no creative/destination pairs"):
        adset_destination_type([])


def test_several_creatives_agreeing_derive_one_type():
    dest = _messenger_dest("m", "sc")
    pairs = [_pair(dest, n) for n in ["A", "B", "C"]]
    assert adset_destination_type(pairs) == "MESSENGER"


def test_a_stratum_mixing_channels_raises_instead_of_picking_one():
    """destination_type is an ad-set field; one stratum is one ad set.

    Before derivation this could not even be detected: every ad set of every arm
    took the same study-wide string.
    """
    messenger = _messenger_dest("messenger", "sc")
    whatsapp = _whatsapp_dest()

    with pytest.raises(Exception, match="different ad set destination types"):
        adset_destination_type([_pair(messenger, "A"), _pair(whatsapp, "B")])


def test_a_stratum_mixing_multi_with_plain_messenger_raises():
    with pytest.raises(Exception, match="different ad set destination types"):
        adset_destination_type(
            [_pair(_messenger_dest("messenger", "sc"), "A"), _pair(_multi_dest(), "B")]
        )


def test_a_stratum_mixing_web_with_messenger_now_raises():
    """A behaviour change, and the reason it is the right one.

    This used to derive MESSENGER and build: Web implied nothing, so it could
    not disagree with anything. But one stratum is one ad set and destination_type
    is an ad-set field, so the Web creative's clicks were being served from an ad
    set Meta labels MESSENGER. That is the same class of silent misroute the old
    recruitment-level check existed to catch, reached from the other side.

    Now Web names WEBSITE, the disagreement is visible, and it raises.
    """
    with pytest.raises(Exception, match="different ad set destination types"):
        adset_destination_type(
            [_pair(_messenger_dest("messenger", "sc"), "A"), _pair(_web_dest("web"), "B")]
        )


def test_a_channel_experiment_gives_each_arm_its_own_destination_type():
    """The thing one study-wide field made impossible.

    Setting MESSAGING_MESSENGER_WHATSAPP to reach both arms made BOTH of them
    multi-destination, which destroys the experiment by handing channel
    assignment to Meta -- you cannot randomise what Meta assigns. Each arm now
    derives its own token from its own destinations.
    """
    messenger = _messenger_dest("Messenger arm", "sc_m")
    whatsapp = FlyWhatsAppDestination(
        type="whatsapp",
        name="WhatsApp arm",
        initial_shortcode="sc_w",
        welcome_message="Tap send",
        whatsapp_phone_number="+1-541-920-2635",
    )
    creatives = [
        CreativeConf(
            destination="Messenger arm", name="m0", template=_template_with_page()
        ),
        CreativeConf(
            destination="WhatsApp arm", name="w0", template=_template_with_page()
        ),
    ]
    study = _study([messenger, whatsapp], creatives)
    stratum = _stratum_with_md("stratum-1", creatives, {"gender": "women"})

    for arm, expected in [("Messenger arm", "MESSENGER"), ("WhatsApp arm", "WHATSAPP")]:
        pairs = pair_creatives_with_destinations(
            study, stratum, f"test-campaign-{arm}"
        )
        assert adset_destination_type(pairs) == expected


# --- invariant 2/3: existing studies are byte-identical --------------------


_UNCHANGING_ADSET_FIELDS = [
    "name",
    "status",
    "daily_budget",
    "campaign_id",
    "optimization_goal",
    "destination_type",
    "billing_event",
    "bid_strategy",
    "targeting",
]


def _adset_snapshot(data):
    """Everything but the two clock-dependent fields, which are asserted present."""
    assert "start_time" in data and "end_time" in data
    return {k: v for k, v in data.items() if k not in ("start_time", "end_time")}


def test_messenger_adset_instructions_are_byte_identical():
    """Asserted directly, not inferred. 110 production studies run through here.

    The whole ad set, not just destination_type: derivation moved the value that
    feeds AdsetConf, so the guard has to cover everything that dict produces.
    """
    data = _adset_for(
        _messenger_dest("messenger", "mnchweek"), _template_with_page(), "messenger"
    )

    assert _adset_snapshot(data) == {
        "name": "stratum-1",
        "status": "ACTIVE",
        "daily_budget": 1000,
        "campaign_id": "campaign-1",
        "optimization_goal": "CONVERSATIONS",
        "destination_type": "MESSENGER",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": {"targeting_automation": {"advantage_audience": 0}},
    }


def test_web_adset_instructions_are_byte_identical():
    """WEBSITE is kept verbatim: a Web destination implies nothing."""
    data = _adset_for(_web_dest("web"), _template_with_page(), "web")

    assert _adset_snapshot(data) == {
        "name": "stratum-1",
        "status": "ACTIVE",
        "daily_budget": 1000,
        "campaign_id": "campaign-1",
        "optimization_goal": "CONVERSATIONS",
        "destination_type": "WEBSITE",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": {"targeting_automation": {"advantage_audience": 0}},
    }


def test_app_adset_instructions_are_byte_identical():
    data = _adset_for(_app_dest("app"), _template_with_page(), "app")

    assert _adset_snapshot(data) == {
        "name": "stratum-1",
        "status": "ACTIVE",
        "daily_budget": 1000,
        "campaign_id": "campaign-1",
        "optimization_goal": "CONVERSATIONS",
        "destination_type": "APP",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": {"targeting_automation": {"advantage_audience": 0}},
        "promoted_object": {
            "application_id": "app-1",
            "object_store_url": "https://play.example/app",
        },
    }


def test_a_messenger_creative_gains_no_asset_feed_spec():
    """_create_creative learned an asset_feed_spec parameter. Nothing else may
    notice: asset_feed_spec is in field_contract.COMPARED_AD, so an extra key
    would rewrite every ad in all 124 Messenger studies on the next run."""
    template = _load_template("image_ad_messenger.json")
    dest = _messenger_dest("messenger", "mnchweek")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, dest)

    assert "asset_feed_spec" not in creative.export_all_data()


def test_a_template_asset_feed_spec_still_flows_through_untouched():
    """The pre-existing path, unchanged by the new parameter."""
    template = _load_template("image_ad_messenger.json")
    template["asset_feed_spec"] = {"optimization_type": "DEGREES_OF_FREEDOM"}
    dest = _messenger_dest("messenger", "mnchweek")
    config = CreativeConf(destination="messenger", name="Smiling", template=template)
    study = _study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    creative = create_creative(study, stratum, config, dest)
    afs = creative["asset_feed_spec"]

    assert afs["optimization_type"] == "DEGREES_OF_FREEDOM"
    assert "page_welcome_message" in afs["additional_data"]


def test_ad_names_are_still_the_creative_name():
    """Reconciliation matches ads by name and the ad id is the attribution key.

    A name change mints new ids and strands every existing ad_attributions row,
    making those studies' past respondents unattributable. So this holds for the
    new destination type as much as the old ones.
    """
    for dest, dt in [
        (_messenger_dest("d", "mnchweek"), "MESSENGER"),
        (_multi_dest(name="d"), "MESSAGING_MESSENGER_WHATSAPP"),
    ]:
        config = CreativeConf(
            destination="d", name="Smiling", template=_template_with_page()
        )
        study = _study([dest], [config])
        stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})
        state = _FakeCampaignState("test-campaign-d")

        _, ads = adset_instructions(study, state, stratum, 10.0)
        assert [a["name"] for a in ads] == ["Smiling"]


def test_a_multi_adset_gets_the_derived_type_and_the_promoted_object():
    data = _adset_for(_multi_dest(), _template_with_page(), "multi")

    assert data["destination_type"] == "MESSAGING_MESSENGER_WHATSAPP"
    assert data["promoted_object"] == {
        "page_id": "page-123",
        "whatsapp_phone_number": "15419202635",
    }


def test_a_stale_stored_destination_type_cannot_reach_the_adset():
    """The backward-compatibility guarantee, asserted end to end.

    ~940 production recruitment confs still carry a `destination_type`, some of
    them values Meta does not define (`WEB` on three studies, `MULTI` on one).
    Loading such a conf must ignore the field entirely rather than send it: the
    ad set is labelled by what its ads actually do.

    Two production studies paired a `WEB` recruitment conf with Messenger
    destinations (both ended in 2024). This is that shape. Note it cannot
    rewrite anything live either -- destination_type is absent from
    COMPARED_ADSET, so it rides only on ad-set creates.
    """
    destination = _messenger_dest("messenger", "mnchweek")
    config = CreativeConf(
        destination=destination.name, name="Smiling", template=_template_with_page()
    )

    stale = _study([destination], [config]).model_dump()
    stale["recruitment"]["destination_type"] = "WEB"
    study = StudyConf(**stale)

    stratum = _stratum_with_md("stratum-1", [config], {"gender": "women"})
    adset, _ = adset_instructions(
        study, _FakeCampaignState("test-campaign-messenger"), stratum, 10.0
    )

    assert adset.export_all_data()["destination_type"] == "MESSENGER"


def test_destination_type_and_promoted_object_ride_only_on_creates():
    """Asserted, not assumed. Two consequences depend on it.

    A running study can never change channel -- ad sets are matched by name and
    the name is the stratum id -- and, more urgently here, deriving the value
    cannot rewrite any existing ad set. If either field is ever added to
    COMPARED_ADSET, this test is where that decision gets made consciously.
    """
    assert "destination_type" not in COMPARED_ADSET
    assert "promoted_object" not in COMPARED_ADSET


# --- the encoded ref, end to end -------------------------------------------
#
# The producer half of the format fly already decodes. What these pin is not the
# encoding itself (test_ref_encoding.py owns that, against golden bytes) but the
# wiring: that every carrier on a creative gets the same token, that the frozen
# blob is untouched by the mode, and that the ad_attributions row carries the
# token the ad actually ships.


def _decoded(ref):
    """The (form, token) fly would recover from a ref this ad ships."""
    assert ref.startswith("r."), ref
    return decode_recruitment_ref(ref[2:])


def _encoded_messenger_ad(metadata=None, shortcode="mnchweek"):
    """A real messenger creative under ref_mode="encoded"."""
    dest = _messenger_dest("messenger", shortcode, ref_mode="encoded")
    config = CreativeConf(
        destination=dest.name,
        name="Smiling",
        template=_load_template("image_ad_messenger.json"),
    )
    study = _study([dest], [config])
    stratum = _stratum_with_md(
        "stratum-1", [config], PRODUCTION_METADATA if metadata is None else metadata
    )
    return create_creative(study, stratum, config, dest), study, stratum, config, dest


def test_an_encoded_messenger_ad_ships_the_same_token_on_both_carriers():
    """Messenger has two carriers and a respondent can arrive by either.

    Different tokens on the two would mean one ad describing two different
    people depending on how they tapped it -- the same reasoning that makes the
    dotted ref identical on both.
    """
    ad, _, _, _, _ = _encoded_messenger_ad({"gender": "women"})

    from_url_tags = ad["url_tags"].removeprefix("ref=")
    from_payload = _welcome_payload_ref(ad)

    assert from_url_tags == from_payload
    assert _decoded(from_url_tags).form == "mnchweek"


def test_an_encoded_ref_carries_the_shortcode_and_nothing_of_the_stratum():
    """The point of the format: routes without disclosing the vocabulary."""
    ad, _, _, _, _ = _encoded_messenger_ad()
    ref = ad["url_tags"].removeprefix("ref=")

    assert _decoded(ref).form == "mnchweek"

    for value in PRODUCTION_METADATA.values():
        assert value not in ref
    assert "Smiling" not in ref


def test_an_encoded_whatsapp_autofill_is_accepted_by_flys_entry_gate():
    """Against fly's second anchor, since `form.` cannot match an opaque ref."""
    dest = _whatsapp_dest(ref_mode="encoded")
    config = CreativeConf(
        destination=dest.name,
        name="Smiling",
        template=_load_template("image_ad_messenger.json"),
    )
    study = _whatsapp_study([dest], [config])
    stratum = _stratum_with_md("stratum-1", [config], PRODUCTION_METADATA)

    ad = create_creative(study, stratum, config, dest)
    welcome = json.loads(ad["object_story_spec"]["link_data"]["page_welcome_message"])
    autofill = welcome["text_format"]["message"]["autofill_message"]["content"]

    assert WHATSAPP_ENTRY_REF_ENCODED.match(autofill), autofill
    assert _decoded(autofill).form == "mnchweek"


def test_a_multi_ads_two_arms_carry_one_token():
    """One ad, one mapping row, so one token -- in all three carriers.

    A multi ad's arms are two grammars over the same facts. If they minted
    different tokens the ad would have two attribution identities and whichever
    arm Meta chose would decide which one a respondent got.
    """
    dest = _multi_dest(ref_mode="encoded")
    ad, _, _, _ = _multi_creative(dest)

    welcome = json.loads(ad["object_story_spec"]["link_data"]["page_welcome_message"])
    autofill = welcome["text_format"]["message"]["autofill_message"]["content"]
    payload = json.loads(
        welcome["text_format"]["message"]["quick_replies"][0]["payload"]
    )["referral"]["ref"]
    url_tags = ad["url_tags"].removeprefix("ref=")

    assert _decoded(autofill) == _decoded(payload) == _decoded(url_tags)


def test_the_encoded_mode_does_not_change_what_gets_frozen():
    """The core invariant, extended to the third mode.

    `creative_metadata` must stay mode-blind. If "encoded" leaked into it, the
    frozen blob would hold nothing but `form`, every `location: "ad"` conf would
    resolve to nothing, every stratum would count zero, and the optimizer would
    reallocate on empty data -- unrecoverably, since the blob is never refreshed.
    """
    full = _messenger_dest("messenger", "mnchweek")
    enc = _messenger_dest("messenger", "mnchweek", ref_mode="encoded")

    creative = _creative("Smiling", "messenger")
    stratum = _stratum_with_md("stratum-1", [creative], PRODUCTION_METADATA)

    frozen_full = ref_metadata(
        creative.name, creative_metadata(_study([full], [creative]), stratum, full)
    )
    frozen_enc = ref_metadata(
        creative.name, creative_metadata(_study([enc], [creative]), stratum, enc)
    )

    assert frozen_full == frozen_enc
    assert "creative" in frozen_enc and "form" in frozen_enc


def test_provenance_carries_the_token_the_ad_actually_ships():
    """The join has to work: the row's token must equal the ref's token.

    If these drifted, every respondent from the ad would arrive with a token
    that matches no row and be counted unmapped -- for the whole study, silently
    until someone read the counters.
    """
    ad, study, stratum, _, _ = _encoded_messenger_ad()

    prov = ad_provenance(study, "test-campaign-messenger", [stratum])

    shipped = _decoded(ad["url_tags"].removeprefix("ref=")).token

    assert prov[("stratum-1", "Smiling")]["ref_token"] == shipped


def test_the_token_is_stable_across_runs():
    """Reconciliation compares creatives, and the ref is part of one.

    A token that changed between runs would make every run rewrite every ad in
    the study, forever, while spending money.
    """
    first, study, stratum, config, dest = _encoded_messenger_ad()
    second = create_creative(study, stratum, config, dest)

    assert first["url_tags"] == second["url_tags"]


def test_distinct_strata_and_creatives_get_distinct_tokens():
    """Otherwise the join is meaningless: the token IS the identity."""
    dest = _messenger_dest("messenger", "mnchweek", ref_mode="encoded")
    a = _creative("Smiling", "messenger")
    b = _creative("Frowning", "messenger")
    study = _study([dest], [a, b])

    strata = [
        _stratum_with_md("stratum-1", [a, b], {"gender": "women"}),
        _stratum_with_md("stratum-2", [a, b], {"gender": "men"}),
    ]

    prov = ad_provenance(study, "test-campaign-messenger", strata)
    tokens = [row["ref_token"] for row in prov.values()]

    assert len(tokens) == 4
    assert len(set(tokens)) == 4


def test_a_token_collision_refuses_to_generate_instructions():
    """The last cheap moment. Past here the ads exist and are spending."""
    with pytest.raises(InvalidConfigError, match="collision"):
        assert_ref_tokens_unique(
            {
                ("stratum-1", "Smiling"): {"ref_token": "aaaaaaaaaa"},
                ("stratum-2", "Frowning"): {"ref_token": "aaaaaaaaaa"},
            }
        )


def test_rows_without_tokens_are_not_treated_as_colliding():
    """None is the normal case for every mode but "encoded"."""
    assert_ref_tokens_unique(
        {
            ("stratum-1", "Smiling"): {"ref_token": None},
            ("stratum-2", "Frowning"): {"ref_token": None},
        }
    )
