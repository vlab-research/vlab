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
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting

from .facebook.reconciliation import adset_dif
from .facebook.state import CampaignState, split
from .facebook.update import Instruction

Params = Dict[str, Any]


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


FacebookTargeting = Dict[str, Any]


class CampaignConf(NamedTuple):
    optimization_goal: str
    destination_type: str
    page_id: str
    instagram_id: Optional[str]
    adset_hours: int
    budget: float
    min_budget: float
    opt_window: int
    end_date: str
    proportional: bool
    ad_account: str
    ad_campaign: str


class CreativeConf(NamedTuple):
    name: str
    image_hash: str
    image: str
    body: str
    welcome_message: str
    link_text: str
    button_text: str
    form: str


class StratumConf(NamedTuple):
    id: str
    quota: Union[int, float]
    creatives: List[str]
    shortcodes: List[str]
    audiences: List[str]
    excluded_audiences: List[str]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: Dict[str, str]


# OLD
# {
#     "name": f"vlab-vacc-{COUNTRY_CODE}-vacc-A+B",
#     "shortcodes": SURVEY_SHORTCODES,
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
#     "shortcodes": SURVEY_SHORTCODES,
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
#     "shortcodes": SURVEY_SHORTCODES,
#     "subtype": "PARTITIONED",
#     "partitioning": {
#     },

# create higher level audience conf object that generates
# AudienceConfs dynamically (in the case of a partitioned audience)
# --> you're implicitly doing this already with custom/lookalike, no?

# OR add configuration -> make it dummer.
# In addition to question_targeting, you have some sort of config
# needed to get users from database, without knowing anything else.
#
# Or make this one the higher level, that's what's happenign already.
# and in addition to "lookalike" it has a "partitions" field...?
# but the 1-1 mapping of AudienceConf to audience will be removed.
# But that's probably better for the old way anyhoo.
#
# The way it's currently is in "manage_aud" -> could work within that.
# It's not a perfect parallel with Lookalikes, because their the set of
# users doesn't really change - or for lookalikes there are no users!


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


class LookalikeSpec(NamedTuple):
    country: str
    ratio: float
    starting_ratio: float


class Lookalike(NamedTuple):
    target: int
    spec: LookalikeSpec


class AudienceConf(NamedTuple):
    name: str
    subtype: str
    shortcodes: List[str]
    question_targeting: Optional[QuestionTargeting] = None
    lookalike: Optional[Lookalike] = None
    partitioning: Optional[Partitioning] = None


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
    shortcodes: List[str]
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
    name = f"vlab-{c.stratum.id}"  # TODO: remove vlab prefix
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


def make_ref(creative: CreativeConf, metadata: Metadata) -> str:
    s = f"form.{creative.form}.creative.{creative.name}"
    for k, v in metadata.items():
        s += f".{k}.{quote(v)}"
    return s


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


def create_creative(
    config: CreativeConf, metadata: Metadata, page_id: str, insta_id: Optional[str]
) -> AdCreative:

    ref = make_ref(config, metadata)
    msg = make_welcome_message(config.welcome_message, config.button_text, ref)

    oss = {
        AdCreativeObjectStorySpec.Field.link_data: {
            AdCreativeLinkData.Field.call_to_action: {
                "type": "MESSAGE_PAGE",
                "value": {"app_destination": "MESSENGER"},
            },
            AdCreativeLinkData.Field.image_hash: config.image_hash,
            AdCreativeLinkData.Field.message: config.body,
            AdCreativeLinkData.Field.name: config.link_text,
            AdCreativeLinkData.Field.page_welcome_message: msg,
        },
        AdCreativeObjectStorySpec.Field.page_id: page_id,
    }

    c = AdCreative()

    if insta_id:
        c[AdCreative.Field.instagram_actor_id] = insta_id
        oss[AdCreativeObjectStorySpec.Field.instagram_actor_id] = insta_id # used???


    c[AdCreative.Field.name] = config.name
    c[AdCreative.Field.url_tags] = f"ref={ref}"
    c[AdCreative.Field.actor_id] = page_id
    c[AdCreative.Field.object_story_spec] = oss

    return c


class Marketing:
    def __init__(self, state: CampaignState, config: CampaignConf):
        cnf: Dict[str, Any] = {
            "PAGE_ID": config.page_id,
            "INSTA_ID": config.instagram_id,
            "OPTIMIZATION_GOAL": config.optimization_goal,
            "DESTINATION_TYPE": config.destination_type,
            "ADSET_HOURS": config.adset_hours,
        }

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

        ac = AdsetConf(
            self.state.campaign,
            stratum,
            budget,
            "ACTIVE",
            self.cnf["INSTA_ID"],
            self.cnf["ADSET_HOURS"],
            self.cnf["OPTIMIZATION_GOAL"],
            self.cnf["DESTINATION_TYPE"],
        )

        adset = create_adset(ac)

        ads = [create_ad(adset, c, "ACTIVE") for c in creatives]
        return (adset, ads)

    def create_creative(self, stratum: Stratum, config: CreativeConf) -> AdCreative:
        return create_creative(
            config, stratum.metadata, self.cnf["PAGE_ID"], self.cnf["INSTA_ID"]
        )
