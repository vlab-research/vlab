import json
import logging
import random
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

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
from .ref_encoding import encoded_ref, mint_ref_token
from .facebook.reconciliation import adset_dif
from .facebook.state import CampaignState, FacebookState, StateNameError, split
from .facebook.update import Instruction
from .study_conf import (
    InvalidConfigError,
    AppDestination,
    Audience,
    CreativeConf,
    DestinationConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    LookalikeAudience,
    Stratum,
    StudyConf,
    WebDestination,
    destination_type_for,
    ref_value,
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
    """Serialise a creative and its metadata into the dotted ref.

    Every segment goes through ref_value, because every segment is a token in
    the same dot-separated grammar and any of them can carry a `.`.

    The creative name used to be interpolated completely raw, which made it
    both the most exposed contributor and the most damaging one. A dotted
    *value* shifts the pairs after it, so a respondent is mis-attributed. A
    dotted *name* shifts everything after it including `form`, so fly routes
    that respondent into the wrong survey entirely. Study
    `unicef-immunization-kyrg` ran creative names ending `.png` for about nine
    hours in January 2023; timing caught it, nothing else would have.

    Encoding here is a serialisation concern and nothing else:

      - the ad's *name* on Facebook stays the raw creative name (create_ad).
        Reconciliation matches ads by name, so encoding it there would orphan
        every live ad and mint new ids — the ad_attributions-stranding failure.
      - ref_metadata freezes the raw name and raw values. The blob holds truth;
        only transport is encoded.
    """
    s = f"creative.{ref_value(creative_name)}"
    for k, v in metadata.items():
        s += f".{ref_value(k)}.{ref_value(v)}"
    return s


def shortcode_ref(shortcode: str) -> str:
    """The routing prefix a WhatsApp autofill is built on.

    `form` is the one key fly cannot do without — getMetadata falls back to
    FALLBACK_FORM when it is missing — and it is the one thing attribution
    cannot supply later, because routing happens at the first inbound message
    while attribution is a batch join done afterwards.

    Not a ref in its own right. It was one briefly, for a mode that emitted
    routing and nothing else; that mode is gone, because a ref carrying neither
    the stratum nor a token attributes nobody and is not something anyone would
    choose. `whatsapp_autofill` prepends this and appends whatever metadata
    there is, which for an unstratified study is nothing at all.

    Encoded like every other ref token, so a shortcode is transported the same
    way on both channels — on Messenger `form` is an ordinary metadata value
    and already goes through ref_value, and the two must not disagree.
    """
    return f"form.{ref_value(shortcode)}"


def messenger_ref(
    creative_name: str,
    metadata: Metadata,
    destination: Union[FlyMessengerDestination, FlyMultiDestination],
    token: Optional[str] = None,
) -> str:
    """What a Messenger ad puts in `referral.ref`.

    The *only* place the ref mode is allowed to matter. It picks a
    serialisation and nothing else: `metadata` arrives already complete from
    creative_metadata and is passed straight through, because that same dict is
    what ref_metadata freezes into ad_attributions.metadata.

    If this mode ever leaked back into creative_metadata, a shortcode-only
    study would freeze mapping rows containing nothing but `form`, every
    `location: "ad"` conf would resolve to nothing, every stratum would count
    zero, and the optimizer would reallocate on empty data — silently, and
    unrecoverably, because the blob is frozen at creation and never refreshed.
    """
    if destination.resolved_ref_mode == "encoded":
        return encoded_ref(
            destination.initial_shortcode, _require_token(token, destination)
        )

    return make_ref(creative_name, metadata)


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


def _require_token(token: Optional[str], destination) -> str:
    """The token an encoded ref cannot be built without.

    A programming error, not a config error: `ad_ref_token` mints one for every
    destination whose mode is "encoded", so a None here means a call site
    computed the mode and the token differently. Raising beats defaulting --
    there is no safe stand-in, and an ad published with a placeholder token
    would attribute every one of its respondents to the same wrong row.
    """
    if token is None:
        raise ValueError(
            f"Destination '{destination.name}' uses ref_mode='encoded' but no "
            "ref token was supplied; call ad_ref_token() and pass the result."
        )

    return token


def ad_ref_token(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
) -> Optional[str]:
    """The opaque token this ad's ref carries, or None if its mode has none.

    One place, so the ref and the frozen `ad_attributions` row cannot disagree
    about what the token is -- if they did, every respondent from this ad would
    arrive with a token that joins to nothing and be counted unmapped.

    The grain is (study, stratum, creative, destination), which is exactly the
    grain of an ad and therefore of a mapping row.
    """
    if not isinstance(
        destination,
        (FlyMessengerDestination, FlyWhatsAppDestination, FlyMultiDestination),
    ):
        return None

    if destination.resolved_ref_mode != "encoded":
        return None

    return mint_ref_token(study.id, stratum.id, config.name, destination.name)


def whatsapp_ref(
    creative_name: str,
    metadata: Metadata,
    destination: Union[FlyWhatsAppDestination, FlyMultiDestination],
    token: Optional[str] = None,
) -> str:
    """What a click-to-WhatsApp ad prefills, under whichever mode applies.

    The WhatsApp counterpart of `messenger_ref`, and deliberately its mirror:
    one function per channel, each the only place that channel's mode is allowed
    to matter. A multi destination calls both, so its two arms always disclose
    the same amount -- one mode, two grammars.
    """
    if destination.resolved_ref_mode == "encoded":
        return encoded_ref(
            destination.initial_shortcode, _require_token(token, destination)
        )

    return whatsapp_autofill(
        destination.initial_shortcode, ref_metadata(creative_name, metadata)
    )


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

    Every token is encoded with ref_value, the same as on Messenger. This used
    to emit raw values, because the old entry gate rejected `%` outright and
    encoding would have made every value undeliverable. fly widened the gate to
    accept percent-encoded octets (fly@feature/ad-id-attribution 37e1e06e), so
    encoding is now both correct and much less restrictive: of the production
    stratum values on record, 5 of 9 were deliverable raw under the old gate
    and 9 of 9 are deliverable encoded under the new one.

    StudyConf.check_whatsapp_refs_are_deliverable still validates at config
    time, against the encoded form.
    """
    s = shortcode_ref(shortcode)

    for k, v in (ref_md or {}).items():
        if k == "form":
            continue
        s += f".{ref_value(k)}.{ref_value(v)}"

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


def make_multi_welcome_message(
    text: str, button_text: str, ref: str, autofill: str
) -> str:
    """One welcome blob carrying BOTH channels' routing tokens.

    This is the shape the whole multi-destination design rests on, and it is
    measured rather than inferred -- for one of its two arms.

    `page_welcome_message` is a single string field and
    `text_format.customer_action_type` is a scalar, so on the face of it one
    blob can only serve one channel. It does not work that way: on 2026-08-17
    ad 120254903561240150 shipped exactly this structure, with
    customer_action_type set to the scalar "autofill_message", and the Messenger
    arm still delivered its quick-reply payload with the ref intact. Messenger
    reads its own sub-structure and ignores the sibling. Meta also stores both
    halves without stripping either, confirmed by reading the creative back.

    Both sub-structures are mandatory, not belt-and-braces:

      - `quick_replies` is the carrier 68% of Messenger ad entrants route
        through, and their *only* carrier -- they produce no OPEN_THREAD
        referral at all. Drop it and two thirds of the Messenger arm lands on
        FALLBACK_FORM.
      - `autofill_message` is the WhatsApp arm's only carrier of any kind. A
        CTWA referral has no advertiser-settable `ref` field, and url_tags was
        measured not to reach WhatsApp.

    The two tokens are different serialisations of the same facts, deliberately.
    `ref` is Messenger's `creative.`-led, order-free grammar; `autofill` is
    WhatsApp's form-first one, because fly's entry pattern anchors on `form.`
    and make_ref's output can therefore never match it whatever the values are.

    Byte-identical to adopt/scripts/ctwa_probe.py's `welcome_combined`, which is
    what actually produced the measurement above. test_marketing asserts that.
    """
    payload = json.dumps({"referral": {"ref": ref}})

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
                    "quick_replies": [
                        {
                            "content_type": "text",
                            "title": button_text,
                            "payload": payload,
                        }
                    ],
                    "text": text,
                },
            },
        },
        sort_keys=True,
    )


def multi_destination_asset_feed_spec() -> Dict[str, Any]:
    """The array of destinations, which lives on asset_feed_spec and nowhere else.

    Meta's format, from the click-to-multidestination guide:
    `object_story_spec.link_data.call_to_action` stays SINGLE-VALUED as the
    fallback, and a parallel `asset_feed_spec` carries the real array under
    `optimization_type: "DOF_MESSAGING_DESTINATION"`. There is no list-valued
    destination field anywhere -- the ad set's destination_type is a single
    combination token, and the creative's destinations must match it.

    `DOF_MESSAGING_DESTINATION` is absent from the AdAssetFeedSpec reference's
    optimization_type enum even though the guide requires it; the reference is
    stale relative to the guide. Do not be alarmed, and do not expect the SDK's
    typed constants to carry it.

    The links are structural: AdCreativeLinkData requires link_data.link to
    match its CTA, and Meta's own sample uses exactly these two URLs.
    MESSENGER_LINK_FALLBACK already *is* the link from that sample.
    """
    return {
        "optimization_type": "DOF_MESSAGING_DESTINATION",
        "call_to_actions": [
            {
                "type": "MESSAGE_PAGE",
                "value": {
                    "app_destination": "MESSENGER",
                    "link": MESSENGER_LINK_FALLBACK,
                },
            },
            {
                "type": "WHATSAPP_MESSAGE",
                "value": {
                    "app_destination": "WHATSAPP",
                    "link": WHATSAPP_LINK,
                },
            },
        ],
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
    asset_feed_spec: Dict[str, Any] | None = None,
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

    template_afs = config.template.get(AdCreative.Field.asset_feed_spec)

    # An injected asset_feed_spec (multi-destination's call_to_actions array)
    # REPLACES the template's rather than merging with it, and refuses to run
    # over a template that has one. Merging would mean silently rewriting the
    # template's `optimization_type` -- asset_feed_spec has exactly one, and
    # DOF_MESSAGING_DESTINATION is not the one an Advantage+ creative template
    # carries -- which would change what respondents see while looking like a
    # destination change. There is no way to know from here which the operator
    # wanted, so say so instead of guessing.
    if asset_feed_spec is not None and template_afs:
        raise Exception(
            f"Creative '{config.name}' needs a multi-destination asset_feed_spec, "
            "but its template already carries one. asset_feed_spec holds a "
            "single optimization_type, so the two cannot both apply: using the "
            "template's would drop the destination array and the ad would only "
            "ever open Messenger, and overriding it would silently discard the "
            "template's creative variants. Use a template without an "
            "asset_feed_spec for multi-destination creatives."
        )

    tafs = asset_feed_spec if asset_feed_spec is not None else template_afs

    if tafs:
        c[AdCreative.Field.asset_feed_spec] = tafs

        if page_welcome_message:
            c[AdCreative.Field.asset_feed_spec]["additional_data"] = {
                "page_welcome_message": page_welcome_message
            }

        if link:
            c[AdCreative.Field.asset_feed_spec]["link_urls"] = [
                {**url, "website_url": link} for url in tafs["link_urls"]
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

    # Every fly destination folds in `form`, identically. That keeps the frozen
    # ad_attributions blob consistent across channels, so a study using
    # `location: "ad"` reads the same keys whether its respondents arrive by
    # Messenger or by WhatsApp -- and, on a multi ad, whichever arm Meta chose
    # for them. One ad, one ad id, one frozen blob: the blob cannot depend on a
    # channel that is only decided at click time.
    if isinstance(
        destination,
        (FlyMessengerDestination, FlyWhatsAppDestination, FlyMultiDestination),
    ):
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
    if isinstance(
        destination,
        (FlyMessengerDestination, FlyWhatsAppDestination, FlyMultiDestination),
    ):
        return destination.initial_shortcode

    return None


def create_creative(
    study: StudyConf,
    stratum: Stratum,
    config: CreativeConf,
    destination: DestinationConf,
) -> AdCreative:
    md = creative_metadata(study, stratum, destination)

    # Minted once per ad and threaded into every carrier below, so a multi
    # destination's Messenger and WhatsApp arms cannot end up with different
    # tokens -- that would be one ad, two mapping identities, and half its
    # respondents attributed to a row that does not exist.
    token = ad_ref_token(study, stratum, config, destination)

    if isinstance(destination, FlyMessengerDestination):
        # One ref, both carriers. Messenger ships it twice — as url_tags, which
        # Meta surfaces as referral.ref, and inside the welcome message's
        # quick-reply payload — and a respondent can arrive by either. Emitting
        # different refs on the two paths would mean the same ad describing two
        # different people depending on how they tapped it.
        ref = messenger_ref(config.name, md, destination, token)
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
        autofill = whatsapp_ref(config.name, md, destination, token)
        msg = make_whatsapp_welcome_message(destination.welcome_message, autofill)

        return _create_creative(
            config,
            call_to_action=whatsapp_call_to_action(),
            page_welcome_message=msg,
            link=WHATSAPP_LINK,
        )

    if isinstance(destination, FlyMultiDestination):
        # Three carriers on one creative, because a multi ad has to satisfy two
        # channels that read different fields and one of them reads two:
        #
        #   url_tags            -> Messenger's referral.ref (32% of entrants)
        #   quick_replies       -> Messenger's quick-reply payload (68%, and
        #                          their only carrier)
        #   autofill_message    -> WhatsApp's compose-box prefill (its only
        #                          carrier of any kind)
        #
        # The first two carry the same Messenger-grammar token, for the same
        # reason the Messenger branch ships it twice: a respondent can arrive by
        # either, and emitting different refs would mean one ad describing two
        # different people depending on how they tapped it. The third carries
        # the same facts in WhatsApp's form-first grammar.
        #
        # `messenger_ref` and `whatsapp_autofill` are reused rather than
        # reimplemented. They differ deliberately -- WhatsApp's entry pattern
        # anchors on `form.` while make_ref leads with `creative.`, so make_ref
        # output can never match it -- and one ref mode drives both, so the two
        # arms of a single ad always agree about how much they disclose.
        ref = messenger_ref(config.name, md, destination, token)
        autofill = whatsapp_ref(config.name, md, destination, token)

        msg = make_multi_welcome_message(
            destination.welcome_message, destination.button_text, ref, autofill
        )

        # The single-valued CTA stays MESSAGE_PAGE as Meta's documented
        # fallback; asset_feed_spec carries the actual destination array.
        return _create_creative(
            config,
            call_to_action=messenger_call_to_action(),
            page_welcome_message=msg,
            url_tags=f"ref={ref}",
            asset_feed_spec=multi_destination_asset_feed_spec(),
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
    provenance = {
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
            # None for every mode but "encoded". Nullable rather than absent so
            # the column means "this ad's ref carries no token", which is a fact
            # about the ad, not a gap in the record.
            "ref_token": ad_ref_token(study, stratum, config, destination),
        }
        for stratum in strata
        for config, destination in pair_creatives_with_destinations(
            study, stratum, campaign_name
        )
    }

    assert_ref_tokens_unique(provenance)

    return provenance


def assert_ref_tokens_unique(provenance: Dict[Tuple[str, str], Dict[str, Any]]) -> None:
    """Refuse to publish a campaign whose ads share a ref token.

    A collision means two ads mint the same join key, so every respondent from
    either is attributed to whichever mapping row was written second. That is a
    wrong answer rather than a missing one: the strata still count, they just
    count the wrong people, and nothing downstream can detect it -- the token
    resolves, so it is not "unmapped", and the numbers look plausible.

    Raising here, at instruction-generation time, is the last moment it is
    cheap. Past this point the ads exist on Facebook and are spending money.

    Two things can cause it, and both are worth a loud failure: a genuine
    40-bit digest collision (vanishingly unlikely -- see REF_TOKEN_BYTES), or
    two ads whose (study, stratum, creative, destination) tuples are actually
    identical, which is a duplicate ad and a config bug in its own right.
    """
    seen: Dict[str, List[Tuple[str, str]]] = {}

    for key, row in provenance.items():
        token = row.get("ref_token")

        if token is not None:
            seen.setdefault(token, []).append(key)

    collisions = {t: keys for t, keys in seen.items() if len(keys) > 1}

    if collisions:
        detail = "; ".join(
            f"{token} shared by {sorted(keys)}" for token, keys in sorted(collisions.items())
        )
        raise InvalidConfigError(
            f"Ref token collision -- two ads would mint the same attribution "
            f"key, so their respondents would be indistinguishable: {detail}"
        )


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

    # Multi needs the same promoted_object as WhatsApp: its WhatsApp arm is a
    # click-to-WhatsApp ad, and Meta will not accept the ad set without a Page
    # and a number, whichever arm a given respondent ends up on.
    if isinstance(destination, (FlyWhatsAppDestination, FlyMultiDestination)):
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
    same`, so a stratum mixing an app creative with any other kind took whatever
    its first creative happened to want and published the rest of its ads under
    the wrong promoted object, silently.
    planning/click-to-whatsapp-ads.md flags this and says to fix it rather than
    inherit it.

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


def adset_destination_type(
    pairs: Sequence[Tuple[CreativeConf, DestinationConf]],
    recruitment_default: str,
) -> str:
    """The ad set's destination_type, agreed across all of its creatives.

    The counterpart of `adset_promoted_object`, and it exists for the same
    reason: destination_type is an ad-set field while destinations are named per
    creative, so channel is necessarily uniform within a stratum and something
    has to enforce agreement.

    Before this, `destination_type` was one string on the recruitment conf
    consumed by every ad set of every arm. Two things followed. A study could
    not have a Messenger arm and a WhatsApp arm in a
    DestinationRecruitmentExperiment -- setting MESSAGING_MESSENGER_WHATSAPP
    made *both* arms multi-destination and destroyed the experiment by handing
    channel assignment to Meta. And a study whose destination_type disagreed
    with its destinations built happily and misrouted silently.

    Destinations that imply nothing (Web, App) fall through to the recruitment
    conf's value, which is what keeps every existing study byte-identical: the
    110 studies whose recruitment conf says MESSENGER have Messenger
    destinations that derive MESSENGER anyway, and the 5 that say WEB or WEBSITE
    have destinations that imply nothing and so keep their stored value
    verbatim. Measured against production study_confs on 2026-08-17.

    Note what this does *not* enable, because someone will ask: a running study
    still cannot change channel. `destination_type` is absent from
    field_contract.COMPARED_ADSET, so it rides only on ad-set creates, and ad
    sets are matched by name where the name is the stratum id. The value here is
    what a *new* ad set gets.
    """
    wanted = [destination_type_for(d) for _, d in pairs]

    distinct = []
    for t in wanted:
        if t is not None and t not in distinct:
            distinct.append(t)

    if len(distinct) > 1:
        raise Exception(
            "Creatives in one stratum ask for different ad set destination "
            f"types: {distinct}. destination_type is set per ad set, so the "
            "creatives in a stratum must agree — split them into separate "
            "strata, or use a multi-destination destination if you want one ad "
            "to open either channel. Note that a multi-destination ad lets Meta "
            "choose the channel per respondent, so it cannot be used to "
            "randomise channel."
        )

    return distinct[0] if distinct else recruitment_default


def adset_instructions(
    study: StudyConf, state: CampaignState, stratum: Stratum, budget: float
) -> Tuple[AdSet, List[Ad]]:
    pairs = pair_creatives_with_destinations(study, stratum, state.campaign_name)

    creatives = [create_creative(study, stratum, c, d) for c, d in pairs]
    promoted_object = adset_promoted_object(pairs)
    destination_type = adset_destination_type(pairs, study.recruitment.destination_type)

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
        destination_type,
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
