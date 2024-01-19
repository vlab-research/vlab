import json
import logging
import random
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timedelta
from typing import (Any, Dict, List, NamedTuple, Optional, Sequence, Tuple,
                    Union)
from urllib.parse import quote

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
# from facebookads.adobjects.adcreativevideodata \
#     import AdCreativeVideoData
from facebook_business.adobjects.adcreativeobjectstoryspec import \
    AdCreativeObjectStorySpec
from facebook_business.adobjects.adpromotedobject import AdPromotedObject
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting

from .budget import Budget
from .facebook.reconciliation import adset_dif
from .facebook.state import CampaignState, FacebookState, StateNameError, split
from .facebook.update import Instruction
from .study_conf import (AppDestination, Audience, CreativeConf,
                         DestinationConf, FlyMessengerDestination, GeneralConf,
                         LookalikeAudience, Stratum, StratumConf, StudyConf,
                         WebDestination)

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
    hours: int
    optimization_goal: str
    destination_type: str
    promoted_object: Optional[dict[str, str]]


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

    return add_users_to_audience(aud.page_ids, ca.get_id(), aud.users)


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
    page_ids: list[str], aud_id: str, users: List[str]
) -> List[Instruction]:
    params: Dict[str, Any] = {
        "schema": ["PAGEUID"],
        "is_raw": True,
        "page_ids": page_ids,
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


def web_call_to_action(link) -> dict:
    return {
        "type": "OPEN_LINK",
        "value": {"link": link},
    }


def _create_creative(
    config: CreativeConf,
    call_to_action: dict[str, Any],
    page_welcome_message: str | None = None,
    url_tags: str | None = None,
    link: str | None = None,
) -> AdCreative:
    c = AdCreative()

    c[AdCreative.Field.name] = config.name

    if url_tags:
        c[AdCreative.Field.url_tags] = url_tags

    fields_to_copy = [
        AdCreative.Field.actor_id,
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.effective_instagram_media_id,
        AdCreative.Field.effective_instagram_story_id,
        AdCreative.Field.effective_object_story_id,
        AdCreative.Field.instagram_actor_id,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.thumbnail_url,
    ]

    for field in fields_to_copy:
        if field in config.template:
            c[field] = config.template[field]

    tld = config.template["object_story_spec"].get("link_data")

    if tld:
        link_data = {
            AdCreativeLinkData.Field.call_to_action: call_to_action,
            AdCreativeLinkData.Field.image_hash: tld["image_hash"],
            AdCreativeLinkData.Field.message: tld.get("message"),
            AdCreativeLinkData.Field.name: tld.get("name"),
            AdCreativeLinkData.Field.description: tld.get("description"),
        }

        if page_welcome_message:
            link_data[
                AdCreativeLinkData.Field.page_welcome_message
            ] = page_welcome_message

        if link:
            link_data[AdCreativeLinkData.Field.link] = link

    toss = config.template["object_story_spec"]

    c[AdCreative.Field.object_story_spec] = {
        AdCreativeObjectStorySpec.Field.page_id: toss.get("page_id"),
        AdCreativeObjectStorySpec.Field.instagram_actor_id: toss.get(
            "instagram_actor_id"
        ),
        AdCreativeObjectStorySpec.Field.link_data: link_data if tld else None,
    }

    tafs = config.template.get(AdCreative.Field.asset_feed_spec)

    if tafs:
        c[AdCreative.Field.asset_feed_spec] = tafs

        if page_welcome_message:
            c[AdCreative.Field.asset_feed_spec]["additional_data"] = {
                "page_welcome_message": page_welcome_message
            }

        if link:
            c[AdCreative.Field.asset_feed_spec]["link_urls"] = [
                {**url, "website_url": link}
                for url in config.template[AdCreative.Field.asset_feed_spec][
                    "link_urls"
                ]
            ]

    return c


def get_destination_for_creative(
    study: StudyConf, config: CreativeConf
) -> DestinationConf:
    dest_lookup = {d.name: d for d in study.destinations}

    try:
        destination = dest_lookup[config.destination]
    except KeyError as e:
        raise Exception(
            f"Config Problem: destination {config.destination} is "
            f"not configured. Destination options: {list(dest_lookup.keys())}"
        ) from e

    return destination


def create_creative(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
) -> AdCreative:
    md = {**stratum.metadata, **study.general.extra_metadata}

    if isinstance(destination, FlyMessengerDestination):
        md = {**md, "form": destination.initial_shortcode}
        ref = make_ref(config.name, md)
        msg = make_welcome_message(
            destination.welcome_message, destination.button_text, ref
        )

        return _create_creative(
            config,
            call_to_action=messenger_call_to_action(),
            page_welcome_message=msg,
            url_tags=f"ref={ref}",
        )

    if isinstance(destination, AppDestination):
        ref = make_ref(config.name, md)
        deeplink = destination.deeplink_template.format(ref=ref)
        link = destination.app_install_link

        return _create_creative(
            config,
            call_to_action=app_download_call_to_action(deeplink),
            link=link,
        )

    if isinstance(destination, WebDestination):
        ref = make_ref(config.name, md)
        link = destination.url_template.format(ref=ref)

        return _create_creative(
            config,
            call_to_action=web_call_to_action(link),
            link=link,
        )

    raise Exception(f"destination is not a proper type: {destination}")


def adset_instructions(
    study: StudyConf, state: CampaignState, stratum: Stratum, budget: float
) -> Tuple[AdSet, List[Ad]]:
    destinations = [get_destination_for_creative(study, c) for c in stratum.creatives]
    creatives = [
        create_creative(study, stratum, c, d)
        for d, c in zip(destinations, stratum.creatives)
    ]

    if isinstance(destinations[0], AppDestination):
        # TODO: assert all destinations are the same
        # and raise an exception if not the case

        d = destinations[0]
        promoted_object = {
            AdPromotedObject.Field.application_id: d.facebook_app_id,
            AdPromotedObject.Field.object_store_url: d.app_install_link,
        }
    else:
        promoted_object = None

    # make paused adset if we have 0 budget
    status = "ACTIVE" if budget > 0 else "PAUSED"
    budget = budget if budget > 0 else study.recruitment.min_budget

    # Facebook budgets are in cents! We do everything in dollars.
    budget = round(budget * 100)

    ac = AdsetConf(
        state.campaign,
        stratum,
        budget,
        status,
        ADSET_HOURS,
        study.recruitment.optimization_goal,
        study.recruitment.destination_type,
        promoted_object,
    )

    adset = create_adset(ac)

    ads = [create_ad(adset, c, "ACTIVE") for c in creatives]
    return (adset, ads)


def create_campaign(name, objective) -> Instruction:
    params = {
        "name": name,
        "objective": objective,
        "status": "PAUSED",
        "special_ad_categories": [],
    }

    return Instruction("campaign", "create", params)


def update_instructions_for_campaign(
    study: StudyConf,
    state: FacebookState,
    campaign_name: str,
    strata: List[Stratum],
    budget: Dict[str, float],
) -> Sequence[Instruction]:
    try:
        campaign_state = state.campaign_state(campaign_name)
        campaign_state.campaign_state
    except StateNameError as e:
        print(e)
        logging.info(f"Could not find campaign with name {campaign_name}. Creating.")
        return [create_campaign(campaign_name, study.recruitment.objective)]

    sb = [(s, budget[s.id]) for s in strata]
    new_state = [adset_instructions(study, campaign_state, s, b) for s, b in sb]
    return adset_dif(campaign_state.campaign_state, new_state)


def update_instructions(
    study: StudyConf,
    state: FacebookState,
    strata: List[Stratum],
    budget: dict[str, Budget],
) -> Sequence[Instruction]:
    return [
        i
        for campaign_name, budg in budget.items()
        for i in update_instructions_for_campaign(
            study, state, campaign_name, strata, budg
        )
    ]
