import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional
from urllib.parse import quote

import xxhash
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting
from toolz import get_in

from .facebook.update import Instruction

Params = Dict[str, Any]


class Cluster(NamedTuple):
    id: str
    name: str


class CreativeConfig(NamedTuple):
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
    creatives: List[CreativeConfig]


class TargetQuestion(NamedTuple):
    name: str
    ref: str
    op: str
    field: str
    value: Optional[str]


FacebookTargeting = Dict[str, Any]


class StratumConf(NamedTuple):
    id: str
    metadata: Dict[str, str]
    quota: int
    creative_group: str
    custom_audience: bool
    facebook_targeting: FacebookTargeting
    surveys: List[str]
    target_questions: List[TargetQuestion]


class Location(NamedTuple):
    lat: float
    lng: float
    rad: float


class AdsetConf(NamedTuple):
    campaign: Campaign
    stratum: StratumConf
    creatives: List[Params]
    budget: Optional[float]
    status: str
    instagram_id: str
    hours: int
    audience: Optional[CustomAudience]
    excluded_audience: Optional[CustomAudience]
    optimization_goal: str


def validate_targeting(targeting):
    valid_targets = set(dir(Targeting.Field))
    for k, _ in targeting.items():
        if k not in valid_targets:
            raise Exception(f"Targeting config invalid, key: {k} does not exist!")


def _adset_base(c: AdsetConf) -> Params:
    targeting = {**c.stratum.facebook_targeting}

    if c.audience:
        targeting[Targeting.Field.custom_audiences] = [{"id": c.audience["id"]}]

    if c.excluded_audience:
        targeting[Targeting.Field.excluded_custom_audiences] = [
            {"id": c.excluded_audience["id"]}
        ]

    params = {
        AdSet.Field.end_time: datetime.utcnow() + timedelta(hours=c.hours),
        AdSet.Field.targeting: targeting,
        AdSet.Field.status: c.status,
    }

    return params


def update_adset(adset: AdSet, c: AdsetConf) -> Instruction:
    params = _adset_base(c)

    if c.budget:
        params[AdSet.Field.daily_budget] = c.budget

    return Instruction("adset", "update", params, adset["id"])


def create_adset(name, c: AdsetConf) -> Instruction:
    params = _adset_base(c)

    params = {
        **params,
        AdSet.Field.name: name,
        AdSet.Field.instagram_actor_id: c.instagram_id,
        AdSet.Field.daily_budget: c.budget,
        AdSet.Field.start_time: datetime.utcnow() + timedelta(minutes=5),
        AdSet.Field.campaign_id: c.campaign["id"],
        AdSet.Field.optimization_goal: c.optimization_goal,
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.bid_strategy: AdSet.BidStrategy.lowest_cost_without_cap,
    }

    return Instruction("adset", "create", params, None)


def hash_creative(creative):
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


def make_ref(form: str, stratum: StratumConf) -> str:
    id_ = quote(stratum.id)
    s = f"form.{form}.stratumid.{id_}"
    for k, v in stratum.metadata.items():
        s += f".{k}.{v}"
    return s


def ads_for_adset(adset, ads):
    return [a for a in ads if a["adset_id"] == adset["id"]]


def create_ad(adset, creative, status) -> Dict[str, Any]:
    return {
        "name": creative["name"],
        "status": status,
        "adset_id": adset["id"],
        "creative": creative,
    }


def create_custom_audience(name: str, desc: str) -> Instruction:
    params = {
        "name": name,
        "subtype": "CUSTOM",
        "description": desc,
        "customer_file_source": "USER_PROVIDED_ONLY",
    }

    return Instruction("custom_audience", "create", params, None)


def split(li, N):
    while li:
        head, li = li[:N], li[N:]
        yield head


def add_users_to_audience(pageid, aud_id, users) -> List[Instruction]:
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


def ad_diff(
    adset,
    running_ads: List[Ad],
    current_creatives: List[AdCreative],
    creatives: List[Dict[str, Any]],
) -> List[Instruction]:

    creative_lookup = {c["id"]: c for c in current_creatives}

    olds = [(a, None, a["creative"]["id"]) for a in running_ads]
    olds = [(a, None, creative_lookup[c]) for a, _, c in olds]
    olds = [(a, hash_creative(c), c) for a, _, c in olds]

    old_hashes = [h for _, h, _ in olds]
    new_hashes = {hash_creative(c): c for c in creatives}

    pause = lambda a: Instruction("ad", "update", {"status": "PAUSED"}, a["id"])
    run = lambda a: Instruction("ad", "update", {"status": "ACTIVE"}, a["id"])
    create = lambda c: Instruction("ad", "create", create_ad(adset, c, "ACTIVE"), None)

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


class Marketing:
    def __init__(self, env, state):
        cnf = {
            "APP_ID": env("FACEBOOK_APP_ID"),
            "APP_SECRET": env("FACEBOOK_APP_SECRET"),
            "PAGE_ID": env("FACEBOOK_PAGE_ID"),
            "INSTA_ID": env("FACEBOOK_INSTA_ID"),
            "USER_TOKEN": env("FACEBOOK_USER_TOKEN"),
            "AD_ACCOUNT": f'act_{env("FACEBOOK_AD_ACCOUNT")}',
            "CAMPAIGN": env("FACEBOOK_AD_CAMPAIGN"),
            "OPTIMIZATION_GOAL": env("FACEBOOK_OPTIMIZATION_GOAL"),
            "AD_LABEL": env("FACEBOOK_AD_LABEL"),
            "ADSET_HOURS": env.int("FACEBOOK_ADSET_HOURS"),
            "LOOKALIKE_STARTING_RATIO": env.float("FACEBOOK_LOOKALIKE_STARTING_RATIO"),
            "LOOKALIKE_RATIO": env.float("FACEBOOK_LOOKALIKE_RATIO"),
        }

        self.state = state
        self.cnf = cnf

    def adset_instructions(
        self,
        cg: CreativeGroup,
        stratum: StratumConf,
        budget: Optional[float],
        audience: Optional[CustomAudience],
        anti_audience: Optional[CustomAudience],
    ) -> List[Instruction]:

        creatives = [self.create_creative(stratum, c) for c in cg.creatives]
        status = "ACTIVE" if budget else "PAUSED"

        ac = AdsetConf(
            self.state.campaign,
            stratum,
            creatives,
            budget,
            status,
            self.cnf["INSTA_ID"],
            self.cnf["ADSET_HOURS"],
            audience,
            anti_audience,
            self.cnf["OPTIMIZATION_GOAL"],
        )

        return self.manage_adset(ac)

    def manage_adset(self, adset_conf: AdsetConf) -> List[Instruction]:

        name = f"vlab-{adset_conf.stratum.id}"
        adset = next((a for a in self.state.adsets if a["name"] == name), None)

        if adset:
            running_ads = ads_for_adset(adset, self.state.ads)
            instructions = [update_adset(adset, adset_conf)]
            instructions += ad_diff(
                adset, running_ads, self.state.creatives, adset_conf.creatives
            )
            return instructions

        return [create_adset(name, adset_conf)]

    def add_users(self, audience, users):
        return add_users_to_audience(self.cnf["PAGE_ID"], audience.get_id(), users)

    def lookalike_settings(self, aud_name):
        slr, lr = self.cnf["LOOKALIKE_STARTING_RATIO"], self.cnf["LOOKALIKE_RATIO"]
        name = f"vlab-lookalike-{aud_name}-{slr}-{lr}"
        return name, slr, lr

    def create_lookalike(self, audience_name: str, country: str) -> Instruction:
        custom_audience = self.state.get_audience(audience_name)
        name, slr, lr = self.lookalike_settings(custom_audience["name"])

        spec = {"starting_ratio": slr, "ratio": lr, "country": country}

        params = {
            CustomAudience.Field.name: name,
            CustomAudience.Field.subtype: CustomAudience.Subtype.lookalike,
            CustomAudience.Field.origin_audience_id: custom_audience.get_id(),
            CustomAudience.Field.lookalike_spec: json.dumps(spec),
        }

        return Instruction("custom_audience", "create", params, None)

    def get_lookalike(self, audience_name: str) -> CustomAudience:
        custom_audience = self.state.get_audience(audience_name)
        name, _, _ = self.lookalike_settings(custom_audience["name"])
        return self.state.get_audience(name)

    def create_creative(
        self, stratum: StratumConf, config: CreativeConfig
    ) -> Dict[str, Any]:

        ref = make_ref(config.form, stratum)
        msg = make_welcome_message(config.welcome_message, config.button_text, ref)

        oss = {
            "instagram_actor_id": self.cnf["INSTA_ID"],
            "link_data": {
                "call_to_action": {
                    "type": "MESSAGE_PAGE",
                    "value": {"app_destination": "MESSENGER"},
                },
                "image_hash": config.image_hash,
                "message": config.body,
                "name": config.link_text,
                "page_welcome_message": msg,
            },
            "page_id": self.cnf["PAGE_ID"],
        }

        params = {
            "name": config.name,
            "url_tags": f"ref={ref}",
            "actor_id": self.cnf["PAGE_ID"],
            "object_story_spec": oss,
            "adlabels": [self.state.label],
        }

        return params
