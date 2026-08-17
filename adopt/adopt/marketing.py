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
from .facebook.reconciliation import adset_dif
from .facebook.state import CampaignState, FacebookState, StateNameError, split
from .facebook.update import Instruction
from .study_conf import (
    AppDestination,
    Audience,
    CreativeConf,
    DestinationConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    FlyWhatsAppDestination,
    LookalikeAudience,
    Stratum,
    StudyConf,
    WebDestination,
)

ADSET_HOURS = 48

# Fallback link for messenger creatives. Facebook requires a link field inside
# object_story_spec.link_data even for click-to-message ads; the CTA value
# determines the actual destination, so this URL is only structural.
MESSENGER_LINK_FALLBACK = "https://fb.com/messenger_doc/"

# Facebook requires link_data.link to match the click-to-WhatsApp CTA. Measured
# working by adopt/scripts/ctwa_probe.py against live ads; do not "tidy" it.
WHATSAPP_LINK = "https://api.whatsapp.com/send"

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

    # Always force Advantage+ Audience off. We never use Advantage+ audience — it
    # imposes constraints (e.g. age_min ≤ 25 as a "control" via individual_setting)
    # that we'd have to remember and validate against. Study confs created before
    # this policy may contain individual_setting copied from the source adset, so
    # we override unconditionally rather than only when the field is missing.
    targeting["targeting_automation"] = {"advantage_audience": 0}


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


def whatsapp_call_to_action() -> dict:
    return {
        "type": "WHATSAPP_MESSAGE",
        "value": {"app_destination": "WHATSAPP"},
    }


def whatsapp_autofill(shortcode: str, ref_md: Optional[Metadata] = None) -> str:
    """The text a click-to-WhatsApp ad prefills into the respondent's compose box.

    Form-first, unlike make_ref. fly's WhatsApp entry pattern anchors on
    `form.`, so make_ref's `creative.`-led output can never match it whatever
    the values are — this is a different serialisation of the same facts, not a
    reuse of one.

    With `ref_md` omitted the token is just `form.<shortcode>`: the default, and
    always parseable. With `ref_md` given (the opt-in full ref) every remaining
    pair is appended; `form` is skipped because it is already the head, so
    parsing the result back yields exactly `ref_md`.

    Values are emitted raw, not quote()d. Percent-encoding would introduce `%`,
    which fly's pattern rejects — and for the values this mode permits (letters,
    digits, underscore, hyphen) quote() is a no-op anyway. What guarantees that
    is StudyConf.check_whatsapp_refs_are_deliverable, at config time.
    """
    s = f"form.{shortcode}"

    for k, v in (ref_md or {}).items():
        if k == "form":
            continue
        s += f".{k}.{v}"

    return s


def make_whatsapp_welcome_message(text: str, autofill: str) -> str:
    """The CTWA welcome screen: greeting text plus the prefilled first message.

    Shape measured against live Meta ads by adopt/scripts/ctwa_probe.py.
    AdCreativeLinkData types page_welcome_message as a string, so this is
    serialised even though Meta's guide prints it unquoted.
    """
    return json.dumps(
        {
            "type": "VISUAL_EDITOR",
            "version": 2,
            "landing_screen_type": "welcome_message",
            "media_type": "text",
            "text_format": {
                "customer_action_type": "autofill_message",
                "message": {
                    "autofill_message": {"content": autofill},
                    "text": text,
                },
            },
        },
        sort_keys=True,
    )


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
    tpd = config.template["object_story_spec"].get("photo_data")
    tvd = config.template["object_story_spec"].get("video_data")

    link_data = None
    video_data = None

    if tld:
        link_data = {
            AdCreativeLinkData.Field.call_to_action: call_to_action,
            AdCreativeLinkData.Field.image_hash: tld["image_hash"],
            AdCreativeLinkData.Field.message: tld.get("message"),
            AdCreativeLinkData.Field.name: tld.get("name"),
            AdCreativeLinkData.Field.description: tld.get("description"),
            # Preserve the link from the template; Facebook requires it for
            # link_data creatives (e.g., click-to-message ads).
            AdCreativeLinkData.Field.link: tld.get("link"),
        }

        # Drop optional keys that were not present in the template so we don't
        # send a bunch of null values.
        link_data = {k: v for k, v in link_data.items() if v is not None}

        if page_welcome_message:
            link_data[
                AdCreativeLinkData.Field.page_welcome_message
            ] = page_welcome_message

        if link:
            link_data[AdCreativeLinkData.Field.link] = link

    elif tpd:
        # Templates created as Instagram photo ads have photo_data instead of
        # link_data. Convert to link_data so the destination-specific CTA can
        # be attached and the required link field is present.
        link_data = {
            AdCreativeLinkData.Field.call_to_action: call_to_action,
            AdCreativeLinkData.Field.image_hash: tpd["image_hash"],
            AdCreativeLinkData.Field.message: tpd.get("caption"),
            AdCreativeLinkData.Field.link: link
            or tpd.get("url")
            or MESSENGER_LINK_FALLBACK,
        }

        if page_welcome_message:
            link_data[
                AdCreativeLinkData.Field.page_welcome_message
            ] = page_welcome_message

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

    object_story_spec = {
        AdCreativeObjectStorySpec.Field.page_id: toss.get("page_id"),
        AdCreativeObjectStorySpec.Field.instagram_user_id: toss.get(
            "instagram_user_id"
        ),
    }

    if link_data is not None:
        object_story_spec[AdCreativeObjectStorySpec.Field.link_data] = link_data
    if video_data is not None:
        object_story_spec[AdCreativeObjectStorySpec.Field.video_data] = video_data

    c[AdCreative.Field.object_story_spec] = object_story_spec

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


def creative_metadata(
    study: StudyConf,
    stratum: Stratum,
    destination: DestinationConf,
) -> Metadata:
    """The metadata dict that make_ref serialises for this (stratum, destination).

    Extracted from create_creative so that the ad -> stratum mapping and the
    ref are computed from one expression and cannot drift apart. The `form`
    key in particular is added here, not in the stratum conf, so anything
    reading `stratum.metadata` directly would silently be missing it.
    """
    md = {**stratum.metadata, **study.general.extra_metadata}

    # Both fly destinations fold in `form`, identically. That keeps the frozen
    # ad_attributions blob consistent across the two channels, so a study using
    # `location: "ad"` reads the same keys whether its respondents arrive by
    # Messenger or by WhatsApp.
    if isinstance(destination, (FlyMessengerDestination, FlyWhatsAppDestination)):
        md = {**md, "form": destination.initial_shortcode}

        if destination.additional_metadata:
            md = {**md, **destination.additional_metadata}

    return md


def ref_metadata(creative_name: str, metadata: Metadata) -> Metadata:
    """The complete key/value set `make_ref(creative_name, metadata)` carries.

    This -- not `stratum.metadata` -- is what gets frozen into
    ad_attributions.metadata. make_ref prepends `creative.<creative_name>`, and
    creative_metadata has already folded in `form` and any additional_metadata,
    so the ref carries strictly more keys than the stratum conf declares.

    Freezing the stratum's metadata instead would silently drop `creative` and
    `form`. Downstream, an extraction conf asking for either would find
    nothing, the stratum would match no one, and the optimizer would quietly
    reallocate budget away from it -- a miscount, not an error. Keep this
    function and make_ref the same shape; test_marketing asserts they are.
    """
    return {"creative": creative_name, **metadata}


def destination_shortcode(destination: DestinationConf) -> Optional[str]:
    """The routing token, where the destination has one.

    Only fly destinations route by shortcode. Web and app destinations encode
    their target in the URL/deeplink template, so they have none, and the
    column is nullable for exactly that reason.
    """
    if isinstance(destination, (FlyMessengerDestination, FlyWhatsAppDestination)):
        return destination.initial_shortcode

    return None


def create_creative(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
) -> AdCreative:
    md = creative_metadata(study, stratum, destination)

    if isinstance(destination, FlyMessengerDestination):
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

    if isinstance(destination, FlyWhatsAppDestination):
        # No url_tags: it was measured not to reach WhatsApp at all. The
        # autofill text is the only carrier, and it is respondent-visible and
        # respondent-editable, which is the other reason the default is the
        # shortcode alone.
        ref_md = (
            ref_metadata(config.name, md)
            if destination.include_metadata_in_ref
            else None
        )
        autofill = whatsapp_autofill(destination.initial_shortcode, ref_md)
        msg = make_whatsapp_welcome_message(destination.welcome_message, autofill)

        return _create_creative(
            config,
            call_to_action=whatsapp_call_to_action(),
            page_welcome_message=msg,
            link=WHATSAPP_LINK,
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


def pair_creatives_with_destinations(
    study: StudyConf, stratum: Stratum, campaign_name: str
) -> List[Tuple[CreativeConf, DestinationConf]]:
    """Pair every creative with the destination its own config names.

    In a destination experiment each campaign is one arm of the experiment,
    so only the creatives assigned to that arm belong in it.

    The pairing is built as tuples rather than by zipping two separately
    derived lists. A previous version filtered the creatives but built the
    destinations from the unfiltered list and let zip() truncate to the
    shorter one, so every arm after the first silently inherited the
    leading arm's destinations. Keeping each creative and its destination
    in a single tuple makes that class of mistake unrepresentable.
    """
    creatives = stratum.creatives

    if isinstance(study.recruitment, DestinationRecruitmentExperiment):
        try:
            destination = next(
                d for d in study.recruitment.destinations if d in campaign_name
            )
        except StopIteration:
            raise Exception(
                f"Could not find destination for campaign_name {campaign_name}"
                " in recruitment destination experiment."
            )

        creatives = [c for c in creatives if c.destination == destination]

    return [(c, get_destination_for_creative(study, c)) for c in creatives]


def ad_provenance(
    study: StudyConf, campaign_name: str, strata: Sequence[Stratum]
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """What vlab knows about every ad it wants to exist, for one campaign.

    Keyed by (adset name, ad name) == (stratum.id, creative.name), which is how
    reconciliation identifies an ad -- adset name is the stratum id
    (create_adset) and ad name is the creative name (create_ad). Reconciliation
    stamps the matching entry onto each ad-create instruction, and
    run_instructions turns it into an ad_attributions row once Facebook returns
    the id.

    Pure: no Graph API, no database. The pairing comes from the same functions
    adset_instructions uses to build the ads themselves, so an ad and its
    provenance can only ever describe the same thing.
    """
    return {
        (stratum.id, config.name): {
            "study_id": study.id,
            "stratum_id": stratum.id,
            "creative_name": config.name,
            "shortcode": destination_shortcode(destination),
            "metadata": ref_metadata(
                config.name, creative_metadata(study, stratum, destination)
            ),
            # The id was handed to us by the ad-create call, so it is an ad id.
            # Recorded rather than assumed so that a row written by some other
            # future path (a WhatsApp referral's source_id, say) is
            # distinguishable from this one without archaeology.
            "resolved_from": "ad_id",
        }
        for stratum in strata
        for config, destination in pair_creatives_with_destinations(
            study, stratum, campaign_name
        )
    }


def template_page_id(config: CreativeConf) -> Optional[str]:
    """The Page an ad posts as, read off the creative template.

    Same source `_create_creative` uses for object_story_spec.page_id, so the
    ad set's promoted_object and the creative can never name different Pages.
    """
    try:
        return config.template["object_story_spec"].get("page_id")
    except (KeyError, TypeError, AttributeError):
        return None


def promoted_object_for(
    config: CreativeConf, destination: DestinationConf
) -> Optional[Dict[str, str]]:
    """What one creative/destination pair needs at the ad set level, or None.

    Facebook requires a promoted_object for app-install and click-to-WhatsApp
    ad sets, and nothing else.
    """
    if isinstance(destination, AppDestination):
        return {
            AdPromotedObject.Field.application_id: destination.facebook_app_id,
            AdPromotedObject.Field.object_store_url: destination.app_install_link,
        }

    if isinstance(destination, FlyWhatsAppDestination):
        page_id = template_page_id(config)
        if not page_id:
            raise Exception(
                f"Creative '{config.name}' targets WhatsApp destination "
                f"'{destination.name}' but its template has no "
                "object_story_spec.page_id. A click-to-WhatsApp ad set's "
                "promoted_object requires the Page id."
            )

        return {
            AdPromotedObject.Field.page_id: page_id,
            AdPromotedObject.Field.whatsapp_phone_number: (
                destination.promoted_phone_number
            ),
        }

    return None


def adset_promoted_object(
    pairs: Sequence[Tuple[CreativeConf, DestinationConf]]
) -> Optional[Dict[str, str]]:
    """The ad set's promoted_object, agreed across all of its creatives.

    promoted_object is an ad set field, but destinations are named per
    creative, so every creative in a stratum has to want the same one. That
    used to be assumed rather than checked: the app branch read
    `destinations[0]` under a standing `# TODO: assert all destinations are the
    same`, so a stratum mixing an app creative with any other kind silently
    published whichever promoted_object happened to sort first — and half its
    ads with the wrong one. planning/click-to-whatsapp-ads.md flags this
    explicitly and says to fix it rather than inherit it.

    Only genuine ambiguity raises. Strata whose creatives all need no
    promoted_object — every Messenger and Web study there is — produce None
    exactly as before, mixed or not, because there is nothing to disagree
    about.
    """
    wanted = [promoted_object_for(c, d) for c, d in pairs]

    distinct = []
    for p in wanted:
        if p not in distinct:
            distinct.append(p)

    if len(distinct) > 1:
        raise Exception(
            "Creatives in one stratum ask for different ad set promoted "
            f"objects: {distinct}. promoted_object is set per ad set, so the "
            "creatives in a stratum must agree — split them into separate "
            "strata, or point them at the same destination."
        )

    return distinct[0] if distinct else None


def adset_instructions(
    study: StudyConf, state: CampaignState, stratum: Stratum, budget: float
) -> Tuple[AdSet, List[Ad]]:
    pairs = pair_creatives_with_destinations(study, stratum, state.campaign_name)

    creatives = [create_creative(study, stratum, c, d) for c, d in pairs]
    promoted_object = adset_promoted_object(pairs)

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
        "is_adset_budget_sharing_enabled": False,
    }

    return Instruction("campaign", "create", params)


def update_campaign(id_, objective) -> Instruction:
    params = {
        "objective": objective,
    }

    return Instruction("campaign", "update", params, id_)


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

    sb = [(s, budget[s.id]) for s in strata]
    new_state = [adset_instructions(study, campaign_state, s, b) for s, b in sb]

    # Built from campaign_state.campaign_name rather than the campaign_name
    # argument so it is derived from exactly the value adset_instructions used
    # to pick each stratum's creatives; in a destination experiment the
    # campaign name selects the arm, so the two must not be able to disagree.
    provenance = ad_provenance(study, campaign_state.campaign_name, strata)

    return adset_dif(campaign_state.campaign_state, new_state, provenance)


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
