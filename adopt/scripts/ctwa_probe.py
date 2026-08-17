"""Probe what Meta actually does with Click-to-WhatsApp and multi-destination ads.

    ctwa_probe.py --list-ads <campaign-id>          # find a template ad to copy
    ctwa_probe.py --variant whatsapp                # dry run: print the payloads
    ctwa_probe.py --variant whatsapp --mode check   # create adset only, report Meta's error
    ctwa_probe.py --variant whatsapp --mode create  # create campaign+adset+ad, PAUSED
    ctwa_probe.py --read-back <ad-id>               # what Meta actually stored
    ctwa_probe.py --preview <ad-id>                 # shareable preview link (click this)
    ctwa_probe.py --capture <ref-token>             # pull matching webhooks out of prod
    ctwa_probe.py --capture-user <userid>           # ...or everything from one user, fast
    ctwa_probe.py --mode cleanup --campaign <id>    # delete what this made

The runbook that drives this is planning/ctwa-probe-runbook.md. Read it before
creating anything: the flag values there are chosen to isolate Meta's behaviour
from fly's deployment state, and picking your own can produce a confidently
wrong answer.

WHY THIS EXISTS
---------------
Meta does not document the things we need to know to support WhatsApp
recruitment. Specifically, as of 2026-08, none of the following appear
anywhere in the official docs (see planning/click-to-whatsapp-ads.md §7):

  1. Whether `AdCreative.url_tags` populates `referral.ref` on a WhatsApp
     conversation the way it demonstrably does on Messenger. This is the
     single most valuable unknown: production data shows every Messenger
     referral since 2024 carrying a `ref` that we set via url_tags
     (marketing.py:463), invisible to the user and not editable by them.
     If the same holds for WhatsApp, our existing mechanism ports unchanged.

  2. What the webhook carries on the WhatsApp arm of a MULTI-DESTINATION ad.
     Meta documents the ad structure but says nothing about attribution:
     not whether `referral` is present at all, not whether `source_id` or
     `ctwa_clid` survive. If nothing survives, multi-destination WhatsApp
     conversations cannot be bound to a survey by any known mechanism.

  3. Whether one `page_welcome_message` can serve both arms — it is a single
     string field, and Messenger and WhatsApp want different shapes inside it.

Everything here is therefore an experiment, not an implementation. The
creative/adset payloads are built to mirror what adopt would send
(adopt/adopt/marketing.py), so that a result here is evidence about the real
code path and not about a hand-rolled approximation.

SAFETY
------
Dry run is the default and touches nothing. `--mode check` creates an ad set
and nothing else, which is enough to learn whether Meta accepts the
page/number binding — a rejected create never becomes a live ad and never
spends. `--mode create` makes real objects, always PAUSED; they must be
activated by hand before they deliver. `--mode cleanup` deletes them again.
"""

import argparse
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError
from facebook_business.session import FacebookSession

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ctwa_probe")

# Meta's own samples use exactly these links, and AdCreativeLinkData requires
# link_data.link to match the CTA link. Do not "tidy" them.
MESSENGER_LINK = "https://fb.com/messenger_doc/"
WHATSAPP_LINK = "https://api.whatsapp.com/send"
INSTAGRAM_LINK = "https://www.instagram.com"

DEFAULT_AD_ACCOUNT = "act_1342820622846299"  # Virtual Lab - USD
GRAPH_VERSION = "v25.0"

CRDB_POD = "gbv-cockroachdb-0"
CRDB_NS = "vprod"

# adopt runs adsets on a fixed window; mirror it (marketing.py:ADSET_HOURS).
ADSET_HOURS = 48


# ---------------------------------------------------------------- credentials


def token_from_prod(key: str = "virtual-lab-vlab") -> str:
    """Read a facebook_ad_user token out of the production credentials table.

    Kept out of argv deliberately so the token never lands in shell history
    or a process list.
    """
    sql = (
        "SELECT details->>'access_token' FROM credentials "
        f"WHERE entity='facebook_ad_user' AND key='{key}'"
    )
    out = subprocess.run(
        ["kubectl", "exec", "-n", CRDB_NS, CRDB_POD, "--", "./cockroach", "sql",
         "--insecure", "--database=chatroach", "--format=csv", "-e", sql],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    if len(out) < 2:
        raise SystemExit(f"No facebook_ad_user credential with key={key!r}")
    return out[-1].strip()


def whatsapp_number_from_prod(phone_number_id: str) -> Dict[str, str]:
    """Resolve a phone_number_id to its display number.

    promoted_object.whatsapp_phone_number wants the dialable number, not the
    phone_number_id, and getting that wrong is an easy way to spend a day
    testing the wrong number — the org has more than one registered.
    """
    sql = (
        "SELECT details->>'display_phone_number', details->>'waba_id' "
        "FROM credentials WHERE entity='whatsapp_business' "
        f"AND key='{phone_number_id}'"
    )
    out = subprocess.run(
        ["kubectl", "exec", "-n", CRDB_NS, CRDB_POD, "--", "./cockroach", "sql",
         "--insecure", "--database=chatroach", "--format=csv", "-e", sql],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    if len(out) < 2:
        raise SystemExit(f"No whatsapp_business credential with key={phone_number_id!r}")
    display, waba = (out[-1].split(",") + ["", ""])[:2]
    # The promoted_object reference types whatsapp_phone_number as a *numeric
    # string*, but credentials store the display form ("+1-541-920-2635").
    # Strip to digits; keep the display form around for the log line so a
    # human can confirm we picked the number they expected.
    digits = "".join(ch for ch in display if ch.isdigit())
    return {"display_phone_number": display.strip(),
            "whatsapp_phone_number": digits,
            "waba_id": waba.strip()}


def get_api(token: str) -> FacebookAdsApi:
    app_id = os.environ.get("FACEBOOK_APP_ID")
    app_secret = os.environ.get("FACEBOOK_APP_SECRET")
    if app_id and app_secret:
        # Matches adopt/adopt/facebook/state.py:get_api — appsecret_proof included.
        return FacebookAdsApi(FacebookSession(app_id, app_secret, token))
    logger.warning("FACEBOOK_APP_ID/SECRET unset — using token-only session")
    return FacebookAdsApi.init(access_token=token, api_version=GRAPH_VERSION)


# ------------------------------------------------------ vlab's ref serialisers
#
# MIRRORED, deliberately, from the real code path:
#   adopt/adopt/marketing.py  make_ref / shortcode_ref / whatsapp_autofill /
#                             ref_metadata / creative_metadata
#   adopt/adopt/study_conf.py ref_value
# on branch `feature/ad-id-attribution` (../vlab-ad-id-attribution).
#
# Copied rather than imported because this script runs from `main`, where
# `whatsapp_autofill` does not exist yet — importing would silently emit the
# *old* format and the probe would measure something nobody will ever ship.
# Keep these in sync with the branch; if the branch's serialisers change, this
# file is stale and the next probe run is measuring history.
#
# The earlier probe emitted `ctwaprobe.alpha.creative.Ad1H.form.probetest`,
# which leads with neither `creative.` nor `form.` and is therefore routable by
# nothing. It duly landed the one and only production WhatsApp referral on
# FALLBACK_FORM. That is the failure this section exists to prevent.


def ref_value(value: str) -> str:
    """study_conf.ref_value. `quote()` keeps `.` and `~`; both break a ref."""
    return quote(value).replace(".", "%2E").replace("~", "%7E")


def shortcode_ref(shortcode: str) -> str:
    """marketing.shortcode_ref — the minimal, always-parseable WhatsApp head."""
    return f"form.{ref_value(shortcode)}"


def make_ref(creative_name: str, metadata: Dict[str, str]) -> str:
    """marketing.make_ref — Messenger's `creative.`-led, order-free grammar."""
    s = f"creative.{ref_value(creative_name)}"
    for k, v in metadata.items():
        s += f".{ref_value(k)}.{ref_value(v)}"
    return s


def ref_metadata(creative_name: str, metadata: Dict[str, str]) -> Dict[str, str]:
    """marketing.ref_metadata — the full key set make_ref carries."""
    return {"creative": creative_name, **metadata}


def whatsapp_autofill(
    shortcode: str, ref_md: Optional[Dict[str, str]] = None
) -> str:
    """marketing.whatsapp_autofill — form-first, because fly's gate anchors there."""
    s = shortcode_ref(shortcode)
    for k, v in (ref_md or {}).items():
        if k == "form":
            continue
        s += f".{ref_value(k)}.{ref_value(v)}"
    return s


def creative_metadata(shortcode: str, stratum_md: Dict[str, str]) -> Dict[str, str]:
    """marketing.creative_metadata, minus the study/stratum plumbing.

    `form` is folded in here and not carried on the stratum, exactly as the
    real function does, so the two refs below are built from one dict.
    """
    return {**stratum_md, "form": shortcode}


# ------------------------------------------------------------- pattern safety
#
# Production fly (`replybot-v0.0.218`, fly@main) gates WhatsApp entry on
#
#   /^(?:start\s+)?form\.([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)$/i
#
# The widened pattern that also accepts `%XX` escapes exists only on fly's
# unmerged `feature/ad-id-attribution` branch. So a probe token containing a
# space, a dot inside a value, or any other character that `ref_value` escapes
# would be rejected by the fly that is actually running — and a null result
# would be indistinguishable from Meta having dropped the token. That is a
# confound that produces a *wrong conclusion*, not merely a missing one.
#
# Hence: refuse to build anything whose tokens are not already inside the
# narrow alphabet. Under that restriction `ref_value` is the identity, so the
# probe emits byte-for-byte what vlab emits while staying inside the deployed
# gate.
PATTERN_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")


def unsafe_tokens(tokens: Dict[str, str]) -> List[str]:
    return [f"{k}={v!r}" for k, v in tokens.items() if not PATTERN_SAFE.match(v)]


def assert_pattern_safe(tokens: Dict[str, str], allow_unsafe: bool) -> None:
    bad = unsafe_tokens(tokens)
    if not bad:
        return
    msg = (
        "These tokens are outside production fly's WhatsApp entry alphabet "
        f"[A-Za-z0-9_-]: {', '.join(bad)}.\n"
        "  ref_value would percent-encode them, and replybot-v0.0.218 rejects "
        "`%` outright.\n"
        "  A null result would then be fly's version lag, not Meta's "
        "behaviour, and the test would prove nothing.\n"
        "  Pick safe values, or pass --allow-unsafe-tokens if you *are* "
        "deliberately testing the gate."
    )
    if allow_unsafe:
        logger.warning("WARNING (--allow-unsafe-tokens): " + msg)
        return
    raise SystemExit("REFUSING TO BUILD: " + msg)


# ------------------------------------------------------- welcome message shapes


def welcome_messenger_legacy(text: str, button: str, ref: str) -> str:
    """Exactly what marketing.py:make_welcome_message builds today.

    The legacy array shape. Included as the control: if the probe cannot
    reproduce a working Messenger ad, a negative WhatsApp result means nothing.
    """
    payload = json.dumps({"referral": {"ref": ref}})
    return json.dumps(
        {"message": {"text": text,
                     "quick_replies": [{"content_type": "text",
                                        "title": button,
                                        "payload": payload}]}},
        sort_keys=True,
    )


def welcome_whatsapp_autofill(greeting: str, autofill: str) -> str:
    """VISUAL_EDITOR + autofill_message, per Meta's CTWA sample.

    NOTE: AdCreativeLinkData types page_welcome_message as `string`, so this
    must be serialised even though the guide prints it unquoted. That mismatch
    is the most likely cause of a first-attempt API error.
    """
    return json.dumps({
        "type": "VISUAL_EDITOR",
        "version": 2,
        "landing_screen_type": "welcome_message",
        "media_type": "text",
        "text_format": {
            "customer_action_type": "autofill_message",
            "message": {"autofill_message": {"content": autofill}, "text": greeting},
        },
    }, sort_keys=True)


def welcome_combined(greeting: str, button: str, ref: str, autofill: str) -> str:
    """Both sub-structures in one blob, to test whether each arm reads its own.

    Undocumented. `customer_action_type` is a scalar and may act as a strict
    discriminator, in which case one of these is silently ignored — which one
    decides which platform loses the ref. That is the whole point of the test.
    """
    payload = json.dumps({"referral": {"ref": ref}})
    return json.dumps({
        "type": "VISUAL_EDITOR",
        "version": 2,
        "landing_screen_type": "welcome_message",
        "media_type": "text",
        "text_format": {
            "customer_action_type": "autofill_message",
            "message": {
                "autofill_message": {"content": autofill},
                "quick_replies": [{"content_type": "text",
                                   "title": button,
                                   "payload": payload}],
                "text": greeting,
            },
        },
    }, sort_keys=True)


# ------------------------------------------------------------------- builders


def build_creative(variant: str, tpl: Dict[str, Any], page_id: str, ref: str,
                   greeting: str, button: str, autofill: str,
                   headline: str, primary_text: str,
                   creative_name: str,
                   multi_fallback: str = "messenger") -> Dict[str, Any]:
    """Build the creative for a variant, copying media/copy from a template ad.

    `ref` is the Messenger-grammar token (url_tags + quick-reply payload);
    `autofill` is the WhatsApp-grammar token (compose-box prefill). They are
    deliberately *different serialisations of the same facts* — see
    whatsapp_autofill's docstring on the branch. Do not collapse them.

    `multi_fallback` only affects `--variant multi`: it selects which app the
    single-valued object_story_spec CTA points at, and therefore which arm a
    PREVIEW click lands on. See the multi branch below.
    """
    # Never inherit a live study's ad copy. An earlier version of this probe
    # copied primary_text off a real ad, which meant a test ad promising
    # respondents 1,000 naira of airtime for a survey that does not exist.
    # Borrow the image; write our own words.
    link_data: Dict[str, Any] = {
        "name": headline,
        "message": primary_text,
    }
    if tpl.get("image_hash"):
        link_data["image_hash"] = tpl["image_hash"]

    creative: Dict[str, Any] = {
        "name": creative_name,
        "object_story_spec": {"page_id": page_id, "link_data": link_data},
    }

    if variant == "messenger":
        # url_tags is a live, load-bearing Messenger carrier: it surfaces as the
        # top-level referral.ref on a messaging_referrals webhook (measured, 3,153
        # rows in 30 days). It is NOT the majority carrier — see the runbook.
        creative["url_tags"] = f"ref={ref}"
        link_data["link"] = MESSENGER_LINK
        link_data["call_to_action"] = {"type": "MESSAGE_PAGE",
                                       "value": {"app_destination": "MESSENGER"}}
        link_data["page_welcome_message"] = welcome_messenger_legacy(greeting, button, ref)

    elif variant == "whatsapp":
        # No url_tags, matching create_creative's WhatsApp branch on the branch:
        # it was measured in 2026-08 not to reach WhatsApp at all (the referral's
        # complete key set came back without `ref`). Emitting it anyway would
        # make this control diverge from what vlab actually ships.
        link_data["link"] = WHATSAPP_LINK
        link_data["call_to_action"] = {"type": "WHATSAPP_MESSAGE",
                                       "value": {"app_destination": "WHATSAPP"}}
        link_data["page_welcome_message"] = welcome_whatsapp_autofill(greeting, autofill)

    elif variant == "multi":
        # object_story_spec CTA stays single-valued as the fallback; the array
        # lives in asset_feed_spec. Per Meta's multidestination sample.
        #
        # WHICH app that fallback names is what `multi_fallback` selects, and it
        # is the entire reason the flag exists. On the 2026-08-17 run the
        # preview followed this single-valued CTA to Messenger on every attempt,
        # so the WhatsApp arm was never reached and its behaviour is still
        # unmeasured — the one thing standing between `type: "multi"` and
        # shipping.
        #
        # Pointing the fallback at WhatsApp steers a preview click to the other
        # arm while leaving the ad set (MESSAGING_MESSENGER_WHATSAPP), the
        # combined page_welcome_message and the asset_feed_spec destination
        # array byte-identical. That isolates the question that actually
        # matters: on a multi-destination ad set, does the WhatsApp side read
        # its own sub-structure out of a blob that also carries quick_replies,
        # or does Meta serve its default prefill and strand every WhatsApp
        # respondent in FALLBACK_FORM?
        #
        # READ THE CAVEAT before concluding anything: this measures the blob,
        # not Meta's organic arm-selection path. See
        # documentation/multi-destination-ads.md.
        creative["url_tags"] = f"ref={ref}"

        if multi_fallback == "whatsapp":
            # AdCreativeLinkData requires link_data.link to match its CTA.
            link_data["link"] = WHATSAPP_LINK
            link_data["call_to_action"] = {
                "type": "WHATSAPP_MESSAGE",
                "value": {"app_destination": "WHATSAPP"}}
        else:
            link_data["link"] = MESSENGER_LINK
            link_data["call_to_action"] = {"type": "MESSAGE_PAGE",
                                           "value": {"app_destination": "MESSENGER"}}

        pwm = welcome_combined(greeting, button, ref, autofill)
        link_data["page_welcome_message"] = pwm
        creative["asset_feed_spec"] = {
            "optimization_type": "DOF_MESSAGING_DESTINATION",
            "call_to_actions": [
                {"type": "MESSAGE_PAGE",
                 "value": {"app_destination": "MESSENGER", "link": MESSENGER_LINK}},
                {"type": "WHATSAPP_MESSAGE",
                 "value": {"app_destination": "WHATSAPP", "link": WHATSAPP_LINK}},
            ],
            # Also on the asset_feed_spec, because that is what adopt does:
            # _create_creative (branch, marketing.py:534-540) sets
            # asset_feed_spec.additional_data.page_welcome_message whenever the
            # template carries an asset_feed_spec, *in addition to* the copy on
            # link_data. The first multi probe (`probe.multi.two`, ad
            # 120254876245580150) omitted this, which means a blank welcome
            # screen there would have had a placement explanation and would
            # have been misread as "Meta dropped the combined blob".
            "additional_data": {"page_welcome_message": pwm},
        }
    else:
        raise SystemExit(f"unknown variant {variant!r}")

    return creative


def build_adset(variant: str, campaign_id: str, page_id: str, name: str,
                budget_cents: int, country: str,
                whatsapp_number: Optional[str],
                optimization_goal: str = "CONVERSATIONS") -> Dict[str, Any]:
    destination = {"messenger": "MESSENGER",
                   "whatsapp": "WHATSAPP",
                   "multi": "MESSAGING_MESSENGER_WHATSAPP"}[variant]

    promoted: Dict[str, Any] = {"page_id": page_id}
    # Be explicit rather than relying on the Page's "primary" number — the org
    # has more than one registered, and a pass on the wrong one proves nothing.
    if variant in ("whatsapp", "multi") and whatsapp_number:
        promoted["whatsapp_phone_number"] = whatsapp_number

    # Mirror adopt/adopt/marketing.py:create_adset. bid_strategy and the
    # start/end window are not optional — Meta rejects the create without a
    # bid strategy (subcode 2490487), and adopt has always sent these.
    now = datetime.utcnow()
    midnight = now.replace(microsecond=0, second=0, minute=0, hour=0)

    adset = {
        "name": name,
        "campaign_id": campaign_id,
        "destination_type": destination,
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        # Meta's docs say multi-destination REQUIRES CONVERSATIONS. But a Page
        # subject to European privacy rules cannot use CONVERSATIONS for CTWA
        # at all (subcode 3858658) — so the two constraints can conflict, and
        # this is configurable in order to map exactly where.
        "optimization_goal": optimization_goal,
        "promoted_object": promoted,
        "daily_budget": budget_cents,
        "start_time": (now + timedelta(minutes=5)).isoformat(),
        "end_time": (midnight + timedelta(hours=ADSET_HOURS)).isoformat(),
        "targeting": {
            "geo_locations": {"countries": [country]},
            # adopt forces Advantage+ audience off unconditionally; match it so
            # we are not testing a different targeting regime than production.
            "targeting_automation": {"advantage_audience": 0},
        },
        "status": "PAUSED",
    }
    return adset


def build_campaign(name: str, variant: str) -> Dict[str, Any]:
    return {
        "name": name,
        "objective": "OUTCOME_ENGAGEMENT",
        "status": "PAUSED",
        # Multi-destination requires this empty; adopt already does the same.
        "special_ad_categories": [],
        # Meta rejects the create outright without this (subcode 4834011).
        # adopt/adopt/marketing.py:create_campaign sets it too — mirroring the
        # real payload is the point of this probe.
        "is_adset_budget_sharing_enabled": False,
    }


# --------------------------------------------------------------------- actions


def list_ads(account: AdAccount, campaign_id: str) -> None:
    from facebook_business.adobjects.campaign import Campaign
    ads = Campaign(campaign_id).get_ads(fields=["name", "creative", "status"])
    for a in ads:
        logger.info(f"{a['id']}  {a.get('status','?'):8}  {a.get('name','')}")


def template_from_ad(ad_id: str) -> Dict[str, Any]:
    """Pull image/copy off an existing ad so the probe looks like a real ad."""
    from facebook_business.adobjects.ad import Ad
    ad = Ad(ad_id).api_get(fields=["creative"])
    from facebook_business.adobjects.adcreative import AdCreative
    cid = ad["creative"]["id"]
    c = AdCreative(cid).api_get(fields=["object_story_spec", "image_hash", "name"])
    oss = c.get("object_story_spec", {}) or {}
    ld = oss.get("link_data", {}) or {}
    tpl = {
        "page_id": oss.get("page_id"),
        "image_hash": ld.get("image_hash") or c.get("image_hash"),
        "headline": ld.get("name"),
        "primary_text": ld.get("message"),
    }
    logger.info(f"template ad {ad_id}: {json.dumps(tpl, indent=2)}")
    return tpl


def read_back(api: FacebookAdsApi, ad_id: str) -> None:
    """What Meta actually STORED — run this before clicking anything.

    Meta can silently drop part of a payload at creation. If the combined blob
    lost its quick_replies array here, the click test is measuring a creative
    that never carried the thing under test.
    """
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.adset import AdSet

    ad = Ad(ad_id, api=api).api_get(
        fields=["name", "status", "effective_status", "adset_id", "creative",
                "preview_shareable_link"]).export_all_data()
    print("=== AD ===\n" + json.dumps(ad, indent=2, default=str))

    aset = AdSet(ad["adset_id"], api=api).api_get(
        fields=["name", "destination_type", "promoted_object", "optimization_goal",
                "billing_event", "status", "daily_budget", "start_time",
                "end_time", "campaign_id"]).export_all_data()
    print("\n=== ADSET ===\n" + json.dumps(aset, indent=2, default=str))

    cr = AdCreative(ad["creative"]["id"], api=api).api_get(
        fields=["name", "url_tags", "object_story_spec",
                "asset_feed_spec"]).export_all_data()
    print("\n=== CREATIVE ===\n" + json.dumps(cr, indent=2, default=str))

    ld = (cr.get("object_story_spec") or {}).get("link_data") or {}
    afs = cr.get("asset_feed_spec") or {}
    found = {"autofill_message": False, "quick_replies": False}
    for where, blob in [
        ("object_story_spec.link_data", ld.get("page_welcome_message")),
        ("asset_feed_spec.additional_data",
         (afs.get("additional_data") or {}).get("page_welcome_message")),
    ]:
        if not blob:
            print(f"\n=== page_welcome_message @ {where}: ABSENT ===")
            continue
        decoded = json.loads(blob)
        print(f"\n=== page_welcome_message @ {where} (decoded) ===")
        print(json.dumps(decoded, indent=2))
        # The two welcome shapes nest `message` differently: the multi/whatsapp
        # blob puts it under text_format, the plain Messenger blob puts it at the
        # top level. Looking only under text_format reported False for a
        # Messenger creative whose quick_replies were plainly present.
        msg = ((decoded.get("text_format") or {}).get("message")
               or decoded.get("message") or {})
        for key in found:
            here = key in msg
            found[key] = found[key] or here
            print(f"  {key} present: {here}")

    print("\n  url_tags present: " + repr(cr.get("url_tags")))

    # Report what was actually found. This previously printed the "both present"
    # conclusion unconditionally, which on the multi creative -- the one whose
    # answer decides the test -- would have claimed the combined blob survived
    # even if Meta had stripped a sub-structure.
    if found["autofill_message"] and found["quick_replies"]:
        print("\nBoth sub-structures present => the combined blob survived "
              "creation. That is API acceptance only; delivery is the click "
              "test.")
    elif found["autofill_message"] or found["quick_replies"]:
        missing = [k for k, v in found.items() if not v]
        print(f"\nONLY ONE sub-structure present -- missing: {missing}. For a "
              "multi-destination creative this means Meta did not store the "
              "combined blob, and that arm cannot route. For a single-"
              "destination control this is expected.")
    else:
        print("\nNEITHER sub-structure present. The welcome message carries no "
              "ref carrier at all; this creative cannot route on either arm.")


def preview(api: FacebookAdsApi, ad_id: str) -> None:
    """Get the shareable preview link. Open it on a PHONE — CTWA is mobile-only."""
    from facebook_business.adobjects.ad import Ad
    ad = Ad(ad_id, api=api).api_get(
        fields=["name", "preview_shareable_link"]).export_all_data()
    print(json.dumps(ad, indent=2, default=str))
    logger.info(
        "\nOpen that link ON A MOBILE DEVICE. Meta does not deliver a CTWA "
        "referral for WhatsApp Web/Desktop, so a desktop click can produce a "
        "false negative on question 3.\n"
        "Preview clicks produce genuine referrals with no activation, no ad "
        "review and no spend (measured 2026-08-16)."
    )


def _crdb(sql: str) -> str:
    res = subprocess.run(
        ["kubectl", "exec", "-n", CRDB_NS, CRDB_POD, "--", "./cockroach", "sql",
         "--insecure", "--database=chatroach", "-e", sql],
        capture_output=True, text=True,
    )
    return res.stdout or res.stderr


def capture(ref: str) -> None:
    """Find webhooks carrying our probe token and print their referral objects.

    NOTE: `messages` has 101M rows and its only indexes are userid-prefixed
    (PRIMARY KEY (hsh, userid), plus messages_userid_timestamp_idx). A LIKE
    over the whole table is a full scan and takes minutes. Prefer
    --capture-user once you know the userid; this exists for the case where you
    do not.
    """
    sql = (
        "SELECT timestamp, userid, content FROM messages "
        f"WHERE content LIKE '%{ref}%' ORDER BY timestamp DESC LIMIT 20"
    )
    logger.info("full-table scan of ~101M rows; this takes minutes...")
    print(_crdb(sql))
    logger.info(
        "\nA referral may arrive WITHOUT our token at all — that is itself a "
        "result. See the runbook's decision table before concluding anything "
        "from an empty response here."
    )


def capture_user(userid: str, minutes: int) -> None:
    """Everything one user sent/received in a window. Index-backed, instant.

    On WhatsApp `userid` is the tester's phone number as digits, no `+`
    (measured: userid `15419799714`). On Messenger it is the page-scoped PSID,
    which you cannot know in advance — find it with --find-arrivals.
    """
    sql = (
        "SELECT timestamp, content FROM messages "
        f"WHERE userid = '{userid}' "
        f"AND timestamp > now() - INTERVAL '{int(minutes)} minutes' "
        "ORDER BY timestamp ASC"
    )
    print(_crdb(sql))


def find_arrivals(page_id: str, phone_number_id: str, minutes: int) -> None:
    """Who arrived on our page/number recently, and where fly routed them.

    `states` is ~1M rows and cheap to scan; `messages` is not. So identify the
    userid here first, then pull the raw JSON with --capture-user.

    `pageid` is the Facebook Page id on Messenger and the WhatsApp
    phone_number_id on WhatsApp (measured: a CTWA arrival wrote pageid
    '1203867182815254'). `current_form` is a computed column over
    state_json->'forms'->>-1; if it reads '305' the arrival fell through to
    FALLBACK_FORM, which is what a lost routing token looks like.
    """
    sql = (
        "SELECT userid, pageid, platform, current_form, current_state, updated "
        "FROM states "
        f"WHERE pageid IN ('{page_id}', '{phone_number_id}') "
        f"AND updated > now() - INTERVAL '{int(minutes)} minutes' "
        "ORDER BY updated DESC"
    )
    print(_crdb(sql))
    logger.info(
        "\ncurrent_form = '305' means FALLBACK_FORM: the routing token did not "
        "survive. Note that a repeat entrant is a no-op rather than a start "
        "(machine.js _hasForm), so an absent row is not proof of anything — "
        "always read the raw referral with --capture-user."
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ad-account", default=DEFAULT_AD_ACCOUNT)
    p.add_argument("--credentials-key", default="virtual-lab-vlab")
    p.add_argument("--variant", choices=["messenger", "whatsapp", "multi"])
    p.add_argument("--mode", choices=["dry", "check", "create", "cleanup"], default="dry")
    p.add_argument("--template-ad", help="ad id to copy image/copy from")
    p.add_argument("--list-ads", metavar="CAMPAIGN_ID")
    p.add_argument("--page-id", default="1855355231229529", help="Virtual Lab page")
    p.add_argument("--phone-number-id", default="1203867182815254")

    # --- what the ad actually carries -------------------------------------
    # The routing token is now DERIVED from a shortcode and a creative name, by
    # the same serialisers vlab uses, instead of being a free string. A free
    # string is how the last probe shipped `ctwaprobe.alpha.creative.Ad1H.
    # form.probetest` — a format no vlab code has ever produced or ever will.
    p.add_argument("--shortcode", default="flysmoke",
                   help="survey shortcode the ad routes to. Default flysmoke: "
                        "it is a real production survey owned by us, so "
                        "end-to-end routing is observable for free. A "
                        "nonexistent shortcode routes to FALLBACK_FORM (305), "
                        "which is a real researcher's survey.")
    p.add_argument("--creative-name", default=None,
                   help="creative name carried in the ref as `creative.<name>`. "
                        "Default probe<Variant>. Make it unique per run so two "
                        "arms' tokens are distinguishable in the DB.")
    p.add_argument("--metadata", action="append", default=[], metavar="K=V",
                   help="extra stratum metadata folded into the ref, repeatable")
    p.add_argument("--ref-mode", choices=["full", "thin"], default="full",
                   help="full = make_ref / whatsapp_autofill with metadata "
                        "(what every live Messenger study ships, and the "
                        "strictly harder case for WhatsApp); thin = "
                        "form.<shortcode> only, which is vlab's WhatsApp "
                        "default but makes the two arms' tokens identical")
    p.add_argument("--allow-unsafe-tokens", action="store_true",
                   help="build even if a token would be percent-encoded. Do "
                        "not use for the delivery test: production fly rejects "
                        "%% and the result becomes uninterpretable.")
    p.add_argument("--ref", help="OVERRIDE the derived Messenger-grammar token")
    p.add_argument("--autofill", help="OVERRIDE the derived WhatsApp-grammar token")
    p.add_argument("--multi-fallback", choices=["messenger", "whatsapp"],
                   default="messenger",
                   help="--variant multi only: which app the single-valued "
                        "object_story_spec CTA names, and therefore which arm a "
                        "PREVIEW click reaches. 'messenger' is what vlab ships "
                        "and what was measured on 2026-08-17; 'whatsapp' is the "
                        "probe-only setting that makes the UNMEASURED WhatsApp "
                        "arm reachable without a second device or a live "
                        "activation. The ad set, the combined welcome blob and "
                        "the asset_feed_spec array are identical either way.")

    p.add_argument("--greeting", default="Welcome! Tap below to start the survey.")
    p.add_argument("--button", default="Start survey")
    p.add_argument("--country", default="US")
    p.add_argument("--headline", default="Virtual Lab test — not a live survey")
    p.add_argument("--primary-text",
                   default="Internal test ad for Virtual Lab research tooling. "
                           "This is not a real survey and offers no incentive.")
    p.add_argument("--budget-cents", type=int, default=200)
    # Measured 2026-08-16: the Virtual Lab Page is subject to European privacy
    # rules, which block CONVERSATIONS for click-to-WhatsApp outright
    # ("The goal Maximize number of conversations is not available..."). Also
    # measured: multi-destination accepts LINK_CLICKS despite Meta's guide
    # calling CONVERSATIONS mandatory. So LINK_CLICKS is the default that
    # actually creates on this Page.
    p.add_argument("--optimization-goal", default="LINK_CLICKS",
                   help="LINK_CLICKS (default; CONVERSATIONS is blocked on this "
                        "Page by EU privacy rules) | CONVERSATIONS | IMPRESSIONS")
    p.add_argument("--campaign", help="campaign id, for --mode cleanup")

    # --- read-only observation --------------------------------------------
    p.add_argument("--read-back", metavar="AD_ID",
                   help="print what Meta stored for this ad; run before clicking")
    p.add_argument("--preview", metavar="AD_ID",
                   help="print the shareable preview link")
    p.add_argument("--capture", metavar="REF", help="slow: full scan of messages")
    p.add_argument("--capture-user", metavar="USERID",
                   help="fast: all raw webhooks for one userid")
    p.add_argument("--find-arrivals", action="store_true",
                   help="who arrived on our page/number recently, from states")
    p.add_argument("--minutes", type=int, default=60,
                   help="window for --capture-user / --find-arrivals")
    args = p.parse_args()

    # DB-only actions: no Meta credentials needed.
    if args.capture:
        return capture(args.capture)
    if args.capture_user:
        return capture_user(args.capture_user, args.minutes)
    if args.find_arrivals:
        return find_arrivals(args.page_id, args.phone_number_id, args.minutes)

    token = token_from_prod(args.credentials_key)
    api = get_api(token)
    account = AdAccount(args.ad_account, api=api)

    if args.list_ads:
        return list_ads(account, args.list_ads)

    if args.read_back:
        return read_back(api, args.read_back)

    if args.preview:
        return preview(api, args.preview)

    if args.mode == "cleanup":
        if not args.campaign:
            raise SystemExit("--mode cleanup needs --campaign <id>")
        from facebook_business.adobjects.campaign import Campaign
        Campaign(args.campaign, api=api).api_delete()
        logger.info(f"deleted campaign {args.campaign}")
        return

    if not args.variant:
        raise SystemExit("--variant is required")

    # --- derive the two routing tokens, exactly as vlab would ---------------
    creative_name = args.creative_name or f"probe{args.variant.capitalize()}"
    stratum_md: Dict[str, str] = {}
    for pair in args.metadata:
        k, _, v = pair.partition("=")
        if not v:
            raise SystemExit(f"--metadata wants K=V, got {pair!r}")
        stratum_md[k] = v

    md = creative_metadata(args.shortcode, stratum_md)
    checked = {"shortcode": args.shortcode, "creative": creative_name,
               **{f"metadata.{k}": v for k, v in stratum_md.items()}}
    assert_pattern_safe(checked, args.allow_unsafe_tokens)

    if args.ref_mode == "full":
        derived_ref = make_ref(creative_name, md)
        derived_autofill = whatsapp_autofill(
            args.shortcode, ref_metadata(creative_name, md))
    else:
        derived_ref = shortcode_ref(args.shortcode)
        derived_autofill = whatsapp_autofill(args.shortcode)

    ref = args.ref or derived_ref
    autofill = args.autofill or derived_autofill

    logger.info(f"messenger ref (url_tags + quick_reply.payload): {ref}")
    logger.info(f"whatsapp autofill (compose box):                {autofill}")

    tpl = template_from_ad(args.template_ad) if args.template_ad else {}
    page_id = args.page_id or tpl.get("page_id")

    wa = (whatsapp_number_from_prod(args.phone_number_id)
          if args.variant in ("whatsapp", "multi") else {})
    if wa:
        logger.info(f"whatsapp number: {wa}")

    name = f"ctwa-probe-{args.variant}-{creative_name}"
    campaign = build_campaign(name, args.variant)
    creative = build_creative(args.variant, tpl, page_id, ref,
                              args.greeting, args.button, autofill,
                              args.headline, args.primary_text, name,
                              args.multi_fallback)
    adset = build_adset(args.variant, "<CAMPAIGN_ID>", page_id, name,
                        args.budget_cents, args.country,
                        wa.get("whatsapp_phone_number"), args.optimization_goal)

    if args.mode == "dry":
        print("\n=== CAMPAIGN ===\n" + json.dumps(campaign, indent=2))
        print("\n=== ADSET ===\n" + json.dumps(adset, indent=2))
        print("\n=== CREATIVE ===\n" + json.dumps(creative, indent=2))
        print("\n(page_welcome_message is a JSON string; decoded for review:)")
        pwm = creative["object_story_spec"]["link_data"].get("page_welcome_message")
        if pwm:
            print(json.dumps(json.loads(pwm), indent=2))
        print("\nNothing was sent to Facebook. Use --mode check or --mode create.")
        return

    # --- live from here ---
    try:
        c = account.create_campaign(params=campaign)
        campaign_id = c["id"]
        logger.info(f"campaign {campaign_id}")
    except FacebookRequestError as e:
        logger.error("CAMPAIGN FAILED")
        logger.error(f"  message:  {e.api_error_message()}")
        logger.error(f"  type:     {e.api_error_type()}")
        logger.error(f"  code:     {e.api_error_code()}  subcode: {e.api_error_subcode()}")
        logger.error(f"  user_msg: {e.get_message()}")
        logger.error(f"  body:     {json.dumps(e.body(), indent=2)}")
        raise SystemExit(1)

    adset["campaign_id"] = campaign_id
    try:
        a = account.create_ad_set(params=adset)
        logger.info(f"adset {a['id']}")
    except FacebookRequestError as e:
        # This is the informative failure: it is where a missing page/number
        # binding, a bad destination_type, or a rejected optimization_goal
        # surfaces. Print everything Meta gives us.
        logger.error("ADSET FAILED — this is the interesting error")
        logger.error(f"  message:  {e.api_error_message()}")
        logger.error(f"  type:     {e.api_error_type()}")
        logger.error(f"  code:     {e.api_error_code()}  subcode: {e.api_error_subcode()}")
        logger.error(f"  user_msg: {e.get_message()}")
        logger.error(f"  body:     {json.dumps(e.body(), indent=2)}")
        logger.error(f"\n  cleanup:  --mode cleanup --campaign {campaign_id}")
        raise SystemExit(1)

    if args.mode == "check":
        logger.info(f"\nadset accepted. cleanup: --mode cleanup --campaign {campaign_id}")
        return

    try:
        cr = account.create_ad_creative(params=creative)
        logger.info(f"creative {cr['id']}")
        ad = account.create_ad(params={"name": name, "adset_id": a["id"],
                                       "creative": {"creative_id": cr["id"]},
                                       "status": "PAUSED"})
        logger.info(f"ad {ad['id']}")
    except FacebookRequestError as e:
        logger.error(f"CREATIVE/AD FAILED: {e.api_error_message()}")
        logger.error(f"  code: {e.api_error_code()} subcode: {e.api_error_subcode()}")
        logger.error(f"  cleanup: --mode cleanup --campaign {campaign_id}")
        raise SystemExit(1)

    logger.info(
        f"\nCreated PAUSED. Do NOT activate — preview clicks produce genuine\n"
        f"referrals with no ad review and no spend (measured 2026-08-16).\n\n"
        f"  1. ctwa_probe.py --read-back {ad['id']}\n"
        f"       confirm both autofill_message and quick_replies survived\n"
        f"  2. ctwa_probe.py --preview {ad['id']}\n"
        f"       open the link ON A PHONE, one arm at a time\n"
        f"  3. record the compose box / welcome screen BEFORE sending\n"
        f"  4. ctwa_probe.py --find-arrivals --minutes 30\n"
        f"     ctwa_probe.py --capture-user <userid> --minutes 30\n"
        f"  5. ctwa_probe.py --mode cleanup --campaign {campaign_id}\n\n"
        f"messenger ref: {ref}\n"
        f"whatsapp autofill: {autofill}\n"
        f"ad id: {ad['id']}   (referrals carry the AD id, never the campaign id)"
    )


if __name__ == "__main__":
    main()
