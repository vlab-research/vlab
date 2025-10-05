import json
import logging
import random
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple, Union
from urllib.parse import quote

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
from facebook_business.adobjects.adcreativeobjectstoryspec import (
    AdCreativeObjectStorySpec,
)
from facebook_business.adobjects.adcreativevideodata import AdCreativeVideoData
from facebook_business.adobjects.adpromotedobject import AdPromotedObject
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting

from .budget import Budget
from .facebook.reconciliation import adset_dif, form_dif, get_latest_form_version
from .facebook.state import CampaignState, FacebookState, StateInitializationError, StateNameError, split
from .facebook.update import Instruction
from .study_conf import (
    AppDestination,
    Audience,
    CreativeConf,
    DestinationConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    LeadGenDestination,
    LookalikeAudience,
    Stratum,
    StudyConf,
    WebDestination,
)

ADSET_HOURS = 48

Metadata = Dict[str, str]


#############################
# Lead Gen Form Helpers
#############################


def make_leadgen_form_base_name(study_id: str, destination_name: str, stratum_id: str) -> str:
    """
    Create base name for a lead gen form (without version suffix).
    Format: {study_id}-{destination_name}-{stratum_id}
    """
    return f"{study_id}-{destination_name}-{stratum_id}"


def make_leadgen_form_name(base_name: str, version: int) -> str:
    """
    Create versioned form name.
    Format: {base_name}-v{version}
    """
    return f"{base_name}-v{version}"


def build_leadgen_form_params(
    destination: LeadGenDestination,
    stratum: Stratum,
    study: StudyConf,
) -> Dict[str, Any]:
    """
    Build parameters for creating a lead gen form.
    Pure function - returns new dict without mutations.
    """
    # Build tracking parameters - include all stratum metadata
    tracking_params = {
        "stratum_id": stratum.id,
        "study_id": study.id,
        **stratum.metadata,
        **study.general.extra_metadata,
    }

    # Build thank you page config
    thank_you_page = None
    if destination.thank_you_url_template:
        thank_you_page = {
            **destination.form_template.get("thank_you_page", {}),
            "url": destination.thank_you_url_template,
        }
    elif "thank_you_page" in destination.form_template:
        thank_you_page = destination.form_template["thank_you_page"]

    # Return new dict with all params
    result = {
        **destination.form_template,
        "page_id": destination.page_id,
        "tracking_parameters": [
            {"key": k, "value": v} for k, v in tracking_params.items()
        ],
    }

    if thank_you_page is not None:
        result["thank_you_page"] = thank_you_page

    return result


#############################
# Location and Config Types
#############################


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
    chunks = [(i + 1, chunk) for i, chunk in enumerate(split(users, 1_000))]
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


def convert_version(c):
    if 'degrees_of_freedom_spec' not in c:
        return c

    cfs = c['degrees_of_freedom_spec']['creative_features_spec']
    if 'standard_enhancements' in cfs:
        del cfs['standard_enhancements']

    return c

def _create_creative(
    config: CreativeConf,
    call_to_action: dict[str, Any],
    page_welcome_message: str | None = None,
    url_tags: str | None = None,
    link: str | None = None,
    lead_gen_form_id: str | None = None,
) -> AdCreative:
    c = AdCreative()

    c[AdCreative.Field.name] = config.name

    if url_tags:
        c[AdCreative.Field.url_tags] = url_tags

    fields_to_copy = [
        AdCreative.Field.actor_id,
        AdCreative.Field.degrees_of_freedom_spec,
        AdCreative.Field.instagram_user_id,
        AdCreative.Field.thumbnail_url,
        AdCreative.Field.contextual_multi_ads,
    ]

    for field in fields_to_copy:
        if field in config.template:
            c[field] = config.template[field]

    c = convert_version(c)

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

    tvd = config.template["object_story_spec"].get("video_data")
    if tvd:
        to_copy = [
            AdCreativeVideoData.Field.image_hash,
            AdCreativeVideoData.Field.message,
            AdCreativeVideoData.Field.title,
            AdCreativeVideoData.Field.video_id,
        ]

        video_data = {k: tvd.get(k) for k in to_copy}
        video_data[AdCreativeVideoData.Field.call_to_action] = call_to_action

        if page_welcome_message:
            video_data[
                AdCreativeVideoData.Field.page_welcome_message
            ] = page_welcome_message

    toss = config.template["object_story_spec"]

    c[AdCreative.Field.object_story_spec] = {
        AdCreativeObjectStorySpec.Field.page_id: toss.get("page_id"),
        AdCreativeObjectStorySpec.Field.instagram_user_id: toss.get(
            "instagram_user_id"
        ),
        AdCreativeObjectStorySpec.Field.link_data: link_data if tld else None,
        AdCreativeObjectStorySpec.Field.video_data: video_data if tvd else None,
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

    # Handle lead gen form
    if lead_gen_form_id:
        # For asset_feed_spec creatives
        if tafs:
            if "call_to_actions" not in c[AdCreative.Field.asset_feed_spec]:
                c[AdCreative.Field.asset_feed_spec]["call_to_actions"] = [{}]
            c[AdCreative.Field.asset_feed_spec]["call_to_actions"][0]["type"] = "LEAD_GEN"
            c[AdCreative.Field.asset_feed_spec]["call_to_actions"][0]["value"] = {
                "lead_gen_form_id": lead_gen_form_id
            }

        # For object_story_spec creatives
        else:
            # Could be in link_data or video_data
            if tld:
                link_data["call_to_action"] = {
                    "type": "LEAD_GEN",
                    "value": {"lead_gen_form_id": lead_gen_form_id}
                }
                c[AdCreative.Field.object_story_spec][AdCreativeObjectStorySpec.Field.link_data] = link_data
            elif tvd:
                video_data["call_to_action"] = {
                    "type": "LEAD_GEN",
                    "value": {"lead_gen_form_id": lead_gen_form_id}
                }
                c[AdCreative.Field.object_story_spec][AdCreativeObjectStorySpec.Field.video_data] = video_data

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


def _get_leadgen_form_id(
    study: StudyConf,
    stratum: Stratum,
    destination: LeadGenDestination,
    campaign_state: CampaignState,
) -> str:
    """
    Pure function to look up the form ID for a LeadGen creative.
    Raises StateInitializationError if form not found.
    """
    base_name = make_leadgen_form_base_name(study.id, destination.name, stratum.id)
    forms = campaign_state.facebook_state.page_forms(destination.page_id)

    latest = get_latest_form_version(forms, base_name)
    if latest is None:
        raise StateInitializationError(
            f"Lead gen form not found for {base_name}. "
            f"Forms should be created before creatives."
        )

    form, _ = latest
    return form["id"]


def create_creative(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
    campaign_state: CampaignState,
) -> AdCreative:
    md = {**stratum.metadata, **study.general.extra_metadata}

    if isinstance(destination, FlyMessengerDestination):
        md = {**md, "form": destination.initial_shortcode}

        if destination.additional_metadata:
            md = {**md, **destination.additional_metadata}

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

    if isinstance(destination, LeadGenDestination):
        form_id = _get_leadgen_form_id(study, stratum, destination, campaign_state)
        return _create_creative(
            config,
            call_to_action={},  # Not used for lead gen
            lead_gen_form_id=form_id,
        )

    raise Exception(f"destination is not a proper type: {destination}")


def adset_instructions(
    study: StudyConf, state: CampaignState, stratum: Stratum, budget: float
) -> Tuple[AdSet, List[Ad]]:
    stratum_creatives = stratum.creatives

    if isinstance(study.recruitment, DestinationRecruitmentExperiment):
        try:
            destination = next(
                d for d in study.recruitment.destinations if d in state.campaign_name
            )
        except StopIteration:
            raise Exception(
                f"Could not find destination for campaign_name {state.campaign_name}"
                " in recruitment destination experiment."
            )

        stratum_creatives = [
            c for c in stratum_creatives if c.destination == destination
        ]

    destinations = [get_destination_for_creative(study, c) for c in stratum.creatives]

    creatives = [
        create_creative(study, stratum, c, d, state)
        for d, c in zip(destinations, stratum_creatives)
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


def update_campaign(id_, objective) -> Instruction:
    params = {
        "objective": objective,
    }

    return Instruction("campaign", "update", params, id_)


def _collect_form_specs_for_stratum(
    study: StudyConf,
    stratum: Stratum,
) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Pure function to collect all form specs needed for a stratum.
    Returns list of (page_id, base_name, params) tuples.
    """
    dest_lookup = {d.name: d for d in study.destinations}
    form_specs = []

    for creative in stratum.creatives:
        destination = dest_lookup.get(creative.destination)
        if not destination or not isinstance(destination, LeadGenDestination):
            continue

        base_name = make_leadgen_form_base_name(study.id, destination.name, stratum.id)
        form_params = build_leadgen_form_params(destination, stratum, study)
        form_specs.append((destination.page_id, base_name, form_params))

    return form_specs


def check_and_create_forms(
    study: StudyConf,
    state: FacebookState,
    strata: List[Stratum],
) -> List[Instruction]:
    """
    Check if lead gen forms exist for all LeadGen strata.
    Returns Instructions to create/update forms as needed.
    """
    # Collect all form specs from all strata
    all_form_specs = [
        spec
        for stratum in strata
        for spec in _collect_form_specs_for_stratum(study, stratum)
    ]

    # Group by page_id
    page_forms_specs: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for page_id, base_name, params in all_form_specs:
        if page_id not in page_forms_specs:
            page_forms_specs[page_id] = []
        page_forms_specs[page_id].append((base_name, params))

    # For each page, get existing forms and reconcile
    all_instructions = []
    for page_id, form_specs in page_forms_specs.items():
        existing_forms = state.page_forms(page_id)
        instructions = form_dif(existing_forms, form_specs)
        all_instructions.extend(instructions)

    return all_instructions


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

    # TODO: need a way to "reconcile" campaign(s) - including
    # if the objective changes. This is hacky, make a proper reconciliation.
    if campaign_state.campaign["objective"] != study.recruitment.objective:
        return [
            update_campaign(campaign_state.campaign["id"], study.recruitment.objective)
        ]

    # Check and create forms first (new)
    form_instructions = check_and_create_forms(study, state, strata)
    if form_instructions:
        return form_instructions

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
