import json
import random
from dataclasses import asdict, dataclass, fields
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
from .facebook.state import FacebookState, split
from .facebook.update import Instruction
from .study_conf import (AppDestination, Audience, CampaignConf, CreativeConf,
                         DestinationConf, FlyMessengerDestination,
                         LookalikeAudience, Stratum, StudyConf, WebDestination)

ADSET_HOURS = 48

Metadata = Dict[str, str]


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


from dataclasses import is_dataclass


def dict_from_nested_type(d):
    """Handles both Facebook SDK's types and Named Tuples
    and Pydantic BaseModels and dataclasses"""

    if hasattr(d, "export_data"):
        d = d.export_data()

    if hasattr(d, "_asdict"):
        d = d._asdict()

    if hasattr(d, "dict"):
        d = d.dict()

    if is_dataclass(d):
        d = asdict(d)

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
        return [create_lookalike_audience(aud.name, aud.spec.dict(), origin)]

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


def messenger_call_to_action() -> dict:
    return {
        "type": "MESSAGE_PAGE",
        "value": {"app_destination": "MESSENGER"},
    }


def app_download_call_to_action(deeplink) -> dict:
    return {
        "type": "INSTALL_MOBILE_APP",
        "value": {"app_link": deeplink},
    }


def _create_creative(
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


def create_creative(
    study: StudyConf, stratum: Stratum, config: CreativeConf
) -> AdCreative:
    md = {**stratum.metadata, **study.general.extra_metadata}

    dest_lookup = {d.name: d for d in study.destinations}

    try:
        destination = dest_lookup[config.destination]
    except KeyError as e:
        raise Exception(
            f"Config Problem: destination {config.destination} is "
            f"not configured. Destination options: {list(dest_lookup.keys())}"
        ) from e

    if isinstance(destination, FlyMessengerDestination):
        md = {**md, "form": destination.initial_shortcode}
        ref = make_ref(config.name, md)
        msg = make_welcome_message(config.welcome_message, config.button_text, ref)

        return _create_creative(
            config,
            study.general.page_id,
            call_to_action=messenger_call_to_action(),
            page_welcome_message=msg,
            insta_id=study.general.instagram_id,
            url_tags=f"ref={ref}",
        )

    if isinstance(destination, AppDestination):
        ref = make_ref(config.name, md)
        deeplink = destination.deeplink_template.format(ref=ref)
        link = destination.app_install_link

        return _create_creative(
            config,
            study.general.page_id,
            call_to_action=app_download_call_to_action(deeplink),
            insta_id=study.general.instagram_id,
            link=link,
        )

    if isinstance(destination, WebDestination):
        ref = make_ref(config.name, md)
        pass  # to implement

    raise Exception(f"destination is not a proper type: {destination}")


def adset_instructions(
    study: StudyConf, state: FacebookState, stratum: Stratum, budget: float
) -> Tuple[AdSet, List[Ad]]:

    creatives = [create_creative(study, stratum, c) for c in stratum.creatives]

    # app destination needs to be set at adest, can't be multiple...
    if len(study.destinations) == 1 and isinstance(
        study.destinations[0], AppDestination
    ):
        d = study.destinations[0]
        promoted_object = {
            AdPromotedObject.Field.application_id: d.facebook_app_id,
            AdPromotedObject.Field.object_store_url: d.app_install_link,
        }
    else:
        promoted_object = None

    ac = AdsetConf(
        state.campaigns[0],  # TODO: multi campaign!
        stratum,
        budget,
        "ACTIVE",
        study.general.instagram_id,
        ADSET_HOURS,
        study.general.optimization_goal,
        study.general.destination_type,
        promoted_object,
    )

    adset = create_adset(ac)

    ads = [create_ad(adset, c, "ACTIVE") for c in creatives]
    return (adset, ads)


# need to turn budget, stratum -> spend, into spending
# across different campaigns.
# --> create an intermediate function with tested business logic
# then use this to do adset diff.

# one function to go from StudyConf -> CampaignGroup Spending Schedule.
def update_instructions(
    study: StudyConf,
    state: FacebookState,
    strata: List[Stratum],
    budget: Dict[str, float],
) -> Sequence[Instruction]:

    sb = [(s, budget[s.id]) for s in strata]
    new_state = [adset_instructions(study, state, s, b) for s, b in sb if b > 0]

    # TODO: fix campaign name --> multicampaign!
    return adset_dif(
        state.campaign_state(study.general.ad_campaign_name).campaign_state, new_state
    )
