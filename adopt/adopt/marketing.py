import json
import random
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from typing import (Any, Dict, List, NamedTuple, Optional, Sequence, Tuple,
                    Union)
from urllib.parse import quote

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
from facebook_business.adobjects.adcreativeobjectstoryspec import \
    AdCreativeObjectStorySpec
from facebook_business.adobjects.adpromotedobject import AdPromotedObject
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting

from .facebook.reconciliation import adset_dif
from .facebook.state import CampaignState, split
from .facebook.update import Instruction

ADSET_HOURS = 48

Params = Dict[str, Any]


class TargetingConf(NamedTuple):
    template_campaign_name: Optional[str]
    distribution_vars: list[str]
    country_code: str
    respondent_audience_name: str


class UserInfo(NamedTuple):
    survey_user: str
    token: str


# add max_budget - for max daily budget
# make budget optional - only for proportional


class TargetVar(NamedTuple):
    type: str
    value: Union[str, int, float]


class QuestionTargeting(NamedTuple):
    op: str
    vars: List[Union[TargetVar, "QuestionTargeting"]]  # type: ignore


class FlyMessengerDestination(NamedTuple):
    initial_shortcode: str
    survey_shortcodes: list[str]
    finished_question_ref: str


class AppDestination(NamedTuple):
    facebook_app_id: str
    app_install_link: str
    deeplink_template: str


DestinationConf = Union[FlyMessengerDestination, AppDestination]

FacebookTargeting = Dict[str, Any]


class CampaignConf(NamedTuple):
    optimization_goal: str
    destination_type: str
    page_id: str
    instagram_id: Optional[str]
    budget: float
    min_budget: float
    opt_window: int
    start_date: datetime
    end_date: datetime
    proportional: bool
    ad_account: str
    ad_campaign_name: str
    extra_metadata: dict[str, str]


class CreativeConf(NamedTuple):
    name: str
    image_hash: str
    body: str
    link_text: str
    welcome_message: Optional[str] = None  # messenger only
    button_text: Optional[str] = None  # messenger only


class StratumConf(NamedTuple):
    id: str
    quota: Union[int, float]
    creatives: List[str]
    audiences: List[str]
    excluded_audiences: List[str]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: Dict[str, str]


# OLD
# {
#     "name": f"vlab-vacc-{COUNTRY_CODE}-vacc-A+B",
#     "subtype": "LOOKALIKE",
#     "lookalike": {
#         "name": f"vlab-vacc-{COUNTRY_CODE}-vacc-A+B-lookalike",
#         "target": 1100,
#         "spec": {
#             "country": COUNTRY_CODE,
#             "starting_ratio": 0.0,
#             "ratio": 0.2
#         }
#     },


# NEW
# {
#     "name": f"vlab-vacc-{COUNTRY_CODE}-",
#     "subtype": "LOOKALIKE",
#     "lookalike": {
#         "target": 1100,
#         "spec": {
#             "country": COUNTRY_CODE,
#             "starting_ratio": 0.0,
#             "ratio": 0.2
#         }
#     },

# {
#     "name": f"vlab-vacc-{COUNTRY_CODE}-respondents",
#     "subtype": "PARTITIONED",
#     "partitioning": {
#     },


class InvalidConfigError(BaseException):
    pass


# scenario: I want to split every N users.
# usage: set min_users only
#
# scenario: I want to split when I've BOTH past X days,
# and have at least N users.
# usage: set min_users, min_days
#
# scenario: I want to split if I've either passed X days
# or past N users
# usage: set max_users, max_days, and min_users
@dataclass(frozen=True)
class Partitioning:
    min_users: int
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    max_users: Optional[int] = None

    @property
    def scenario(self):
        return {f.name for f in fields(self) if getattr(self, f.name)}

    def __post_init__(self):
        valid_scenarios = [
            {"min_users"},
            {"min_users", "min_days"},
            {"min_users", "max_users", "max_days"},
        ]

        if self.scenario not in valid_scenarios:
            raise InvalidConfigError(
                f"Invalid partitioning config. The following fields "
                f"were all set: {self.scenario}. Please see documentation for "
                f"valid combinations."
            )


def validate(cls, subtype, subtype_confs):
    if subtype not in subtype_confs:
        raise InvalidConfigError(
            f"Invalid subtype: {subtype}. " f"We support: {list(subtype_confs.keys())}"
        )

    conf = subtype_confs[subtype]
    if conf:
        attr, type_ = conf
        val = getattr(cls, attr)
        if not isinstance(val, type_):
            raise InvalidConfigError(
                f"Invalid config. Subtype {subtype} "
                f"requires a {type_} value for {attr}"
            )


@dataclass(frozen=True)
class SimpleRandomizationConf:
    arms: int


@dataclass(frozen=True)
class RandomizationConf:
    name: str
    strategy: str
    config: Union[SimpleRandomizationConf]

    def __post_init__(self):
        subtype_confs = {
            "SIMPLE": ("config", SimpleRandomizationConf),
        }
        validate(self, self.subtype, subtype_confs)


class LookalikeSpec(NamedTuple):
    country: str
    ratio: float
    starting_ratio: float


class Lookalike(NamedTuple):
    target: int
    spec: LookalikeSpec


@dataclass(frozen=True)
class AudienceConf:
    name: str
    subtype: str
    question_targeting: Optional[QuestionTargeting] = None
    lookalike: Optional[Lookalike] = None
    partitioning: Optional[Partitioning] = None

    def __post_init__(self):
        subtype_confs = {
            "CUSTOM": None,
            "LOOKALIKE": ("lookalike", Lookalike),
            "PARTITIONED": ("partitioning", Partitioning),
        }
        validate(self, self.subtype, subtype_confs)


class Audience(NamedTuple):
    name: str
    pageid: str
    users: List[str]


class LookalikeAudience(NamedTuple):
    name: str
    spec: LookalikeSpec
    origin_audience: Audience


AnyAudience = Union[Audience, LookalikeAudience]


class CreativeGroup(NamedTuple):
    name: str
    creatives: List[CreativeConf]


Metadata = Dict[str, str]


class Stratum(NamedTuple):
    id: str
    quota: Union[int, float]
    creatives: List[CreativeConf]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: Metadata


class Location(NamedTuple):
    lat: float
    lng: float
    rad: float


class AdsetConf(NamedTuple):
    campaign: Campaign
    stratum: Stratum
    budget: float
    status: str
    instagram_id: Optional[str]
    hours: int
    optimization_goal: str
    destination_type: str
    promoted_object: Optional[dict[str, str]]


def dict_from_nested_type(d):
    """Handles both Facebook SDK's types and Named Tuples"""
    if hasattr(d, "export_data"):
        d = d.export_data()

    if hasattr(d, "_asdict"):
        d = d._asdict()

    if isinstance(d, dict):
        for k, v in d.items():
            d[k] = dict_from_nested_type(v)
        return d

    if isinstance(d, list):
        return [dict_from_nested_type(v) for v in d]

    return d


def validate_targeting(targeting):
    valid_targets = set(dir(Targeting.Field))
    for k, _ in targeting.items():
        if k not in valid_targets:
            raise Exception(f"Targeting config invalid, key: {k} does not exist!")


def create_adset(c: AdsetConf) -> AdSet:
    name = c.stratum.id
    targeting = {**c.stratum.facebook_targeting}

    # TODO: document this funkyness - pretends it's runnign at midnight...
    midnight = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=0)

    adset = AdSet()
    adset[AdSet.Field.end_time] = midnight + timedelta(hours=c.hours)
    adset[AdSet.Field.targeting] = targeting
    adset[AdSet.Field.status] = c.status
    adset[AdSet.Field.daily_budget] = c.budget
    adset[AdSet.Field.name] = name
    adset[AdSet.Field.start_time] = datetime.utcnow() + timedelta(minutes=5)
    adset[AdSet.Field.campaign_id] = c.campaign["id"]
    adset[AdSet.Field.optimization_goal] = c.optimization_goal
    adset[AdSet.Field.destination_type] = c.destination_type
    adset[AdSet.Field.billing_event] = AdSet.BillingEvent.impressions
    adset[AdSet.Field.bid_strategy] = AdSet.BidStrategy.lowest_cost_without_cap

    # hack to support app install ads...
    if c.promoted_object:
        adset[AdSet.Field.promoted_object] = c.promoted_object

    return adset


def make_welcome_message(text, button_text, ref):
    payload = json.dumps({"referral": {"ref": ref}})

    message = {
        "message": {
            "text": text,
            "quick_replies": [
                {"content_type": "text", "title": button_text, "payload": payload}
            ],
        }
    }

    return json.dumps(message, sort_keys=True)


def create_ad(adset: AdSet, creative: AdCreative, status: str) -> Ad:
    a = Ad()
    a[Ad.Field.name] = creative["name"]
    a[Ad.Field.status] = status
    a[Ad.Field.adset_id] = adset["id"]
    a[Ad.Field.creative] = creative
    return a


def manage_basic_aud(
    old_auds: List[CustomAudience], aud: Audience
) -> List[Instruction]:
    existing = {a["name"]: a for a in old_auds}
    ca = existing.get(aud.name)

    if ca is None:
        return [create_custom_audience(aud.name, "virtual lab auto-generated audience")]

    return add_users_to_audience(aud.pageid, ca.get_id(), aud.users)


def manage_lookalike_aud(
    old_auds: List[CustomAudience], aud: LookalikeAudience
) -> List[Instruction]:
    existing = {a["name"]: a for a in old_auds}
    origin = existing.get(aud.origin_audience.name)

    if aud.name not in existing and origin:
        return [create_lookalike_audience(aud.name, aud.spec._asdict(), origin)]

    return []


def manage_aud(
    old_auds: List[CustomAudience], aud: Union[Audience, LookalikeAudience]
) -> List[Instruction]:

    if isinstance(aud, Audience):
        return manage_basic_aud(old_auds, aud)

    if isinstance(aud, LookalikeAudience):
        return manage_lookalike_aud(old_auds, aud)


def manage_audiences(
    state, new_auds: List[Union[Audience, LookalikeAudience]]
) -> List[Instruction]:

    return [i for aud in new_auds for i in manage_aud(state.custom_audiences, aud)]


def create_lookalike_audience(
    name: str, spec: Dict[str, Any], source: CustomAudience
) -> Instruction:

    params = {
        CustomAudience.Field.name: name,
        CustomAudience.Field.subtype: CustomAudience.Subtype.lookalike,
        CustomAudience.Field.origin_audience_id: source.get_id(),
        CustomAudience.Field.lookalike_spec: json.dumps(spec),
    }

    return Instruction("custom_audience", "create", params, None)


def create_custom_audience(name: str, desc: str) -> Instruction:

    params = {
        CustomAudience.Field.name: name,
        CustomAudience.Field.subtype: "CUSTOM",
        CustomAudience.Field.description: desc,
        CustomAudience.Field.customer_file_source: "USER_PROVIDED_ONLY",
    }

    return Instruction("custom_audience", "create", params, None)


def add_users_to_audience(
    pageid: str, aud_id: str, users: List[str]
) -> List[Instruction]:

    params: Dict[str, Any] = {
        "schema": ["PAGEUID"],
        "is_raw": True,
        "page_ids": [pageid],
    }

    session_id = random.randint(1, 1_000_000)
    chunks = [(i + 1, chunk) for i, chunk in enumerate(split(users, 10_000))]
    batches = len(chunks)

    return [
        Instruction(
            "custom_audience",
            "add_users",
            {
                "payload": {**params, "data": [[u] for u in chunk]},
                "session": {
                    "session_id": session_id,
                    "batch_seq": i,
                    "last_batch_flag": i == batches,
                    "estimated_num_total": len(users),
                },
            },
            aud_id,
        )
        for i, chunk in chunks
    ]


def make_ref(creative_name: str, metadata: Metadata) -> str:
    s = f"creative.{creative_name}"
    for k, v in metadata.items():
        s += f".{k}.{quote(v)}"
    return s


def messenger_call_to_action():
    {
        "type": "MESSAGE_PAGE",
        "value": {"app_destination": "MESSENGER"},
    }


def app_download_call_to_action(deeplink):
    return {
        "type": "INSTALL_MOBILE_APP",
        "value": {"app_link": deeplink},
    }


def create_creative(
    config: CreativeConf,
    page_id: str,
    call_to_action: dict[str, Any],
    insta_id: Optional[str],
    page_welcome_message: Optional[str] = None,
    url_tags: Optional[str] = None,
    link: Optional[str] = None,
) -> AdCreative:

    c = AdCreative()

    link_data = {
        AdCreativeLinkData.Field.call_to_action: call_to_action,
        AdCreativeLinkData.Field.image_hash: config.image_hash,
        AdCreativeLinkData.Field.message: config.body,
        AdCreativeLinkData.Field.name: config.link_text,
    }

    if page_welcome_message:
        link_data[AdCreativeLinkData.Field.page_welcome_message] = page_welcome_message

    if link:
        link_data[AdCreativeLinkData.Field.link] = link

    if insta_id:
        c[AdCreative.Field.instagram_actor_id] = insta_id

    if url_tags:
        c[AdCreative.Field.url_tags] = url_tags

    c[AdCreative.Field.name] = config.name
    c[AdCreative.Field.actor_id] = page_id
    c[AdCreative.Field.object_story_spec] = {
        AdCreativeObjectStorySpec.Field.link_data: link_data,
        AdCreativeObjectStorySpec.Field.page_id: page_id,
    }

    return c


class Marketing:
    def __init__(
        self, state: CampaignState, config: CampaignConf, destination: DestinationConf
    ):
        cnf: Dict[str, Any] = {
            "PAGE_ID": config.page_id,
            "INSTA_ID": config.instagram_id,
            "OPTIMIZATION_GOAL": config.optimization_goal,
            "DESTINATION_TYPE": config.destination_type,
            "ADSET_HOURS": ADSET_HOURS,
            "EXTRA_METADATA": config.extra_metadata,
        }

        self.destination = destination
        self.state = state
        self.cnf = cnf

    # TODO: in order to accomodate multiple campaigns, this should be split
    # into two parts: A) generates the "format" from the configs (this should be
    # either persisted or exposed via API) and then B) uses that format to
    # create a set of instructions which can then be diffed with the
    # facebook_ad_state reconciler.
    def update_instructions(
        self, strata: List[Stratum], budget: Dict[str, float]
    ) -> Sequence[Instruction]:

        sb = [(s, budget[s.id]) for s in strata]
        new_state = [self.adset_instructions(s, b) for s, b in sb if b > 0]

        return adset_dif(self.state.campaign_state, new_state)

    def adset_instructions(
        self, stratum: Stratum, budget: float
    ) -> Tuple[AdSet, List[Ad]]:

        creatives = [self.create_creative(stratum, c) for c in stratum.creatives]

        if isinstance(self.destination, AppDestination):
            d = self.destination
            promoted_object = {
                AdPromotedObject.Field.application_id: d.facebook_app_id,
                AdPromotedObject.Field.object_store_url: d.app_install_link,
            }
        else:
            promoted_object = None

        ac = AdsetConf(
            self.state.campaign,
            stratum,
            budget,
            "ACTIVE",
            self.cnf["INSTA_ID"],
            self.cnf["ADSET_HOURS"],
            self.cnf["OPTIMIZATION_GOAL"],
            self.cnf["DESTINATION_TYPE"],
            promoted_object,
        )

        adset = create_adset(ac)

        ads = [create_ad(adset, c, "ACTIVE") for c in creatives]
        return (adset, ads)

    def create_creative(self, stratum: Stratum, config: CreativeConf) -> AdCreative:
        md = {**stratum.metadata, **self.cnf["EXTRA_METADATA"]}

        if isinstance(self.destination, FlyMessengerDestination):
            md = {**md, "form": self.destination.initial_shortcode}
            ref = make_ref(config.name, md)
            msg = make_welcome_message(config.welcome_message, config.button_text, ref)

            return create_creative(
                config,
                self.cnf["PAGE_ID"],
                call_to_action=messenger_call_to_action(),
                page_welcome_message=msg,
                insta_id=self.cnf["INSTA_ID"],
                url_tags=f"ref={ref}",
            )

        if isinstance(self.destination, AppDestination):
            ref = make_ref(config.name, md)
            deeplink = self.destination.deeplink_template.format(ref=ref)
            link = self.destination.app_install_link

            return create_creative(
                config,
                self.cnf["PAGE_ID"],
                call_to_action=app_download_call_to_action(deeplink),
                insta_id=self.cnf["INSTA_ID"],
                link=link,
            )
