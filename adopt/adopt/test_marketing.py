import json
import random
from datetime import datetime
from typing import TypeVar
from unittest.mock import patch
from urllib.parse import unquote

import pytest
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience

from .facebook.update import Instruction
from .marketing import (
    _create_creative,
    ad_provenance,
    adset_instructions,
    create_creative,
    creative_metadata,
    destination_shortcode,
    make_ref,
    manage_aud,
    messenger_call_to_action,
    pair_creatives_with_destinations,
    ref_metadata,
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
    WebDestination,
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


def _web_dest(name, url_template="https://survey.example/?r={ref}"):
    return WebDestination(type="web", name=name, url_template=url_template)


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
            destination_type="MESSENGER",
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


def test_frozen_metadata_survives_a_dotted_value_that_the_ref_mangles():
    """Documents a real limit of the ref, and why the blob is strictly better.

    make_ref does not escape "." (quote() treats it as always-safe), so a
    metadata value containing a dot splits into extra tokens and the ref
    parses back to garbage. The frozen blob has no such grammar and keeps the
    value intact -- so for these studies the ad-ID path is *more* accurate
    than what it replaces, not merely equal. Asserted rather than fixed:
    changing make_ref would rewrite the creative of every live ad.
    """
    dest = _web_dest("web")
    creative = _creative("Smiling", "web")
    study = _study([dest], [creative])
    stratum = _stratum_with_md("stratum-1", [creative], {"city": "St. Louis"})

    md = creative_metadata(study, stratum, dest)
    frozen = ref_metadata(creative.name, md)

    assert frozen["city"] == "St. Louis"
    assert _parse_ref(make_ref(creative.name, md)) != frozen


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
