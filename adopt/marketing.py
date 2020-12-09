import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Sequence
from urllib.parse import quote

import typing_json
import xxhash
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
from facebook_business.adobjects.adcreativeobjectstoryspec import \
    AdCreativeObjectStorySpec
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting
from toolz import get_in

from .facebook.state import CampaignState
from .facebook.update import Instruction

Params = Dict[str, Any]


class Cluster(NamedTuple):
    id: str
    name: str


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


class TargetQuestion(NamedTuple):
    ref: str
    op: str
    field: str
    value: Optional[str] = None
    name: Optional[str] = None


FacebookTargeting = Dict[str, Any]


class Stratum(NamedTuple):
    id: str
    quota: int
    creatives: List[CreativeConf]
    shortcodes: List[str]
    target_questions: List[TargetQuestion]
    facebook_targeting: FacebookTargeting = {}
    metadata: Dict[str, str] = {}


class StratumConf(NamedTuple):
    id: str
    quota: int
    creatives: List[str]
    shortcodes: List[str]
    target_questions: List[TargetQuestion]
    facebook_targeting: FacebookTargeting = {}
    metadata: Dict[str, str] = {}


class Location(NamedTuple):
    lat: float
    lng: float
    rad: float


class AdsetConf(NamedTuple):
    campaign: Campaign
    stratum: Stratum
    creatives: List[AdCreative]
    budget: float
    status: str
    instagram_id: str
    hours: int
    optimization_goal: str
    destination_type: str


class LookalikeSpec(NamedTuple):
    country: str
    ratio: float
    starting_ratio: float


class Audience(NamedTuple):
    name: str
    type: str
    shortcodes: List[str]
    target_questions: List[TargetQuestion]
    lookalike_spec: Optional[LookalikeSpec] = None


class TargetingConf(NamedTuple):
    audiences: List[Audience]
    strata: List[Stratum]


def parse_sc(s: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        **s,
        "target_questions": [TargetQuestion(**t) for t in s["target_questions"]],
    }


def load_strata_conf(path: str) -> List[StratumConf]:
    with open(path) as f:
        d = json.loads(f.read())
        return [StratumConf(**parse_sc(s)) for s in d]


def parse_conf(d: Mapping[str, Sequence[Mapping[str, Any]]]) -> TargetingConf:
    try:
        audiences = typing_json.from_json_obj(d["audiences"], List[Audience])
        strata = [Stratum(**parse_sc(s)) for s in d["strata"]]
        return TargetingConf(audiences, strata)
    except KeyError as e:
        raise Exception("Could not parse targeting config, missing keys") from e


def validate_targeting(targeting):
    valid_targets = set(dir(Targeting.Field))
    for k, _ in targeting.items():
        if k not in valid_targets:
            raise Exception(f"Targeting config invalid, key: {k} does not exist!")


def create_adset(c: AdsetConf) -> AdSet:
    name = f"vlab-{c.stratum.id}"
    targeting = {**c.stratum.facebook_targeting}

    adset = AdSet()
    adset[AdSet.Field.end_time] = datetime.utcnow() + timedelta(hours=c.hours)
    adset[AdSet.Field.targeting] = targeting
    adset[AdSet.Field.status] = c.status
    adset[AdSet.Field.daily_budget] = c.budget
    adset[AdSet.Field.name] = name
    adset[AdSet.Field.instagram_actor_id] = c.instagram_id
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
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {"type": "postback", "title": button_text, "payload": payload}
                    ],
                },
            }
        }
    }

    return json.dumps(message, sort_keys=True)


def make_ref(form: str, stratum: Stratum) -> str:
    s = f"form.{form}"
    for k, v in stratum.metadata.items():
        s += f".{k}.{quote(v)}"
    return s


def ads_for_adset(adset, ads):
    return [a for a in ads if a["adset_id"] == adset["id"]]


def create_ad(adset: AdSet, creative: AdCreative, status: str) -> Ad:
    a = Ad()
    a[Ad.Field.name] = creative["name"]
    a[Ad.Field.status] = status
    a[Ad.Field.adset_id] = adset["id"]
    a[Ad.Field.creative] = creative
    return a


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


def split(li, N):
    while li:
        head, li = li[:N], li[N:]
        yield head


def add_users_to_audience(
    pageid: str, aud_id: str, users: List[str]
) -> List[Instruction]:

    params: Dict[str, Any] = {
        "schema": ["PAGEUID"],
        "is_raw": True,
        "page_ids": [pageid],
    }

    return [
        Instruction(
            "custom_audience",
            "add_users",
            {**params, "data": [[u] for u in chunk]},
            aud_id,
        )
        for chunk in split(users, 1000)
    ]


def update_adset(source: AdSet, adset: AdSet) -> Instruction:
    fields = [
        AdSet.Field.end_time,
        AdSet.Field.targeting,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
    ]
    params = {f: adset[f] for f in fields}
    return Instruction("adset", "update", params, source["id"])


def manage_adset(
    state: CampaignState, adset: AdSet, creatives: List[AdCreative]
) -> List[Instruction]:

    source = next((a for a in state.adsets if a["name"] == adset["name"]), None)

    if source:
        running_ads = ads_for_adset(source, state.ads)
        instructions = [update_adset(source, adset)]
        instructions += ad_diff(source, running_ads, state.creatives, creatives)
        return instructions

    return [Instruction("adset", "create", adset.export_all_data(), None)]


def hash_creative(creative: AdCreative) -> str:
    keys = [
        ["actor_id"],
        ["url_tags"],
        ["object_story_spec", "instagram_actor_id"],
        ["object_story_spec", "link_data", "image_hash"],
        ["object_story_spec", "link_data", "message"],
        ["object_story_spec", "link_data", "name"],
        ["object_story_spec", "link_data", "page_welcome_message"],
    ]

    vals = [get_in(k, creative) for k in keys]
    vals = [v for v in vals if v]
    s = " ".join(vals)
    return xxhash.xxh64(s).hexdigest()


# Hashing ourselves makes everything much simpler, given so
# many creatives (every ref change is a different creative)
def ad_diff(
    adset: AdSet,
    running_ads: List[Ad],
    current_creatives: List[AdCreative],
    creatives: List[AdCreative],
) -> List[Instruction]:

    creative_lookup = {c["id"]: c for c in current_creatives}

    olds = [(a, "", a["creative"]["id"]) for a in running_ads]
    olds = [(a, "", creative_lookup[c]) for a, _, c in olds]
    olds = [(a, hash_creative(c), c) for a, _, c in olds]

    old_hashes = [h for _, h, _ in olds]
    new_hashes = {hash_creative(c): c for c in creatives}

    pause = lambda a: Instruction("ad", "update", {"status": "PAUSED"}, a["id"])
    run = lambda a: Instruction("ad", "update", {"status": "ACTIVE"}, a["id"])
    create = lambda c: Instruction(
        "ad", "create", create_ad(adset, c, "ACTIVE").export_all_data(), None
    )

    instructions = [
        pause(a)
        for a, h, c in olds
        if h not in new_hashes.keys() and a["status"] != "PAUSED"
    ]

    instructions += [
        run(a) for a, h, c in olds if h in new_hashes.keys() and a["status"] != "ACTIVE"
    ]

    instructions += [create(c) for h, c in new_hashes.items() if h not in old_hashes]

    return instructions


# TODO: abstract this into general lib
# and wrap with project-specific parts
class Marketing:
    def __init__(self, env, state):
        cnf = {
            "PAGE_ID": env("FACEBOOK_PAGE_ID"),
            "INSTA_ID": env("FACEBOOK_INSTA_ID"),
            "OPTIMIZATION_GOAL": env("FACEBOOK_OPTIMIZATION_GOAL"),
            "DESTINATION_TYPE": env("FACEBOOK_DESTINATION_TYPE"),
            "ADSET_HOURS": env.int("FACEBOOK_ADSET_HOURS"),
        }

        self.state = state
        self.cnf = cnf

    def adset_instructions(self, stratum: Stratum, budget: float) -> List[Instruction]:
        creatives = [self.create_creative(stratum, c) for c in stratum.creatives]
        status = "PAUSED" if budget == 0 else "ACTIVE"

        ac = AdsetConf(
            self.state.campaign,
            stratum,
            creatives,
            budget,
            status,
            self.cnf["INSTA_ID"],
            self.cnf["ADSET_HOURS"],
            self.cnf["OPTIMIZATION_GOAL"],
            self.cnf["DESTINATION_TYPE"],
        )

        adset = create_adset(ac)
        return manage_adset(self.state, adset, creatives)

    def create_creative(self, stratum: Stratum, config: CreativeConf) -> AdCreative:

        ref = make_ref(config.form, stratum)
        msg = make_welcome_message(config.welcome_message, config.button_text, ref)

        oss = {
            AdCreativeObjectStorySpec.Field.instagram_actor_id: self.cnf["INSTA_ID"],
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

        c = AdCreative()
        c[AdCreative.Field.name] = config.name
        c[AdCreative.Field.url_tags] = f"ref={ref}"
        c[AdCreative.Field.actor_id] = self.cnf["PAGE_ID"]
        c[AdCreative.Field.object_story_spec] = oss
        c[AdCreative.Field.adlabels] = [self.state.label]

        return c
