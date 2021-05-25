import json
import random
from datetime import datetime, timedelta
from typing import (Any, Dict, List, NamedTuple, Optional, Sequence, Tuple,
                    TypeVar, Union)
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

from .facebook.state import CampaignState, split
from .facebook.update import Instruction

Params = Dict[str, Any]


class UserInfo(NamedTuple):
    survey_user: str
    token: str


# add max_budget - for max daily budget
# make budget optional - only for proportional


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


class CreativeGroup(NamedTuple):
    name: str
    creatives: List[CreativeConf]


class TargetVar(NamedTuple):
    type: str
    value: Union[str, int, float]


class QuestionTargeting(NamedTuple):
    op: str
    vars: List[Union[TargetVar, "QuestionTargeting"]]  # type: ignore


FacebookTargeting = Dict[str, Any]


class Stratum(NamedTuple):
    id: str
    quota: Union[int, float]
    creatives: List[CreativeConf]
    shortcodes: List[str]
    facebook_targeting: FacebookTargeting
    question_targeting: Optional[QuestionTargeting]
    metadata: Dict[str, str]


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


class LookalikeSpec(NamedTuple):
    country: str
    ratio: float
    starting_ratio: float


class Lookalike(NamedTuple):
    name: str
    target: int
    spec: LookalikeSpec


class AudienceConf(NamedTuple):
    name: str
    subtype: str
    shortcodes: List[str]
    question_targeting: Optional[QuestionTargeting] = None
    lookalike: Optional[Lookalike] = None


class Audience(NamedTuple):
    name: str
    subtype: str
    pageid: str
    users: List[str]
    lookalike: Optional[Lookalike] = None


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

    if c.instagram_id:
        adset[AdSet.Field.instagram_actor_id] = c.instagram_id

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


def make_ref(creative: CreativeConf, stratum: Stratum) -> str:
    s = f"form.{creative.form}.creative.{creative.name}"
    for k, v in stratum.metadata.items():
        s += f".{k}.{quote(v)}"
    return s


def create_ad(adset: AdSet, creative: AdCreative, status: str) -> Ad:
    a = Ad()
    a[Ad.Field.name] = creative["name"]
    a[Ad.Field.status] = status
    a[Ad.Field.adset_id] = adset["id"]
    a[Ad.Field.creative] = creative
    return a


def manage_aud(old_auds: List[CustomAudience], aud: Audience) -> List[Instruction]:

    existing = {a["name"]: a for a in old_auds}
    ca = existing.get(aud.name)

    if ca is None:
        return [create_custom_audience(aud.name, "virtual lab auto-generated audience")]

    instructions = add_users_to_audience(aud.pageid, ca.get_id(), aud.users)

    if aud.subtype == "LOOKALIKE" and aud.lookalike is not None:
        count = ca["approximate_count"]
        if aud.lookalike.name not in existing and count > aud.lookalike.target:
            instructions += [
                create_lookalike_audience(
                    aud.lookalike.name, aud.lookalike.spec._asdict(), ca
                )
            ]

    return instructions


def manage_audiences(state, new_auds: List[Audience]) -> List[Instruction]:
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


def _eq(a, b, fields=None) -> bool:
    try:
        a, b = a.export_all_data(), b.export_all_data()
    except AttributeError:
        pass

    try:
        for k, v in a.items():
            if fields and k not in fields:
                continue
            if k not in b:
                continue
            if not _eq(v, b[k]):
                return False
        return True

    except AttributeError:
        return a == b


def update_adset(source: AdSet, adset: AdSet) -> List[Instruction]:
    fields = [
        AdSet.Field.end_time,
        AdSet.Field.targeting,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
        AdSet.Field.optimization_goal,
    ]

    if _eq(source, adset, fields):
        return []

    dat = adset.export_all_data()
    params = {f: dat[f] for f in fields}
    return [Instruction("adset", "update", params, source["id"])]


def update_ad(source: Ad, ad: Ad) -> List[Instruction]:

    if not _eq(ad["creative"], source["creative"]):
        return [Instruction("ad", "update", ad.export_all_data(), source["id"])]

    elif source["status"] != ad["status"]:
        return [Instruction("ad", "update", {"status": ad["status"]}, source["id"])]

    return []


T = TypeVar("T", AdSet, Ad)


def _dedup_olds(type_: str, li: Sequence[T]) -> Tuple[Dict[str, T], List[Instruction]]:

    lookup = {}
    instructions = []

    for obj in li:
        if obj["name"] in lookup:
            instructions += [Instruction(type_, "delete", {}, obj["id"])]
        else:
            lookup[obj["name"]] = obj

    return lookup, instructions


def _diff(type_, updater, creator, olds, news) -> List[Instruction]:
    try:
        old_lookup, instructions = _dedup_olds(type_, olds)
    except KeyError as e:
        raise Exception("Old ad(set)s do not have name!") from e

    updated = set()

    for x in news:
        if x["name"] in old_lookup:
            updated.add(x["name"])
            instructions += updater(old_lookup[x["name"]], x)
        else:
            instructions += creator(x)

    for x in olds:
        if x["name"] not in updated and x["status"] != "PAUSED":
            instructions += [
                Instruction(type_, "update", {"status": "PAUSED"}, x["id"])
            ]

    return instructions


def ad_dif(
    adset: AdSet,
    old_ads: Sequence[Ad],
    new_ads: Sequence[Ad],
) -> List[Instruction]:
    def creator(x):
        params = {**x.export_all_data(), "adset_id": adset["id"]}
        return [Instruction("ad", "create", params, None)]

    return _diff("ad", update_ad, creator, old_ads, new_ads)


def adset_dif(
    old_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
    new_adsets: Sequence[Tuple[AdSet, Sequence[Ad]]],
) -> List[Instruction]:

    new_lookup = {a["name"]: ads for a, ads in new_adsets}
    old_lookup = {a["name"]: ads for a, ads in old_adsets}

    def updater(source, adset):
        instructions = update_adset(source, adset)
        instructions += ad_dif(
            source, old_lookup[source["name"]], new_lookup[adset["name"]]
        )
        return instructions

    creator = lambda x: [Instruction("adset", "create", x.export_all_data(), None)]

    olds, news = [[a for a, _ in x] for x in [old_adsets, new_adsets]]

    return _diff("adset", updater, creator, olds, news)


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

        ref = make_ref(config, stratum)
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
            AdCreativeObjectStorySpec.Field.page_id: self.cnf["PAGE_ID"],
        }

        if self.cnf["INSTA_ID"]:
            oss[AdCreativeObjectStorySpec.Field.instagram_actor_id] = self.cnf[
                "INSTA_ID"
            ]

        c = AdCreative()
        c[AdCreative.Field.name] = config.name
        c[AdCreative.Field.url_tags] = f"ref={ref}"
        c[AdCreative.Field.actor_id] = self.cnf["PAGE_ID"]
        c[AdCreative.Field.object_story_spec] = oss

        return c
