"""Build the PAUSED Meta objects a study's configuration is derived from.

A vlab study is configured *from* a template campaign: the Variables form reads
`facebook_targeting` off its ad sets (`authoring.extract.extract_from_adset`)
and the Creatives form reads the creative blob off its ads
(`GET /{org}/meta/ads`, stored verbatim as `creatives[].template`). adopt then
builds the study's real campaign, ad sets and ads from the study conf. The
template itself is never delivered, never activated, and never read at run time
by name -- `Level.template_campaign` / `Level.template_adset` are authoring-time
provenance, nothing more.

Until now a researcher had to build all of that by hand in Ads Manager, which
an agent cannot do, and which is where every load-bearing Meta quirk below was
learned the hard way. This module is the library form of
`adopt/scripts/make_template_campaign.py` (untracked, superseded by this file)
plus the creative half that script never had, and every comment marked
"MEASURED" is lifted from it or from `adopt/scripts/ctwa_probe.py` with the
date the measurement was taken.

    plan = plan_template_campaign(
        account_id="act_1342820622846299",
        name="VL Pulse Nigeria",
        adsets=[AdsetSpec(name="Kwara - Men", targeting=t, ...)],
        ads=[AdSpec(name="vlpulse-ng-1", kind="messenger", page_id=..., ...)],
    )
    print(json.dumps(plan.to_dict(), indent=2))   # a dry run IS the plan
    result = apply(plan, api)                     # only now does anything exist

WHY PLAN / APPLY, AND WHY DRY RUN IS THE DEFAULT

`plan_template_campaign` is pure: no sockets, no clock, no randomness. It
returns the exact Graph calls that would be made, as data, so an agent (or a
reviewer, or a test) can read what is about to be created on someone's ad
account before a single byte leaves the machine. Everything that can be checked
without Meta is checked here -- the declared-property contract, the budget
ceiling, the PAUSED invariant, whether the creative kind and the ad set's
`destination_type` agree -- so the failure lands in the plan rather than four
objects into an apply, leaving debris nobody asked for.

SAFETY, AND THE LIMITS OF IT

Everything is created `PAUSED` and nothing here can transition anything to
ACTIVE: `status` is not a caller-supplied field, it is a constant. Budgets are
capped at `MAX_DAILY_BUDGET` and are unchargeable while the campaign is paused
in any case. `delete_template_campaign` refuses any campaign that does not
carry the template marker, and `apply` refuses to add ads to one. What this
CANNOT protect against is a human activating the campaign afterwards in Ads
Manager; the marker in the name is there to make that obviously wrong.

**Nothing in this module has been run against live Meta.** It reproduces shapes
that were measured live by the script and the probe, and every test mocks
`FacebookAdsApi.call`. Treat the first live run as an experiment; see
`planning/template-authoring.md` "Known gaps".
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..meta_fields import CREATIVE_FIELDS, REQUIRED_TEMPLATE_CREATIVE_FIELDS
from ..study_conf import (
    APP_DESTINATION_TYPE,
    MESSENGER_DESTINATION_TYPE,
    MULTI_DESTINATION_TYPE,
    WEB_DESTINATION_TYPE,
    WHATSAPP_DESTINATION_TYPE,
)
from .extract import PropertyMissingError, extract_from_adset

__all__ = [
    "TemplateError",
    "TemplatePlanError",
    "TemplateApplyError",
    "AdsetSpec",
    "AdSpec",
    "Create",
    "TemplatePlan",
    "TemplateResult",
    "CREATIVE_KINDS",
    "TEMPLATE_CAMPAIGN_PREFIX",
    "MAX_DAILY_BUDGET",
    "DEFAULT_PROPERTIES",
    "template_campaign_name",
    "is_template_campaign",
    "build_creative",
    "plan_template_campaign",
    "plan_template_ads",
    "apply",
    "find_campaign_by_name",
    "delete_template_campaign",
    "validate_targeting",
    "meta_message",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def _marketing():
    """`adopt.marketing`, imported on use rather than at module load.

    `marketing` imports `budget`, which imports cvxpy: **1.4 seconds**,
    measured. `adopt.sdk.cli` registers the `vlab template` group at import
    time, so a module-level import here would put that 1.4s in front of EVERY
    `vlab` command -- `vlab validate` included, whose entire selling point is
    that it is instant and offline.

    This is not a copy of anything. `marketing` remains the single definition
    of what a vlab call-to-action, structural link and multi-destination
    asset_feed_spec are (plan §7, "one implementation"); all that moves is WHEN
    it is read. Everything the planner does before a creative is built --
    including the whole of `plan_template_campaign` for a campaign with no ads
    -- costs nothing.
    """
    from .. import marketing

    return marketing


class TemplateError(Exception):
    """Common base, so a caller can catch everything from this module.

    An `Exception`, not a `BaseException`, for the reason `extract.ExtractError`
    gives: a `BaseException` walks past every `except Exception` in the service
    and past the CLI's own handler, so a config problem reaches the user as a
    traceback with the careful message only in a log.
    """


class TemplatePlanError(TemplateError):
    """The plan cannot be built. Nothing was sent to Meta; nothing exists."""


class TemplateApplyError(TemplateError):
    """The plan was refused, or Meta refused part of it. See the message."""


# ---------------------------------------------------------------------------
# The marker: how a template campaign is recognisable
# ---------------------------------------------------------------------------

# A campaign this module created, or will delete, carries this name prefix.
#
# WHY THE NAME AND NOT AN AD LABEL. Both were on the table. An ad label is a
# separate Graph object (`/act_x/adlabels`) that has to be created, referenced
# by id on every child, and read back with an extra field expansion -- three
# more failure modes -- and it is invisible in the one place a human looks,
# which is the campaign list in Ads Manager. The prefix is visible there, it is
# already the convention on the production account (`Templates - VapeFree`,
# `Templates - Shujaaz - Free2Choose`, read off the account 2026-08-27), and it
# is readable through `GET /{org}/meta/campaigns`, whose `fields` is `name,id`
# and carries no labels. The cost is that a human can rename a campaign out of
# (or into) the marker; that is accepted, and `delete_template_campaign` says
# so when it refuses.
TEMPLATE_CAMPAIGN_PREFIX = "Templates - "

# Cents per day. A paused campaign with paused ad sets cannot be charged, so
# this is not a spend control -- it is a guard against a typo (`200000` for
# `2000`) becoming a real budget the moment somebody activates the campaign by
# hand. 2000 mirrors the live `Templates - VapeFree` ad sets; the ceiling is
# five times that, which is comfortably above any template and far below
# anything that would matter.
DEFAULT_DAILY_BUDGET = 2_000
MAX_DAILY_BUDGET = 10_000

# PAUSED, everywhere, always. Deliberately a module constant referenced by the
# builders rather than a parameter with a default: a default can be overridden,
# and there is no legitimate reason for this module to create a delivering
# object. See the module docstring.
PAUSED = "PAUSED"

# Mirrors `Templates - VapeFree` (120227642396520150), read off the account
# 2026-08-27, so the shape is one Meta already accepts on this ad account
# rather than one assembled from the reference docs.
DEFAULT_OBJECTIVE = "OUTCOME_ENGAGEMENT"
DEFAULT_OPTIMIZATION_GOAL = "CONVERSATIONS"
DEFAULT_BILLING_EVENT = "IMPRESSIONS"
DEFAULT_BID_STRATEGY = "LOWEST_COST_WITHOUT_CAP"

# The targeting properties a variable built on these ad sets should declare.
#
# `targeting_automation` IS SET ON THE AD SETS AND IS NOT IN THIS LIST, which
# corrects `make_template_campaign.py`, whose docstring says it "has to be set
# and has to be declared". The first half is still true and matters (Meta's
# Advantage audience expansion is ON by default and leaks delivery outside the
# stratum being measured). The second half is not true any more, and is now
# actively harmful:
#
#   * `extract_from_adset` FORCES `targeting_automation = {"advantage_audience": 0}`
#     onto every extraction regardless of what was declared or what the source
#     ad set held (extract.py, "Always force Advantage+ Audience off"). So
#     declaring it buys nothing -- the study's ad sets get it either way.
#   * `diff_property_keys` strips `targeting_automation` from the STORED key set
#     and not from the current property list (plan §12.3 item 4, a faithfully
#     ported TypeScript bug). A variable that declares it therefore shows the
#     dashboard's two-line "properties drifted" banner forever, with nothing a
#     researcher can do about it.
#
# It is still set on the ad set below, because a template is also read by
# humans and an ad set that says it does not use Advantage audience is the
# honest artifact.
DEFAULT_PROPERTIES: Tuple[str, ...] = (
    "genders",
    "age_min",
    "age_max",
    "geo_locations",
)

# The five destination kinds vlab supports, named exactly as `DestinationConf`
# discriminates them (`study_conf.py`), minus web's second legacy spelling.
MESSENGER = "messenger"
WHATSAPP = "whatsapp"
MULTI = "multi"
WEB = "web"
APP = "app"

CREATIVE_KINDS: Tuple[str, ...] = (MESSENGER, WHATSAPP, MULTI, WEB, APP)

# The ad set `destination_type` each creative kind belongs with. Not a second
# definition of `study_conf.destination_type_for` -- it is the same constants,
# keyed by the conf's own `type` discriminator, because a plan has a kind
# string and not a `DestinationConf` instance. `test_templates.py` asserts the
# two agree for every destination class, so they cannot drift.
DESTINATION_TYPE_BY_KIND: Mapping[str, str] = {
    MESSENGER: MESSENGER_DESTINATION_TYPE,
    WHATSAPP: WHATSAPP_DESTINATION_TYPE,
    MULTI: MULTI_DESTINATION_TYPE,
    WEB: WEB_DESTINATION_TYPE,
    APP: APP_DESTINATION_TYPE,
}

# The kinds whose creative states a messaging destination, and the single-entry
# `asset_feed_spec` that states it. See `build_creative`'s `declare_destination`.
MESSAGING_KINDS = (MESSENGER, WHATSAPP, MULTI)


# ---------------------------------------------------------------------------
# The marker helpers
# ---------------------------------------------------------------------------


def template_campaign_name(name: str) -> str:
    """`name` with the template marker, added if it is not already there.

    Normalising rather than rejecting an unprefixed name: the marker is what
    makes `delete_template_campaign` safe, so a campaign this module creates
    must carry it by construction and not by the caller remembering. The plan
    prints the final name, so nothing is hidden.
    """
    name = (name or "").strip()
    if not name:
        raise TemplatePlanError("A template campaign needs a name.")
    if is_template_campaign(name):
        return name
    return f"{TEMPLATE_CAMPAIGN_PREFIX}{name}"


def is_template_campaign(name: Optional[str]) -> bool:
    return bool(name) and str(name).startswith(TEMPLATE_CAMPAIGN_PREFIX)


# ---------------------------------------------------------------------------
# The creative builder
# ---------------------------------------------------------------------------


def _single_destination_asset_feed_spec(kind: str) -> Dict[str, Any]:
    """The one-entry sibling of `marketing.multi_destination_asset_feed_spec`.

    A click-to-messaging ad built in Ads Manager already carries a
    `DOF_MESSAGING_DESTINATION` `asset_feed_spec` naming its one app -- that is
    stated in `refuse_template_destination_conflicts`, which had to be narrowed
    in 2026-08 precisely because it was refusing those ordinary templates. So
    emitting one here is reproducing what the UI produces, not inventing a
    shape.

    It is what makes a template SAY what it is for. Without it, a Messenger
    template and a WhatsApp template are indistinguishable to
    `refuse_template_destination_conflicts` (`have` is empty, so it returns
    early), and pointing a creative at the wrong one is caught by nothing --
    the runtime overrides the CTA and the link per destination, so the ad it
    ships is *correct* but is not the ad the researcher was looking at. With
    it, the mismatch is refused by name at plan time.

    Structurally identical to the multi spec, one entry instead of two, and the
    same links: `AdCreativeLinkData` requires `link_data.link` to match its
    CTA, and these two URLs are Meta's own sample values
    (`MESSENGER_LINK_FALLBACK`, `WHATSAPP_LINK`).
    """
    m = _marketing()
    if kind == MULTI:
        return m.multi_destination_asset_feed_spec()

    cta = {
        MESSENGER: {
            "type": "MESSAGE_PAGE",
            "value": {
                "app_destination": "MESSENGER",
                "link": m.MESSENGER_LINK_FALLBACK,
            },
        },
        WHATSAPP: {
            "type": "WHATSAPP_MESSAGE",
            "value": {"app_destination": "WHATSAPP", "link": m.WHATSAPP_LINK},
        },
    }[kind]

    return {"optimization_type": m.MULTI_OPTIMIZATION_TYPE, "call_to_actions": [cta]}


def _call_to_action_for(kind: str, link: Optional[str], deeplink: Optional[str]):
    """The creative's single-valued CTA, from the runtime's own builders.

    Imported rather than restated: `marketing` is what constructs these on the
    study's real ads, and a template whose CTA disagreed with the runtime's
    would be a template that looks right in Ads Manager and ships something
    else. Multi takes MESSAGE_PAGE, which is Meta's documented fallback while
    `asset_feed_spec` carries the real array (`create_creative`, multi branch).
    """
    m = _marketing()
    if kind in (MESSENGER, MULTI):
        return m.messenger_call_to_action()
    if kind == WHATSAPP:
        return m.whatsapp_call_to_action()
    if kind == WEB:
        return m.web_call_to_action(link)
    if kind == APP:
        return m.app_download_call_to_action(deeplink)
    raise TemplatePlanError(f"Unknown creative kind {kind!r}.")


def _structural_link(kind: str, link: Optional[str]) -> str:
    """`object_story_spec.link_data.link`, which Meta requires even when the
    CTA is what actually routes the click.

    Messaging kinds get the structural constant the runtime uses, so that a
    template and the ad built from it carry the same value and reconciliation
    sees no drift. Web and app get the caller's URL.
    """
    m = _marketing()
    if kind == WHATSAPP:
        return m.WHATSAPP_LINK
    if kind in (MESSENGER, MULTI):
        return m.MESSENGER_LINK_FALLBACK
    if not link:
        raise TemplatePlanError(
            f"A {kind!r} creative needs a link: it is the ad's destination, and "
            "Meta requires object_story_spec.link_data.link on every link_data "
            "creative."
        )
    return link


def build_creative(
    kind: str,
    *,
    name: str,
    page_id: str,
    message: str,
    headline: Optional[str] = None,
    description: Optional[str] = None,
    image_hash: Optional[str] = None,
    video_id: Optional[str] = None,
    instagram_user_id: Optional[str] = None,
    link: Optional[str] = None,
    deeplink: Optional[str] = None,
    declare_destination: bool = True,
) -> Dict[str, Any]:
    """The `POST /act_<id>/adcreatives` body for one template creative.

    Pure. `image_hash` is the hash of an already-uploaded image (`apply`
    substitutes one for a planned upload); `video_id` is an existing Meta video
    id. Exactly one of the two is required, because Meta has no creative with
    neither and `_create_creative` reads `link_data` xor `video_data`.

    WHAT THE RUNTIME DOES WITH WHAT THIS PRODUCES -- the reason each field is
    here, from `marketing._create_creative` (the only reader):

    | this builds | the runtime does |
    |---|---|
    | `object_story_spec.page_id` | copied verbatim; also the ad set's
      `promoted_object.page_id` for WhatsApp/multi (`template_page_id`) |
    | `object_story_spec.instagram_user_id` | copied verbatim |
    | `link_data.image_hash` / `message` / `name` / `description` | copied verbatim |
    | `video_data.image_hash` / `message` / `title` / `video_id` | copied verbatim |
    | `link_data.call_to_action` | **overridden** per destination |
    | `link_data.link` | **overridden** for web/app; kept for messaging |
    | `page_welcome_message` | **injected**, carrying the ref |
    | `url_tags` | **injected**, carrying the ref |
    | `asset_feed_spec.optimization_type` / `call_to_actions` | copied for
      single-destination, **replaced** for multi |

    So the copy is the researcher's and the destination is the study conf's,
    which is exactly the split `planning/creative-construction-contract.md`
    argues for. Building a template that STATES a destination is still worth
    doing, and that is `declare_destination`.

    :param kind: one of `CREATIVE_KINDS`.
    :param name: the creative's name. **A join key, not a label** -- vlab's ad
        name is the creative name, `mint_ref_token` is keyed on it, and
        reconciliation matches ads by it. Changing it later deletes an ad and
        creates another with a new attribution row
        (`planning/encoded-ref-probe-runbook.md` §3.5). Name it once.
    :param headline: `link_data.name` on an image creative, `video_data.title`
        on a video one. Meta calls it the headline in Ads Manager; the API
        calls it three different things.
    :param declare_destination: emit the messaging `asset_feed_spec` described
        in `_single_destination_asset_feed_spec`. Ignored for web and app,
        which state no messaging destination at all -- an omission with a real
        consequence, recorded in `planning/template-authoring.md`.
    """
    if kind not in CREATIVE_KINDS:
        raise TemplatePlanError(
            f"Unknown creative kind {kind!r}. One of: {', '.join(CREATIVE_KINDS)}."
        )
    if not page_id:
        raise TemplatePlanError(
            f"Creative {name!r}: page_id is required. It is the Page the ad "
            "posts as, it becomes the creative's actor_id (which "
            "audiences.py reads with a bare `template['actor_id']`), and for "
            "WhatsApp and multi it is also the ad set's promoted_object."
        )
    if not image_hash:
        # An image is required in BOTH shapes: on its own it is the ad, and
        # alongside a `video_id` it is the video's thumbnail, which is what
        # `AdCreativeVideoData.image_hash` means and what Meta requires
        # (video_data takes image_hash or image_url).
        #
        # This used to be an xor -- image OR video, never both -- which review
        # caught, and it was the wrong shape for a reason worth keeping: it
        # made a video creative that could not carry a thumbnail, and
        # `_create_creative`'s video branch copies its four fields with
        # `tvd.get(k)` and NO None filter (marketing.py ~905), so such a
        # template deployed `video_data: {image_hash: None, title: None, ...}`.
        # Nobody had hit it because an Ads-Manager video template always has
        # both. Required here rather than filtered there: the runtime code is
        # pre-existing and shared with every hand-built template, and a
        # template that cannot deploy should fail while someone is still
        # looking at it.
        raise TemplatePlanError(
            f"Creative {name!r}: an image is required — as the ad's image, or "
            "as the video's thumbnail when `video_id` is given. Meta's "
            "video_data needs image_hash or image_url, and _create_creative "
            "copies image_hash unconditionally, so a video template without "
            "one deploys `image_hash: null`."
        )
    if video_id and not headline:
        # Same reason: `_create_creative` copies `title` with no None filter,
        # so a video template with no headline deploys `title: null`.
        raise TemplatePlanError(
            f"Creative {name!r}: a video creative needs a headline. It becomes "
            "video_data.title, which _create_creative copies unconditionally, "
            "so leaving it off deploys `title: null` rather than omitting it."
        )
    if kind == APP and not deeplink:
        raise TemplatePlanError(
            f"Creative {name!r}: an app creative needs a deeplink for its "
            "INSTALL_MOBILE_APP call_to_action."
        )
    if kind in (WEB, APP) and not link:
        # Checked HERE and not only in `_structural_link`, which review caught:
        # `_structural_link` is called from the link_data branch alone, so a
        # web VIDEO creative with no link sailed through the plan and shipped
        # `call_to_action.value.link = null` -- rejected by Meta at
        # `POST /adcreatives`, after the campaign and its ad sets already
        # exist, which is the exact failure plan-time checks are for.
        raise TemplatePlanError(
            f"Creative {name!r}: a {kind!r} creative needs a link. It is the "
            "ad's destination, it is what the call_to_action carries, and for "
            "an image creative Meta additionally requires it as "
            "object_story_spec.link_data.link."
        )

    call_to_action = _call_to_action_for(kind, link, deeplink)

    story: Dict[str, Any] = {"page_id": str(page_id)}
    if instagram_user_id:
        story["instagram_user_id"] = str(instagram_user_id)

    if video_id:
        # `title`, not `name`: AdCreativeVideoData spells the headline
        # differently from AdCreativeLinkData, and `_create_creative` copies
        # exactly `image_hash, message, title, video_id`. A `description` has
        # nowhere to go on a video creative, so it is refused rather than
        # silently dropped.
        if description:
            raise TemplatePlanError(
                f"Creative {name!r}: a video creative has no description field "
                "(_create_creative copies image_hash, message, title and "
                "video_id only). Put it in the message."
            )
        # All four of `_create_creative`'s copied fields are present, and are
        # required above rather than conditional here -- that function copies
        # them with `tvd.get(k)` and no None filter, so an absent key becomes
        # a null on the deployed ad rather than an omission.
        story["video_data"] = {
            "video_id": str(video_id),
            "image_hash": image_hash,
            "title": headline,
            "message": message,
            "call_to_action": call_to_action,
        }
    else:
        link_data: Dict[str, Any] = {
            "image_hash": image_hash,
            "message": message,
            "link": _structural_link(kind, link),
            "call_to_action": call_to_action,
        }
        if headline:
            link_data["name"] = headline
        if description:
            link_data["description"] = description
        story["link_data"] = link_data

    creative: Dict[str, Any] = {"name": name, "object_story_spec": story}

    if declare_destination and kind in MESSAGING_KINDS:
        creative["asset_feed_spec"] = _single_destination_asset_feed_spec(kind)

    return creative


# ---------------------------------------------------------------------------
# Specs -- what a caller describes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdsetSpec:
    """One template ad set: a targeting combination a study may stratify on.

    `targeting` is an arbitrary Meta targeting dict, deliberately. The caller
    may hand-build it, or get one from `authoring.geo.location_levels`, or lift
    one off an existing ad set; this module composes with all three and
    validates the result rather than owning a targeting DSL of its own.
    """

    name: str
    targeting: Dict[str, Any]
    kind: str = MESSENGER
    daily_budget: int = DEFAULT_DAILY_BUDGET
    optimization_goal: str = DEFAULT_OPTIMIZATION_GOAL
    billing_event: str = DEFAULT_BILLING_EVENT
    bid_strategy: str = DEFAULT_BID_STRATEGY
    # For WhatsApp and multi this must carry `page_id` (and normally
    # `whatsapp_phone_number`); for app, `application_id` and
    # `object_store_url`. `plan_template_campaign` fills the page in from the
    # ads it is planning when it can, and says so when it cannot.
    promoted_object: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AdSpec:
    """One template ad, and the creative it carries.

    `image` is a path on this machine, uploaded by `apply` and substituted for
    `image_hash`; `image_hash` is one already on the account. Exactly one of
    the two is required -- **including for a video**, where it is the
    thumbnail (`video_data.image_hash`) and a video also requires a
    `headline`; see `build_creative`. `adset` names which planned ad set the ad
    hangs on, defaulting to the first.
    """

    name: str
    kind: str
    page_id: str
    message: str
    headline: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    image_hash: Optional[str] = None
    video_id: Optional[str] = None
    instagram_user_id: Optional[str] = None
    link: Optional[str] = None
    deeplink: Optional[str] = None
    adset: Optional[str] = None
    declare_destination: bool = True


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


# A create's `params` may reference an earlier create's result by this
# placeholder syntax, substituted by `apply` once that create has an id. A
# plain string rather than an object so that a plan is JSON, byte for byte, and
# a caller can diff two plans or commit one.
#
# The substituted value is an id for a campaign / ad set / creative and the
# image HASH for an image, because a hash is what a creative references. That
# asymmetry is the only thing about the syntax worth remembering.
#
# WHY THE `vlab:` PREFIX. `_substitute` walks every string in a create's params,
# and those params include the researcher's own ad copy. A bare `${...}` syntax
# would mean a message reading exactly "${discount}" was either substituted or
# -- because an unknown ref is treated as a planner bug -- a hard error at apply
# time on an ad that was fine. Namespacing the placeholder makes a collision
# require a message that is exactly `${vlab:<a ref this plan defines>}`, and
# lets the unknown-ref guard stay a hard error, which is what catches a real
# planner bug.
PLACEHOLDER_PREFIX = "${vlab:"


def ref_placeholder(ref: str) -> str:
    return PLACEHOLDER_PREFIX + ref + "}"


@dataclass(frozen=True)
class Create:
    """One `POST /act_<id>/<edge>` (or `/<parent>/<edge>`), as data."""

    ref: str
    node: str
    edge: str
    params: Dict[str, Any]
    # Only for images: the local file whose bytes get uploaded. Kept out of
    # `params` because it is not a Graph parameter -- the SDK sends it as a
    # multipart file -- and because a path is machine-local, so a plan that put
    # it in `params` would not be portable.
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "ref": self.ref,
            "node": self.node,
            "edge": self.edge,
            "params": self.params,
        }
        if self.source is not None:
            out["source"] = self.source
        return out


@dataclass(frozen=True)
class TemplatePlan:
    """Everything `apply` will do, and nothing it will not."""

    account_id: str
    creates: Tuple[Create, ...]
    # The campaign this plan creates, or None when it adds ads to an existing
    # one. Exactly one of these two is set, and `apply` branches on it: a new
    # campaign is refused if the name is taken, an existing one is refused if
    # it does not carry the template marker.
    campaign_name: Optional[str] = None
    campaign_id: Optional[str] = None
    # A PRE-EXISTING ad set every ad in this plan hangs on. Set only alongside
    # `campaign_id`, and `apply` verifies on Meta that it really belongs to
    # that campaign -- because an ad is created with an `adset_id` and no
    # campaign of its own, so the ad set is what actually decides where the ad
    # lands. See `plan_template_ads`.
    adset_id: Optional[str] = None
    properties: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    # Refs whose values are already known -- an ad set that exists on Meta
    # rather than one this plan creates. Primes `apply`'s substitution table.
    seed: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "campaign_name": self.campaign_name,
            "campaign_id": self.campaign_id,
            "adset_id": self.adset_id,
            "properties": list(self.properties),
            "warnings": list(self.warnings),
            "seed": dict(self.seed),
            "creates": [c.to_dict() for c in self.creates],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class TemplateResult:
    """What `apply` created. Ids by ref, plus the blobs a study conf needs."""

    ids: Dict[str, str] = field(default_factory=dict)
    campaign_id: Optional[str] = None
    adsets: List[Dict[str, str]] = field(default_factory=list)
    ads: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "adsets": self.adsets,
            "ads": self.ads,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def _adset_params(spec: AdsetSpec, campaign_ref: str) -> Dict[str, Any]:
    if spec.kind not in CREATIVE_KINDS:
        raise TemplatePlanError(
            f"Ad set {spec.name!r}: unknown kind {spec.kind!r}. "
            f"One of: {', '.join(CREATIVE_KINDS)}."
        )
    if spec.daily_budget > MAX_DAILY_BUDGET:
        raise TemplatePlanError(
            f"Ad set {spec.name!r}: daily_budget {spec.daily_budget} is above "
            f"the template ceiling of {MAX_DAILY_BUDGET} cents. A template is "
            "never delivered, so its budget is a typo guard, not a setting -- "
            "if you meant it, this is the wrong tool."
        )
    if spec.daily_budget <= 0:
        raise TemplatePlanError(
            f"Ad set {spec.name!r}: daily_budget must be positive; Meta "
            "rejects an ad set with no budget and no campaign budget."
        )
    if not isinstance(spec.targeting, dict) or not spec.targeting:
        raise TemplatePlanError(
            f"Ad set {spec.name!r}: targeting must be a non-empty dict. It is "
            "the entire point of a template ad set -- the Variables form reads "
            "it back with extract_from_adset."
        )

    params: Dict[str, Any] = {
        "name": spec.name,
        "campaign_id": ref_placeholder(campaign_ref),
        "optimization_goal": spec.optimization_goal,
        "billing_event": spec.billing_event,
        "bid_strategy": spec.bid_strategy,
        "daily_budget": spec.daily_budget,
        "destination_type": DESTINATION_TYPE_BY_KIND[spec.kind],
        # Advantage audience off, and set here as well as forced by
        # `extract_from_adset`, so the template itself is honest about what it
        # targets. See DEFAULT_PROPERTIES for why it is NOT declared.
        "targeting": {
            **spec.targeting,
            "targeting_automation": {"advantage_audience": 0},
        },
        "status": PAUSED,
    }
    if spec.promoted_object:
        params["promoted_object"] = dict(spec.promoted_object)
    return params


def _check_declared_properties(
    adsets: Sequence[AdsetSpec], properties: Sequence[str]
) -> None:
    """Every declared property must exist on every planned ad set.

    Run at PLAN time, through the same `extract_from_adset` the dashboard's
    Variables form runs, because that is where the failure otherwise lands: a
    variable declaring `geo_locations` against an ad set built without it
    throws `PropertyMissingError` in the browser, hours later, with the
    template already created and the researcher looking at a React error rather
    than at the ad set they got wrong.

    Every ad set, not "some level": `properties_on_some_level` exists for the
    real case where Meta writes a key only where something is set
    (`excluded_geo_locations` on the excluding level only), and that is a
    property of ad sets read back FROM Meta. A plan is what we are about to
    send, so the stricter check is available here and is the useful one -- it
    catches the authoring mistake instead of tolerating it.
    """
    for spec in adsets:
        adset = {
            "id": spec.name,
            "name": spec.name,
            "targeting": {
                **spec.targeting,
                "targeting_automation": {"advantage_audience": 0},
            },
        }
        try:
            extract_from_adset(adset, list(properties))
        except PropertyMissingError as e:
            raise TemplatePlanError(
                f"Ad set {spec.name!r} has no {e.property_key!r} in its "
                "targeting, but it is a declared variable property. Either "
                "target it on this ad set, or drop it from `properties` -- "
                "extract_from_adset raises exactly this in the dashboard's "
                "Variables form, which is a much worse place to find out."
            ) from e


def _targeting_warnings(adsets: Sequence[AdsetSpec]) -> List[str]:
    out: List[str] = []
    for spec in adsets:
        geo = spec.targeting.get("geo_locations") or {}
        if not isinstance(geo, dict):
            continue
        if geo.get("regions") and "location_types" in geo:
            # MEASURED 2026-08-27 (make_template_campaign.py): Meta rewrites
            # `location_types` on write, adding `frequently_in` to
            # ["home", "recent"], and it CANNOT be removed -- an update sending
            # only home/recent is accepted and reads back with frequently_in
            # still on it. `extract_from_adset` then copies that into the
            # study's own ad sets. Harmless while nothing delivers; a real
            # sampling decision once something does, and one that belongs in
            # the study's write-up rather than being discovered in the data.
            out.append(
                f"Ad set {spec.name!r}: Meta will add 'frequently_in' to "
                f"geo_locations.location_types ({geo['location_types']}) and it "
                "cannot be removed (measured 2026-08-27). Region targeting "
                "therefore reaches people who frequently visit the region as "
                "well as residents. State that in the study's write-up."
            )
        if geo.get("regions"):
            out.append(
                f"Ad set {spec.name!r}: Meta canonicalises region names on "
                "write ('Kwara' -> 'Kwara State'), so the stored targeting "
                "will not be byte-identical to this plan."
            )
    return out


def _objective_warnings(objective: str, adsets: Sequence[AdsetSpec]) -> List[str]:
    """Pairings Meta is likely to reject, warned about rather than enforced.

    Warned and not refused, deliberately. Meta's own documentation contradicts
    itself here -- the `destination_type` guide's objective table omits
    WHATSAPP for OUTCOME_LEADS and OUTCOME_SALES while the click-to-WhatsApp
    page lists both (`planning/click-to-whatsapp-ads.md` §1.1) -- and the
    allowed set moves between Graph versions. A hardcoded matrix in here would
    become wrong silently and would then refuse plans Meta would have accepted,
    which is worse than saying "check this".

    The defaults are the messaging ones, mirrored off a live template campaign,
    so the pairing that actually bites is a web or app ad set left on them.
    """
    out: List[str] = []
    messaging_defaults = objective == DEFAULT_OBJECTIVE
    for spec in adsets:
        if spec.kind in (WEB, APP) and messaging_defaults:
            out.append(
                f"Ad set {spec.name!r} is {spec.kind!r} but the campaign "
                f"objective is {objective} and its optimization_goal is "
                f"{spec.optimization_goal} -- the click-to-messaging defaults. "
                "Meta pairs objective, optimization_goal and destination_type, "
                "and a website or app ad set normally wants OUTCOME_TRAFFIC "
                "with LINK_CLICKS or LANDING_PAGE_VIEWS. Check it before "
                "creating; the rejection at ad-set create time does not "
                "explain itself."
            )
        if spec.kind == APP and not (spec.promoted_object or {}).get("application_id"):
            out.append(
                f"Ad set {spec.name!r} is 'app' but has no "
                "promoted_object.application_id / object_store_url. Meta "
                "requires a promoted_object for an app-install ad set. Unlike "
                "the WhatsApp Page, there is nothing on the creative to take "
                "it from -- it lives on the study's `destinations` conf -- so "
                "pass it explicitly."
            )
        if spec.kind == MULTI and spec.optimization_goal != "CONVERSATIONS":
            out.append(
                f"Ad set {spec.name!r} is 'multi' with optimization_goal "
                f"{spec.optimization_goal!r}. Meta's click-to-multidestination "
                "guide says CONVERSATIONS is the only one accepted, which is "
                "strictly narrower than single-destination click-to-WhatsApp."
            )
    return out


def _creative_params(spec: AdSpec, image_ref: Optional[str]) -> Dict[str, Any]:
    return build_creative(
        spec.kind,
        name=spec.name,
        page_id=spec.page_id,
        message=spec.message,
        headline=spec.headline,
        description=spec.description,
        image_hash=(
            ref_placeholder(image_ref) if image_ref is not None else spec.image_hash
        ),
        video_id=spec.video_id,
        instagram_user_id=spec.instagram_user_id,
        link=spec.link,
        deeplink=spec.deeplink,
        declare_destination=spec.declare_destination,
    )


def _image_ref(path: str) -> str:
    """A stable ref for an upload, keyed on the path.

    Keyed on the path and not on a counter so that two ads sharing one image
    share one upload, and so that a plan is byte-stable under reordering of the
    ads that use it.
    """
    return f"image:{os.path.basename(path)}"


def _plan_ads(
    ads: Sequence[AdSpec],
    adset_ref_for: Mapping[Optional[str], str],
    known_adsets: Sequence[str],
) -> Tuple[List[Create], List[Create]]:
    """`(image uploads, creatives + ads)`, split so the caller can order them.

    Split rather than concatenated because the two halves belong on opposite
    sides of the campaign create: an image is cheap, reusable and orphan-safe,
    so uploading before anything else means a bad file cannot leave a campaign
    behind -- whereas a creative cannot be built until its image hash exists,
    and an ad cannot be built until its ad set does.
    """
    creates: List[Create] = []
    images: Dict[str, Create] = {}

    for spec in ads:
        if spec.image and spec.image_hash:
            raise TemplatePlanError(
                f"Ad {spec.name!r}: give an image path or an image_hash, not " "both."
            )
        if spec.adset is not None and spec.adset not in known_adsets:
            raise TemplatePlanError(
                f"Ad {spec.name!r} names ad set {spec.adset!r}, which this plan "
                f"does not create. Ad sets in this plan: {list(known_adsets)}."
            )

        image_ref: Optional[str] = None
        if spec.image:
            if not os.path.exists(spec.image):
                raise TemplatePlanError(
                    f"Ad {spec.name!r}: no such image file: {spec.image}. "
                    "Checked at plan time so an apply cannot die half way "
                    "through, leaving a campaign and ad sets nobody asked for."
                )
            image_ref = _image_ref(spec.image)
            if image_ref not in images:
                images[image_ref] = Create(
                    ref=image_ref,
                    node="image",
                    edge="adimages",
                    params={"name": os.path.basename(spec.image)},
                    source=spec.image,
                )
            elif images[image_ref].source != spec.image:
                raise TemplatePlanError(
                    f"Ad {spec.name!r}: two different image files share the "
                    f"basename {os.path.basename(spec.image)!r} "
                    f"({images[image_ref].source} and {spec.image}). Rename "
                    "one -- the upload is keyed on the basename so the plan "
                    "stays readable."
                )

        creative_ref = f"creative:{spec.name}"
        creates.append(
            Create(
                ref=creative_ref,
                node="creative",
                edge="adcreatives",
                params=_creative_params(spec, image_ref),
            )
        )

    # Deterministic order (sorted by ref) so the plan is byte-stable.
    ordered_images = [images[k] for k in sorted(images)]

    ad_creates: List[Create] = []
    for spec in ads:
        ad_creates.append(
            Create(
                ref=f"ad:{spec.name}",
                node="ad",
                edge="ads",
                params={
                    # The ad's name IS the creative's name, deliberately: vlab's
                    # reconciliation matches ads by name and the ad it builds is
                    # named for the creative conf. A template that follows the
                    # same rule is one whose Ads Manager row and whose study
                    # conf entry are the same string.
                    "name": spec.name,
                    "adset_id": ref_placeholder(adset_ref_for[spec.adset]),
                    "creative": {
                        "creative_id": ref_placeholder(f"creative:{spec.name}")
                    },
                    "status": PAUSED,
                },
            )
        )

    return ordered_images, creates + ad_creates


def _fill_promoted_object(
    spec: AdsetSpec, ads: Sequence[AdSpec], default_adset: str
) -> AdsetSpec:
    """Give a WhatsApp/multi ad set the Page its own ads post as, if it has none.

    `promoted_object_for` reads the page off the CREATIVE
    (`template_page_id`), so the ad set and the creative can never name
    different Pages at run time. A template ad set has to name it up front --
    Meta refuses a click-to-WhatsApp ad set without one -- and taking it from
    the ads being planned is the only source that cannot disagree.

    The WhatsApp NUMBER is not filled in: it lives on the study's
    `destinations` conf, not on the template, and guessing one is the failure
    `ctwa_probe.whatsapp_number_from_prod` exists to avoid ("an easy way to
    spend a day testing the wrong number").
    """
    if spec.kind not in (WHATSAPP, MULTI):
        return spec
    if spec.promoted_object and spec.promoted_object.get("page_id"):
        return spec

    # `a.adset or default_adset`, not `a.adset in (None, spec.name)`, which
    # review caught: an ad with no `adset` hangs on the FIRST ad set, but the
    # `in (None, ...)` form made it a candidate Page for every ad set — so an
    # ad set with no ads of its own silently inherited a Page from an ad
    # hanging somewhere else, and this function's own "no ad hangs on it"
    # message became unreachable in exactly the case it describes.
    pages = sorted(
        {
            a.page_id
            for a in ads
            if (a.adset or default_adset) == spec.name and a.page_id
        }
    )
    if len(pages) != 1:
        raise TemplatePlanError(
            f"Ad set {spec.name!r} is {spec.kind!r} and needs "
            "promoted_object.page_id -- Meta refuses a click-to-WhatsApp ad "
            "set without one. "
            + (
                "No ad in this plan hangs on it, so there is no Page to take."
                if not pages
                else f"Its ads name more than one Page ({pages}); say which."
            )
        )
    merged = dict(spec.promoted_object or {})
    merged["page_id"] = pages[0]
    return replace(spec, promoted_object=merged)


def plan_template_campaign(
    *,
    account_id: str,
    name: str,
    adsets: Sequence[AdsetSpec] = (),
    ads: Sequence[AdSpec] = (),
    objective: str = DEFAULT_OBJECTIVE,
    properties: Optional[Sequence[str]] = None,
) -> TemplatePlan:
    """The exact Graph calls that would build this template campaign.

    Pure: no sockets, no clock, no randomness, so the same arguments give the
    same bytes and a plan can be diffed, reviewed or committed. Everything
    checkable without Meta is checked here.

    :param account_id: `act_<id>` or `<id>`; normalised to the `act_` form,
        which is what a Graph path needs and what `GET /meta/adaccounts`
        returns.
    :param name: gains the `Templates - ` marker if it does not have it.
    :param properties: the variable properties these ad sets will be declared
        with. Defaults to `DEFAULT_PROPERTIES`; every one of them must be in
        every ad set's targeting or this raises.
    """
    account = normalise_account_id(account_id)
    campaign_name = template_campaign_name(name)
    props = tuple(DEFAULT_PROPERTIES if properties is None else properties)

    if not adsets:
        raise TemplatePlanError(
            "A template campaign with no ad sets configures nothing: the "
            "Variables form reads targeting off ad sets. Plan at least one."
        )

    seen: set = set()
    for spec in adsets:
        if spec.name in seen:
            raise TemplatePlanError(
                f"Two ad sets named {spec.name!r}. A level points at a template "
                "ad set by id, but a human picks it by name in a dropdown."
            )
        seen.add(spec.name)

    ad_names: set = set()
    for a in ads:
        if a.name in ad_names:
            raise TemplatePlanError(
                f"Two ads named {a.name!r}. The creative name is a join key -- "
                "`mint_ref_token` is keyed on it and reconciliation matches ads "
                "by it -- so it has to be unique."
            )
        ad_names.add(a.name)

    _check_declared_properties(adsets, props)

    # `adsets[0].name` is where an ad with no `adset` hangs; passing it in is
    # what keeps `_fill_promoted_object` agreeing with `_plan_ads` about that.
    filled = [_fill_promoted_object(s, ads, adsets[0].name) for s in adsets]

    campaign_ref = "campaign"
    campaign = Create(
        ref=campaign_ref,
        node="campaign",
        edge="campaigns",
        params={
            "name": campaign_name,
            "objective": objective,
            "status": PAUSED,
            "special_ad_categories": [],
            # MEASURED (make_template_campaign.py): required by Meta whenever
            # the campaign carries no budget of its own -- omitting it is a 400
            # with error_subcode 4834011. False matches
            # `marketing.create_campaign`, so a template campaign and the
            # campaigns adopt creates share one budgeting model.
            "is_adset_budget_sharing_enabled": False,
        },
    )

    adset_creates = [
        Create(
            ref=f"adset:{s.name}",
            node="adset",
            edge="adsets",
            params=_adset_params(s, campaign_ref),
        )
        for s in filled
    ]

    adset_ref_for: Dict[Optional[str], str] = {
        s.name: f"adset:{s.name}" for s in filled
    }
    adset_ref_for[None] = f"adset:{filled[0].name}"

    image_creates, ad_creates = _plan_ads(ads, adset_ref_for, [s.name for s in filled])

    warnings = _targeting_warnings(filled) + _objective_warnings(objective, filled)
    if "targeting_automation" in props:
        warnings.append(
            "'targeting_automation' is in `properties`. It is set on every ad "
            "set here and forced on by extract_from_adset regardless, so "
            "declaring it buys nothing -- and diff_property_keys strips it "
            "from the stored key set but not from the declared one, so the "
            "dashboard will show a 'properties drifted' banner on this "
            "variable forever (plan §12.3 item 4)."
        )
    if not ads:
        warnings.append(
            "No ads planned. The Creatives form reads ADS from a template "
            "campaign, so this campaign can back Variables but not Creatives. "
            "`vlab template creative` adds one later."
        )

    return TemplatePlan(
        account_id=account,
        # Images, then the campaign, then its ad sets, then the creatives and
        # the ads. See `_plan_ads` for why the uploads lead.
        creates=tuple(image_creates + [campaign] + adset_creates + ad_creates),
        campaign_name=campaign_name,
        properties=props,
        warnings=tuple(warnings),
    )


def plan_template_ads(
    *,
    account_id: str,
    campaign_id: str,
    adset_id: str,
    ads: Sequence[AdSpec],
) -> TemplatePlan:
    """Ads (and their creatives, and their image uploads) into a campaign that
    already exists.

    The Creatives half on its own, because that is the half a researcher
    actually gets stuck on: targeting can be lifted off any ad set, but a
    creative has to be built.

    `apply` refuses unless `campaign_id` carries the template marker AND
    `adset_id` actually belongs to that campaign. Both, because **an ad is
    created with an `adset_id` and no campaign of its own** -- Meta places it in
    whatever campaign that ad set belongs to. Checking only the campaign name
    therefore checked a value nothing downstream uses: a marked `--campaign`
    paired with an ad set from a live study's campaign passed the guard and put
    a paused ad inside the live study. Review caught it; `test_templates.py`
    has both directions.

    Keeping `campaign_id` as an argument rather than deriving it from the ad
    set is deliberate now that they are cross-checked. Deriving alone would
    accept an ad set from ANY marked campaign, so a mis-pasted id that happens
    to name another template's ad set would be silently honoured; naming both
    makes that a refusal.
    """
    if not ads:
        raise TemplatePlanError("Nothing to do: no ads given.")

    account = normalise_account_id(account_id)
    names: set = set()
    for a in ads:
        if a.name in names:
            raise TemplatePlanError(f"Two ads named {a.name!r}.")
        names.add(a.name)

    image_creates, ad_creates = _plan_ads(
        ads, {None: "adset", adset_id: "adset"}, [adset_id]
    )

    # `_plan_ads` emits a `${adset}` placeholder because it does not know
    # whether the ad set is planned or pre-existing. Here it is pre-existing,
    # so the id goes in the seed rather than being substituted into the plan:
    # the placeholder syntax stays uniform, and `apply`'s "references something
    # nothing creates" guard keeps its teeth for every other ref.
    return TemplatePlan(
        account_id=account,
        creates=tuple(image_creates + ad_creates),
        campaign_id=str(campaign_id),
        adset_id=str(adset_id),
        seed={"adset": str(adset_id)},
    )


def normalise_account_id(account_id: str) -> str:
    """`123` or `act_123` -> `act_123`.

    Both forms are in circulation for the same reason `server/meta.py` accepts
    both: the dashboard holds the bare `account_id` and prefixes it, while an
    agent reading `/meta/adaccounts` sees the already-prefixed `id`.
    """
    value = str(account_id or "").strip()
    if not value:
        raise TemplatePlanError("An ad account id is required.")
    return value if value.startswith("act_") else f"act_{value}"


# ---------------------------------------------------------------------------
# Applying
# ---------------------------------------------------------------------------


def _substitute(value: Any, table: Mapping[str, str]) -> Any:
    """Replace `${vlab:ref}` placeholders, recursively.

    Whole-string only: a placeholder is always an entire value (an id, a hash),
    never embedded in a sentence, so there is no partial interpolation to get
    wrong and no way for a Meta-supplied string to be treated as a template.
    Namespaced, so that a researcher's own ad copy cannot collide with one --
    see `PLACEHOLDER_PREFIX`.
    """
    if isinstance(value, str):
        if value.startswith(PLACEHOLDER_PREFIX) and value.endswith("}"):
            ref = value[len(PLACEHOLDER_PREFIX) : -1]
            if ref not in table:
                raise TemplateApplyError(
                    f"Plan references {ref!r}, which nothing in it creates. "
                    "This is a bug in the planner, not in your input."
                )
            return table[ref]
        return value
    if isinstance(value, dict):
        return {k: _substitute(v, table) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, table) for v in value]
    return value


def _graph_post(api, path: Tuple[str, ...], params=None, files=None) -> Dict[str, Any]:
    """One `POST`, through the SDK's session and nothing else.

    `api.call` rather than the typed `AdAccount.create_*` helpers, for one
    concrete reason: those validate parameter names against a hardcoded
    `param_types` map, and `is_adset_budget_sharing_enabled` -- the campaign
    field whose absence is a 400 with subcode 4834011 -- is not in the
    `create_campaign` map in facebook-business v22. Raw `call` also puts the
    mock boundary in exactly one place, which is where `server/test_meta.py`
    puts it.

    `adopt.facebook.api.call` is deliberately NOT used: it retries codes
    2/17/368/80004 forever at five-minute intervals with no attempt cap, which
    is right for a cron with hours to spend and wrong for a CLI a human is
    watching -- and worse than wrong for a create, where a retried POST that
    actually succeeded the first time leaves a duplicate object on the account.
    """
    response = api.call("POST", path, params=params or {}, files=files or {})
    return response.json()


def _graph_get(api, path: Tuple[str, ...], params=None) -> Dict[str, Any]:
    return api.call("GET", path, params=params or {}).json()


def meta_message(e: Exception) -> str:
    """A Meta rejection as one readable line, without `str(e)`.

    `str(FacebookRequestError)` interpolates the whole `request_context` --
    every parameter of the failed call. `server/meta.py` forbids echoing it for
    that reason, and although the access token is on the SESSION's params
    rather than in `request_context` (so there is no token to leak here), a
    creative body dumped into an exception message buries the one sentence Meta
    actually said. The code and subcode are what a search engine and
    `planning/click-to-whatsapp-ads.md` are indexed on.

    Falls back to `str(e)` for anything that is not a Meta error at all -- a
    connection reset, say -- where `str(e)` is the whole message.
    """
    getters = ("api_error_message", "api_error_code", "api_error_subcode")
    if not all(hasattr(e, g) for g in getters):
        return str(e)
    try:
        bits = [str(e.api_error_message())]  # type: ignore[attr-defined]
        code = e.api_error_code()  # type: ignore[attr-defined]
        subcode = e.api_error_subcode()  # type: ignore[attr-defined]
        if code is not None:
            bits.append(f"code {code}")
        if subcode is not None:
            bits.append(f"subcode {subcode}")
        return (
            " (".join([bits[0], ", ".join(bits[1:]) + ")"])
            if len(bits) > 1
            else bits[0]
        )
    except Exception:  # noqa: BLE001 -- a malformed error body must not mask the error
        return str(e)


def find_campaign_by_name(api, account_id: str, name: str) -> Optional[Dict[str, Any]]:
    """The first campaign on the account with exactly this name, or None."""
    body = _graph_get(
        api,
        (normalise_account_id(account_id), "campaigns"),
        {
            "fields": "name,id,effective_status",
            "filtering": json.dumps(
                [{"field": "name", "operator": "EQUAL", "value": name}]
            ),
            "limit": 100,
        },
    )
    for c in body.get("data") or []:
        if c.get("name") == name:
            return c
    return None


def _upload_image(api, account_id: str, path: str) -> str:
    """Upload one local file and return its `image_hash`.

    Meta's `/act_<id>/adimages` response is `{"images": {<filename>: {"hash",
    "url"}}}` -- keyed by the name the file was uploaded under, not by
    anything the caller chose, which is why the hash is read out of the single
    value rather than looked up by key.
    """
    with open(path, "rb") as fh:
        body = _graph_post(
            api,
            (normalise_account_id(account_id), "adimages"),
            files={os.path.basename(path): fh},
        )
    images = body.get("images") or {}
    if not images:
        raise TemplateApplyError(
            f"Meta accepted the upload of {path} but returned no image hash: "
            f"{body!r}"
        )
    return next(iter(images.values()))["hash"]


def _read_creative(api, creative_id: str) -> Dict[str, Any]:
    """The created creative, in the shape `GET /{org}/meta/ads` returns it.

    Read back rather than assumed. What a study stores as
    `creatives[].template` is what the Meta proxy returns, NOT what we sent:
    Meta fills in `actor_id`, rewrites `object_story_spec`, and drops fields it
    did not accept. Handing the caller the sent params as if they were the
    template would produce a `creatives` conf that has never existed on Meta --
    and `audiences.py` reads `template["actor_id"]`, which is exactly one of
    the fields Meta derives rather than echoes.
    """
    return _graph_get(api, (creative_id,), {"fields": CREATIVE_FIELDS})


def _refuse_unsafe_creates(plan: TemplatePlan) -> None:
    """Re-check PAUSED and the budget ceiling on the plan `apply` was handed.

    Both are enforced by the planner already. This is not redundancy for its
    own sake: `apply` posts `create.params` VERBATIM, and a `TemplatePlan` is a
    plain dataclass that anything can construct -- a test fixture, a plan
    round-tripped through JSON and edited, a future third planner. The two
    invariants this module is *for* should hold at the boundary that actually
    sends bytes, not only at the one that happens to be the usual entry point.

    Cheap enough to be free (a walk over a list that is already in memory) and
    it fails before the first Graph call, so an unsafe plan creates nothing.
    """
    for create in plan.creates:
        if create.node in ("campaign", "adset", "ad"):
            status = create.params.get("status")
            if status != PAUSED:
                raise TemplateApplyError(
                    f"REFUSING: {create.node} {create.ref!r} has status "
                    f"{status!r}, not {PAUSED!r}. This module never creates a "
                    "delivering object; a plan that says otherwise did not "
                    "come from its planner."
                )
        if create.node == "adset":
            budget = create.params.get("daily_budget")
            if not isinstance(budget, int) or not 0 < budget <= MAX_DAILY_BUDGET:
                raise TemplateApplyError(
                    f"REFUSING: ad set {create.ref!r} has daily_budget "
                    f"{budget!r}, outside 1..{MAX_DAILY_BUDGET} cents."
                )


def _refuse_adset_outside_campaign(api, plan: TemplatePlan) -> None:
    """The ad set a plan hangs its ads on must belong to the marked campaign.

    THE HOLE THIS CLOSES, found in review of PR #267. An ad is created with an
    `adset_id` and no campaign of its own -- Meta puts it in whatever campaign
    that ad set belongs to. So checking the marker on `plan.campaign_id` was
    checking a value nothing downstream reads: `--campaign <a "Templates - "
    campaign> --adset <an ad set in a live study's campaign> --create` passed
    the guard and created a paused ad inside the live study. The campaign name
    was, in effect, decoration.

    Resolved from Meta rather than trusted, and compared against the campaign
    whose marker was just checked, so the two statements have to agree.
    """
    if plan.adset_id is None:
        return

    adset = _graph_get(api, (plan.adset_id,), {"fields": "id,name,campaign_id"})
    actual = str(adset.get("campaign_id") or "")
    if actual != str(plan.campaign_id):
        raise TemplateApplyError(
            f"REFUSING: ad set {plan.adset_id} ({adset.get('name')!r}) belongs "
            f"to campaign {actual or '(unknown)'}, not to "
            f"{plan.campaign_id}. An ad is created with an adset_id and no "
            "campaign of its own, so the AD SET decides which campaign the ad "
            "lands in -- a marked campaign paired with someone else's ad set "
            "would put a paused ad inside whatever study owns that ad set. "
            "Pass the campaign this ad set is actually in."
        )


def apply(plan: TemplatePlan, api) -> TemplateResult:
    """Execute a plan, in order, refusing before it starts if it is unsafe.

    Two refusals, both before anything is created:

    * a NEW campaign whose name is already on the account. Refusing rather than
      reusing, because two campaigns with one name make
      `FacebookState.campaign` raise `StateNameError` ("Multiple campaigns
      found with name") -- so a duplicate does not just confuse a human, it
      breaks the run path for any study pointing at that name. A half-populated
      reuse would also leave ad sets whose targeting nobody has checked. Delete
      and re-run is the recoverable path.
    * an EXISTING campaign that does not carry the template marker, AND a
      pre-existing ad set that does not belong to that campaign. Both are
      needed: an ad is created with an `adset_id` and no campaign of its own,
      so the ad set is what actually decides where the ad lands. Together they
      are what stands between `vlab template creative` and a paused ad
      appearing inside a live study's campaign.

    There is no rollback. A create that fails half way leaves what it already
    made; the message says which ref failed, and `delete_template_campaign`
    removes the campaign and everything under it.
    """
    _refuse_unsafe_creates(plan)

    result = TemplateResult(warnings=list(plan.warnings))
    table: Dict[str, str] = dict(plan.seed)

    if plan.campaign_name is not None:
        existing = find_campaign_by_name(api, plan.account_id, plan.campaign_name)
        if existing is not None:
            raise TemplateApplyError(
                f"REFUSING: a campaign named {plan.campaign_name!r} already "
                f"exists on {plan.account_id} (id {existing.get('id')}). "
                "Delete it first or pick another name -- duplicate names break "
                "FacebookState.campaign, which raises StateNameError and takes "
                "down the run path of any study naming that campaign."
            )
    elif plan.campaign_id is not None:
        campaign = _graph_get(api, (plan.campaign_id,), {"fields": "name,id"})
        if not is_template_campaign(campaign.get("name")):
            raise TemplateApplyError(
                f"REFUSING: campaign {plan.campaign_id} is named "
                f"{campaign.get('name')!r}, which does not start with "
                f"{TEMPLATE_CAMPAIGN_PREFIX!r}. This tool only writes into "
                "campaigns marked as templates, so that it can never add an "
                "object to a campaign that is actually recruiting."
            )
        _refuse_adset_outside_campaign(api, plan)
        result.campaign_id = str(plan.campaign_id)
    else:
        # Neither field set. Not reachable from either constructor today, and
        # that is precisely why it is worth a raise rather than a comment: this
        # `if/elif` is the ONLY place the two refusals live, so a plan that
        # matched neither arm would create objects with nothing checked at all.
        # A future third constructor should have to notice this.
        raise TemplateApplyError(
            "This plan names neither a campaign to create nor a campaign to "
            "add to, so neither the name-collision check nor the template "
            "marker check can run. Refusing to create anything. This is a bug "
            "in the planner, not in your input."
        )

    for create in plan.creates:
        params = _substitute(create.params, table)

        try:
            if create.node == "image":
                assert create.source is not None
                table[create.ref] = _upload_image(api, plan.account_id, create.source)
                continue

            # Every edge here hangs off the ad account -- `/act_x/campaigns`,
            # `/act_x/adsets`, `/act_x/adcreatives`, `/act_x/ads`. The parent
            # links (campaign_id, adset_id, creative_id) travel in the body,
            # which is why the plan needs placeholders at all.
            body = _graph_post(api, (plan.account_id, create.edge), params)
        except TemplateError:
            raise
        except Exception as e:  # noqa: BLE001 -- re-raised with the ref attached
            raise TemplateApplyError(
                f"Meta refused {create.node} {create.ref!r}: {meta_message(e)}. "
                f"Nothing after it was attempted; what came before it exists. "
                + (
                    f"Remove it with `vlab template delete {table['campaign']}`."
                    if "campaign" in table
                    else ""
                )
            ) from e

        new_id = str(body.get("id"))
        table[create.ref] = new_id

        if create.node == "campaign":
            result.campaign_id = new_id
        elif create.node == "adset":
            result.adsets.append({"id": new_id, "name": params["name"]})
        elif create.node == "ad":
            creative_id = params["creative"]["creative_id"]
            template = _read_creative(api, creative_id)
            missing = [
                f for f in REQUIRED_TEMPLATE_CREATIVE_FIELDS if not template.get(f)
            ]
            if missing:
                result.warnings.append(
                    f"Creative {params['name']!r} came back from Meta without "
                    f"{missing}. A `creatives` conf built on it will fail at "
                    "run time -- adopt reads template['actor_id'] with a bare "
                    "KeyError and indexes template['object_story_spec'] "
                    "unconditionally."
                )
            result.ads.append(
                {
                    "id": new_id,
                    "name": params["name"],
                    "adset_id": params["adset_id"],
                    "creative_id": creative_id,
                    # The blob to paste into a `creatives` conf as `template`.
                    "template": template,
                }
            )

    result.ids = table
    return result


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------

# Meta's `effective_status` values that mean the campaign is, or could be,
# delivering. Refusing to delete one of these is belt-and-braces on top of the
# name marker: a template campaign should never be in any of them, so finding
# one here means something has been activated by hand and deleting it silently
# would destroy whatever that was.
DELIVERING_STATUSES = frozenset({"ACTIVE", "IN_PROCESS", "WITH_ISSUES"})


def delete_template_campaign(
    api, campaign_id: str, force: bool = False
) -> Dict[str, Any]:
    """Delete a campaign and everything under it -- if it is marked as a template.

    The marker is the name prefix (`TEMPLATE_CAMPAIGN_PREFIX`). Two refusals,
    and the second one is the one that will annoy somebody: a campaign whose
    `effective_status` says it is delivering is refused even when it IS marked,
    because a delivering template is a template someone activated, and the
    reason they did is not knowable from here. `force=True` skips only that
    second check; nothing skips the marker.
    """
    campaign = _graph_get(
        api, (str(campaign_id),), {"fields": "name,id,effective_status"}
    )
    name = campaign.get("name")

    if not is_template_campaign(name):
        raise TemplateApplyError(
            f"REFUSING to delete campaign {campaign_id}: it is named {name!r}, "
            f"which does not start with {TEMPLATE_CAMPAIGN_PREFIX!r}. This tool "
            "deletes only campaigns it could have created. If this really is a "
            "template, rename it in Ads Manager first -- that is a deliberate "
            "speed bump, because the alternative is a typo'd id deleting a "
            "live study's campaign and every ad in it."
        )

    status = campaign.get("effective_status")
    if status in DELIVERING_STATUSES and not force:
        raise TemplateApplyError(
            f"REFUSING to delete campaign {campaign_id} ({name!r}): its "
            f"effective_status is {status}, so it is or could be delivering. A "
            "template is created PAUSED and should never be; somebody "
            "activated it. Pause it, or pass --force if you know why."
        )

    api.call("DELETE", (str(campaign_id),))
    return {"deleted": str(campaign_id), "name": name}


# ---------------------------------------------------------------------------
# Targeting validation, without creating anything
# ---------------------------------------------------------------------------

REACH_ESTIMATE = "reachestimate"
DELIVERY_ESTIMATE = "delivery_estimate"


def validate_targeting(
    api,
    account_id: str,
    targeting: Dict[str, Any],
    *,
    edge: str = REACH_ESTIMATE,
    optimization_goal: Optional[str] = None,
) -> Dict[str, Any]:
    """Ask Meta whether a targeting spec is valid, and how many people it reaches.

    Read-only: it creates nothing, spends nothing and touches no campaign. That
    makes it the cheapest possible answer to "will this ad set be accepted",
    which today is only answerable by creating one -- the gap
    `planning/agent-study-authoring.md` §10 names when it says reachestimate is
    "a worthwhile meta:read addition".

    A malformed spec comes back as a Meta 400 naming the offending key, which
    is the entire value: `geo_locations.regions[].key` wrong by one digit is
    otherwise discovered at ad-set create time, after a campaign exists.

    Two edges, because Meta has been migrating between them for years and
    neither this repo nor its docs pin a version where one is definitively
    gone:

    * `reachestimate` (default) takes only `targeting_spec` and answers with
      `users_lower_bound` / `users_upper_bound` (older responses said `users`).
    * `delivery_estimate` additionally requires `optimization_goal` and answers
      with a list of `estimate_dau` / `estimate_mau_lower_bound` entries.

    Neither has been exercised against live Meta from this code. If the default
    returns "Unsupported get request", pass `edge=DELIVERY_ESTIMATE`.
    """
    if edge not in (REACH_ESTIMATE, DELIVERY_ESTIMATE):
        raise TemplatePlanError(
            f"Unknown edge {edge!r}; one of {REACH_ESTIMATE}, {DELIVERY_ESTIMATE}."
        )
    if edge == DELIVERY_ESTIMATE and not optimization_goal:
        raise TemplatePlanError(
            "delivery_estimate requires an optimization_goal (e.g. "
            f"{DEFAULT_OPTIMIZATION_GOAL})."
        )

    params: Dict[str, Any] = {"targeting_spec": json.dumps(targeting)}
    if optimization_goal:
        params["optimization_goal"] = optimization_goal

    return _graph_get(api, (normalise_account_id(account_id), edge), params)
