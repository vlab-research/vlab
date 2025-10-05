import json
import random
from datetime import datetime
from typing import TypeVar

import pytest
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience

from .facebook.update import Instruction
from .facebook.state import CampaignState, FacebookState, StateInitializationError
from .marketing import (
    _create_creative,
    adset_instructions,
    build_leadgen_form_params,
    check_and_create_forms,
    create_creative,
    make_leadgen_form_base_name,
    make_leadgen_form_name,
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
    GeneralConf,
    InvalidConfigError,
    LeadGenDestination,
    Lookalike,
    LookalikeAudience,
    LookalikeSpec,
    Partitioning,
    SimpleRecruitment,
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



#############################
# Lead Gen Tests
#############################


def test_make_leadgen_form_base_name():
    base = make_leadgen_form_base_name("study123", "dest1", "stratum1")
    assert base == "study123-dest1-stratum1"


def test_make_leadgen_form_name():
    name = make_leadgen_form_name("study123-dest1-stratum1", 1)
    assert name == "study123-dest1-stratum1-v1"

    name = make_leadgen_form_name("study123-dest1-stratum1", 42)
    assert name == "study123-dest1-stratum1-v42"


def test_build_leadgen_form_params():
    from .study_conf import SimpleRecruitment, UserInfo
    from datetime import datetime

    destination = LeadGenDestination(
        type="lead_gen",
        name="test-dest",
        page_id="123456",
        form_template={
            "questions": [{"key": "email", "label": "Email"}],
            "context_card": {"content": []},
        }
    )

    stratum = Stratum(
        id="stratum1",
        quota=0.5,
        creatives=[],
        facebook_targeting={},
        metadata={"gender": "female", "age": "18-24"},
    )

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
            extra_metadata={"campaign_type": "test"},
        ),
        destinations=[destination],
        audiences=[],
        creatives=[],
        strata=[],
        recruitment=SimpleRecruitment(
            ad_campaign_name="test",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="LINK_CLICKS",
            destination_type="WEBSITE",
            min_budget=100,
            budget=1000,
            max_sample=100,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        ),
    )

    params = build_leadgen_form_params(destination, stratum, study)

    # Should include template content
    assert params["questions"] == [{"key": "email", "label": "Email"}]

    # Should include tracking parameters with all metadata
    tracking = {item["key"]: item["value"] for item in params["tracking_parameters"]}
    assert tracking["stratum_id"] == "stratum1"
    assert tracking["study_id"] == "study123"
    assert tracking["gender"] == "female"
    assert tracking["age"] == "18-24"
    assert tracking["campaign_type"] == "test"


def test_build_leadgen_form_params_with_thank_you_url():
    from .study_conf import SimpleRecruitment, UserInfo
    from datetime import datetime

    destination = LeadGenDestination(
        type="lead_gen",
        name="test-dest",
        page_id="123456",
        form_template={
            "questions": [{"key": "email"}],
        },
        thank_you_url_template="https://example.com/thanks"
    )

    stratum = Stratum(
        id="stratum1",
        quota=0.5,
        creatives=[],
        facebook_targeting={},
        metadata={},
    )

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        destinations=[destination],
        audiences=[],
        creatives=[],
        strata=[],
        recruitment=SimpleRecruitment(
            ad_campaign_name="test",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="LINK_CLICKS",
            destination_type="WEBSITE",
            min_budget=100,
            budget=1000,
            max_sample=100,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        ),
    )

    params = build_leadgen_form_params(destination, stratum, study)

    assert params["thank_you_page"]["url"] == "https://example.com/thanks"


def test_check_and_create_forms_with_multiple_strata():
    """Test check_and_create_forms() with multiple strata on same page"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={"name": "Test Creative"}
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum1 = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    stratum2 = Stratum(
        id="stratum2",
        quota=200,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["CA"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock FacebookState
    state = MagicMock(spec=FacebookState)
    state.page_forms.return_value = []  # No existing forms

    instructions = check_and_create_forms(study, state, [stratum1, stratum2])

    # Should create 2 forms (one per stratum)
    assert len(instructions) == 2
    assert all(i.action == "create" for i in instructions)
    assert all(i.node == "leadgen_form" for i in instructions)

    # Verify form names
    form_names = [i.params["name"] for i in instructions]
    assert "study123-dest1-stratum1-v1" in form_names
    assert "study123-dest1-stratum2-v1" in form_names


def test_check_and_create_forms_skips_non_leadgen_destinations():
    """Test check_and_create_forms() skips non-LeadGen destinations"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            WebDestination(
                name="web_dest",
                type="WEB",
                url_template="https://example.com?ref={ref}"
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="web_dest",
                template_campaign="template_campaign",
                template={"name": "Test Creative"}
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    state = MagicMock(spec=FacebookState)

    instructions = check_and_create_forms(study, state, [stratum])

    # Should not create any forms
    assert len(instructions) == 0


def test_check_and_create_forms_groups_by_page_id():
    """Test check_and_create_forms() groups forms by page_id"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form 1", "questions": []},
            ),
            LeadGenDestination(
                name="dest2",
                type="LEAD_GEN",
                page_id="page456",
                form_template={"name": "Test Form 2", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={"name": "Test Creative 1"}
            ),
            CreativeConf(
                name="creative2",
                destination="dest2",
                template_campaign="template_campaign",
                template={"name": "Test Creative 2"}
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum1 = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    stratum2 = Stratum(
        id="stratum2",
        quota=200,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["CA"]}},
        creatives=[study.creatives[1]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock FacebookState
    state = MagicMock(spec=FacebookState)
    state.page_forms.return_value = []  # No existing forms

    instructions = check_and_create_forms(study, state, [stratum1, stratum2])

    # Should be called once per page_id
    assert state.page_forms.call_count == 2
    state.page_forms.assert_any_call("page123")
    state.page_forms.assert_any_call("page456")


def test_create_creative_raises_when_leadgen_form_not_found():
    """Test create_creative() raises StateInitializationError when form doesn't exist"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={"name": "Test Creative"}
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock CampaignState with no forms
    fb_state = MagicMock(spec=FacebookState)
    fb_state.page_forms.return_value = []  # No forms exist

    campaign_state = MagicMock(spec=CampaignState)
    campaign_state.facebook_state = fb_state
    campaign_state.campaign_name = "test_campaign"

    config = study.creatives[0]
    destination = study.destinations[0]

    with pytest.raises(StateInitializationError) as exc_info:
        create_creative(study, stratum, config, destination, campaign_state)

    assert "Lead gen form not found for study123-dest1-stratum1" in str(exc_info.value)


def test_create_creative_uses_latest_form_version():
    """Test create_creative() uses the latest version of the form"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={
                    "name": "Test Creative",
                    "object_story_spec": {
                        "page_id": "page123",
                        "link_data": {
                            "message": "Test message",
                            "image_hash": "abc123"
                        }
                    }
                }
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock CampaignState with multiple form versions
    fb_state = MagicMock(spec=FacebookState)
    fb_state.page_forms.return_value = [
        {"id": "form1", "name": "study123-dest1-stratum1-v1", "status": "ACTIVE"},
        {"id": "form2", "name": "study123-dest1-stratum1-v2", "status": "ACTIVE"},
        {"id": "form3", "name": "study123-dest1-stratum1-v3", "status": "ACTIVE"},
    ]

    campaign_state = MagicMock(spec=CampaignState)
    campaign_state.facebook_state = fb_state
    campaign_state.campaign_name = "test_campaign"

    config = study.creatives[0]
    destination = study.destinations[0]

    creative = create_creative(study, stratum, config, destination, campaign_state)

    # Should use v3 (latest version)
    assert creative["object_story_spec"]["link_data"]["call_to_action"]["value"]["lead_gen_form_id"] == "form3"


def test_create_creative_modifies_asset_feed_spec_for_leadgen():
    """Test _create_creative() properly sets lead_gen_form_id in asset_feed_spec"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={
                    "name": "Test Creative",
                    "object_story_spec": {
                        "page_id": "page123"
                    },
                    "asset_feed_spec": {
                        "images": [{"hash": "abc123"}],
                        "bodies": [{"text": "Test body"}],
                        "titles": [{"text": "Test title"}],
                        "link_urls": [{"website_url": "https://example.com"}]
                    }
                }
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock CampaignState with a form
    fb_state = MagicMock(spec=FacebookState)
    fb_state.page_forms.return_value = [
        {"id": "form123", "name": "study123-dest1-stratum1-v1", "status": "ACTIVE"},
    ]

    campaign_state = MagicMock(spec=CampaignState)
    campaign_state.facebook_state = fb_state
    campaign_state.campaign_name = "test_campaign"

    config = study.creatives[0]
    destination = study.destinations[0]

    creative = create_creative(study, stratum, config, destination, campaign_state)

    # Verify asset_feed_spec has call_to_actions with lead_gen_form_id
    assert "asset_feed_spec" in creative
    assert "call_to_actions" in creative["asset_feed_spec"]
    assert creative["asset_feed_spec"]["call_to_actions"][0]["type"] == "LEAD_GEN"
    assert creative["asset_feed_spec"]["call_to_actions"][0]["value"]["lead_gen_form_id"] == "form123"


def test_create_creative_modifies_video_data_for_leadgen():
    """Test _create_creative() properly sets lead_gen_form_id in video_data"""
    from unittest.mock import MagicMock

    study = StudyConf(
        id="study123",
        user=UserInfo(survey_user="test", token="test"),
        general=GeneralConf(
            name="Test Study",
            credentials_key="test",
            credentials_entity="test",
            ad_account="123",
            opt_window=7,
        ),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test_campaign",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            destination_type="LEAD_GEN",
            min_budget=10.0,
            budget=100.0,
            max_sample=1000,
        ),
        destinations=[
            LeadGenDestination(
                name="dest1",
                type="LEAD_GEN",
                page_id="page123",
                form_template={"name": "Test Form", "questions": []},
            )
        ],
        creatives=[
            CreativeConf(
                name="creative1",
                destination="dest1",
                template_campaign="template_campaign",
                template={
                    "name": "Test Creative",
                    "object_story_spec": {
                        "page_id": "page123",
                        "video_data": {
                            "video_id": "video123",
                            "message": "Test message"
                        }
                    }
                }
            )
        ],
        audiences=[],
        strata=[],
    )

    stratum = Stratum(
        id="stratum1",
        quota=100,
        metadata={"campaign_name": "test_campaign"},
        facebook_targeting={"geo_locations": {"countries": ["US"]}},
        creatives=[study.creatives[0]],
        audiences=[],
        excluded_audiences=[]
    )

    # Mock CampaignState with a form
    fb_state = MagicMock(spec=FacebookState)
    fb_state.page_forms.return_value = [
        {"id": "form123", "name": "study123-dest1-stratum1-v1", "status": "ACTIVE"},
    ]

    campaign_state = MagicMock(spec=CampaignState)
    campaign_state.facebook_state = fb_state
    campaign_state.campaign_name = "test_campaign"

    config = study.creatives[0]
    destination = study.destinations[0]

    creative = create_creative(study, stratum, config, destination, campaign_state)

    # Verify video_data has call_to_action with lead_gen_form_id
    assert "object_story_spec" in creative
    assert "video_data" in creative["object_story_spec"]
    assert creative["object_story_spec"]["video_data"]["call_to_action"]["type"] == "LEAD_GEN"
    assert creative["object_story_spec"]["video_data"]["call_to_action"]["value"]["lead_gen_form_id"] == "form123"

