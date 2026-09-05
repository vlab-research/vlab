"""Tests for `authoring/templates.py`.

WHERE THE MOCK BOUNDARY IS. `FacebookAdsApi.call` -- the one method that puts
bytes on the wire -- exactly as `server/test_meta.py` mocks it, and nothing
above it. So every test drives the real planner, the real placeholder
substitution, the real refusals and the real `FacebookSession` construction;
only the HTTP request to graph.facebook.com is fake. No database is touched by
anything in this file.

THE TEST THAT MATTERS is `test_a_built_creative_deploys_through_the_runtime`
and its mismatch twin. Everything else here checks that the planner does what
it says; those two check the thing this module exists for -- that a creative
this library builds, stored as a `CreativeConf.template`, survives
`refuse_template_destination_conflicts` and comes out of
`marketing.create_creative` as a deployable ad. A template that plans
beautifully and is refused at run time would be worse than no library at all.

ONE ASSUMPTION IS MADE ABOUT META and it is marked at `_as_meta_returns_it`:
that a creative created with `object_story_spec.page_id` reads back with
`actor_id` set to that Page. It is documented Graph behaviour and it is what
every stored template in production looks like, but it was not verified live
from this branch. If it is wrong, `apply` already warns (it checks the
read-back against `REQUIRED_TEMPLATE_CREATIVE_FIELDS`) rather than shipping a
template that would KeyError in `audiences.py`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

from ..marketing import (
    _create_creative,
    create_creative,
    messenger_call_to_action,
    refuse_template_destination_conflicts,
)
from ..meta_fields import CREATIVE_FIELD_LIST, REQUIRED_TEMPLATE_CREATIVE_FIELDS
from ..study_conf import (
    AppDestination,
    CreativeConf,
    DestinationRecruitmentExperiment,
    FlyMessengerDestination,
    FlyMultiDestination,
    FlyWhatsAppDestination,
    GeneralConf,
    Stratum,
    StudyConf,
    UserInfo,
    WebDestination,
    destination_type_for,
)
from . import templates as tp

PAGE = "1855355231229529"  # Virtual Lab, the Page every production template uses
ACCOUNT = "act_1342820622846299"

# Kwara, resolved from Meta's own /search endpoint on 2026-08-27:
#   type=adgeolocation location_types=["region"] q=Kwara country_code=NG
#   -> key=2619 name='Kwara' country=NG type=region
# Hardcoded rather than looked up so a rerun cannot silently pick a different
# region if Meta's search ranking changes.
KWARA = {"key": "2619", "name": "Kwara", "country": "NG"}


def _targeting(genders: List[int]) -> Dict[str, Any]:
    return {
        "genders": genders,
        "age_min": 18,
        "age_max": 65,
        "geo_locations": {
            "regions": [KWARA],
            "location_types": ["home", "recent"],
        },
    }


def _adsets(kind: str = tp.MESSENGER, promoted_object=None) -> List[tp.AdsetSpec]:
    return [
        tp.AdsetSpec(
            name=f"Kwara - {label}",
            targeting=_targeting(genders),
            kind=kind,
            promoted_object=promoted_object,
        )
        for label, genders in (("Men", [1]), ("Women", [2]))
    ]


def _ad(kind: str = tp.MESSENGER, **kw) -> tp.AdSpec:
    defaults: Dict[str, Any] = dict(
        name="vlpulse-ng-1",
        kind=kind,
        page_id=PAGE,
        message="Tell us what you think. It takes about three minutes.",
        headline="Chat with us",
        description="₦500 in airtime",
        image_hash="7fabd5c7072f2242195f6f5dbbfb512c",
    )
    if kind == tp.WEB:
        defaults["link"] = "https://survey.example/start"
    if kind == tp.APP:
        defaults["link"] = "https://play.google.com/store/apps/details?id=x"
        defaults["deeplink"] = "myapp://survey?ref={ref}"
    defaults.update(kw)
    return tp.AdSpec(**defaults)


# ---------------------------------------------------------------------------
# The mocked Graph boundary -- lifted from server/test_meta.py
# ---------------------------------------------------------------------------


class _Response:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


class _Graph:
    """Records the calls made, replays canned bodies keyed on (method, edge).

    Keyed rather than a flat queue because `apply` interleaves creates with a
    creative read-back, and a queue would make every test depend on that
    interleaving -- which is exactly the implementation detail a test should be
    free to change.
    """

    def __init__(self, bodies: Dict[str, Any]):
        self.bodies = {k: list(v) for k, v in bodies.items()}
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, api_self, method, path, params=None, files=None, **kwargs):
        joined = "/".join(str(p) for p in path)
        self.calls.append(
            {
                "method": method,
                "path": joined,
                "params": dict(params or {}),
                "files": sorted((files or {}).keys()),
            }
        )
        key = f"{method} {joined.rsplit('/', 1)[-1]}"
        queue = self.bodies.get(key)
        if not queue:
            queue = self.bodies.get(method) or []
        body = queue.pop(0) if queue else {"id": f"auto-{len(self.calls)}"}
        if isinstance(body, BaseException):
            raise body
        return _Response(body)

    def posted(self, edge: str) -> List[Dict[str, Any]]:
        return [
            c["params"]
            for c in self.calls
            if c["method"] == "POST" and c["path"].endswith("/" + edge)
        ]


def _graph(**bodies):
    g = _Graph(bodies)

    # A plain function, not the recorder itself: setting a non-function object
    # as a class attribute skips the descriptor protocol, so `api.call(...)`
    # would be invoked with no `self` and every argument position would shift.
    def _call(api_self, method, path, params=None, files=None, **kwargs):
        return g(api_self, method, path, params=params, files=files, **kwargs)

    return patch.object(FacebookAdsApi, "call", _call), g


@pytest.fixture
def api():
    from ..facebook.state import api_for_token

    return api_for_token("TEST-TOKEN", "app-id", "app-secret")


def _as_meta_returns_it(sent: Dict[str, Any], creative_id="120000000000000001"):
    """What `GET /<creative>?fields=…` gives back for a creative we just sent.

    ASSUMPTION, marked because it is the one thing here that is not read out of
    this repository: Meta derives `actor_id` from `object_story_spec.page_id`
    and returns it on read even though it was not sent. That is documented
    Graph behaviour and it is the shape of every stored template in production
    (`creatives[].template.actor_id` is populated on studies whose templates
    were built in Ads Manager, and `audiences.py:150` has relied on it for
    years) -- but it was not verified live from this branch.
    """
    return {
        "id": creative_id,
        "name": sent["name"],
        "actor_id": sent["object_story_spec"]["page_id"],
        "object_story_spec": sent["object_story_spec"],
        **(
            {"asset_feed_spec": sent["asset_feed_spec"]}
            if "asset_feed_spec" in sent
            else {}
        ),
    }


# ---------------------------------------------------------------------------
# The plan is data, and it is stable
# ---------------------------------------------------------------------------


def test_the_plan_for_a_messenger_campaign_is_byte_stable():
    """The whole plan, as a literal.

    A golden test rather than a set of field assertions, on purpose: this is
    what gets created on somebody's ad account, and the value of a plan is that
    a reviewer can read it. A diff here is a change in what vlab builds, and
    should be looked at even when every other test still passes.
    """
    plan = tp.plan_template_campaign(
        account_id="1342820622846299",
        name="VL Pulse Nigeria",
        adsets=_adsets(),
        ads=[_ad()],
    )

    assert json.loads(plan.to_json()) == {
        "account_id": "act_1342820622846299",
        "campaign_name": "Templates - VL Pulse Nigeria",
        "campaign_id": None,
        "properties": ["genders", "age_min", "age_max", "geo_locations"],
        "seed": {},
        "warnings": [
            "Ad set 'Kwara - Men': Meta will add 'frequently_in' to "
            "geo_locations.location_types (['home', 'recent']) and it cannot be "
            "removed (measured 2026-08-27). Region targeting therefore reaches "
            "people who frequently visit the region as well as residents. State "
            "that in the study's write-up.",
            "Ad set 'Kwara - Men': Meta canonicalises region names on write "
            "('Kwara' -> 'Kwara State'), so the stored targeting will not be "
            "byte-identical to this plan.",
            "Ad set 'Kwara - Women': Meta will add 'frequently_in' to "
            "geo_locations.location_types (['home', 'recent']) and it cannot be "
            "removed (measured 2026-08-27). Region targeting therefore reaches "
            "people who frequently visit the region as well as residents. State "
            "that in the study's write-up.",
            "Ad set 'Kwara - Women': Meta canonicalises region names on write "
            "('Kwara' -> 'Kwara State'), so the stored targeting will not be "
            "byte-identical to this plan.",
        ],
        "creates": [
            {
                "ref": "campaign",
                "node": "campaign",
                "edge": "campaigns",
                "params": {
                    "name": "Templates - VL Pulse Nigeria",
                    "objective": "OUTCOME_ENGAGEMENT",
                    "status": "PAUSED",
                    "special_ad_categories": [],
                    "is_adset_budget_sharing_enabled": False,
                },
            },
            {
                "ref": "adset:Kwara - Men",
                "node": "adset",
                "edge": "adsets",
                "params": {
                    "name": "Kwara - Men",
                    "campaign_id": "${vlab:campaign}",
                    "optimization_goal": "CONVERSATIONS",
                    "billing_event": "IMPRESSIONS",
                    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    "daily_budget": 2000,
                    "destination_type": "MESSENGER",
                    "targeting": {
                        "genders": [1],
                        "age_min": 18,
                        "age_max": 65,
                        "geo_locations": {
                            "regions": [KWARA],
                            "location_types": ["home", "recent"],
                        },
                        "targeting_automation": {"advantage_audience": 0},
                    },
                    "status": "PAUSED",
                },
            },
            {
                "ref": "adset:Kwara - Women",
                "node": "adset",
                "edge": "adsets",
                "params": {
                    "name": "Kwara - Women",
                    "campaign_id": "${vlab:campaign}",
                    "optimization_goal": "CONVERSATIONS",
                    "billing_event": "IMPRESSIONS",
                    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    "daily_budget": 2000,
                    "destination_type": "MESSENGER",
                    "targeting": {
                        "genders": [2],
                        "age_min": 18,
                        "age_max": 65,
                        "geo_locations": {
                            "regions": [KWARA],
                            "location_types": ["home", "recent"],
                        },
                        "targeting_automation": {"advantage_audience": 0},
                    },
                    "status": "PAUSED",
                },
            },
            {
                "ref": "creative:vlpulse-ng-1",
                "node": "creative",
                "edge": "adcreatives",
                "params": {
                    "name": "vlpulse-ng-1",
                    "object_story_spec": {
                        "page_id": PAGE,
                        "link_data": {
                            "image_hash": "7fabd5c7072f2242195f6f5dbbfb512c",
                            "message": (
                                "Tell us what you think. It takes about three "
                                "minutes."
                            ),
                            "link": "https://fb.com/messenger_doc/",
                            "call_to_action": {
                                "type": "MESSAGE_PAGE",
                                "value": {"app_destination": "MESSENGER"},
                            },
                            "name": "Chat with us",
                            "description": "₦500 in airtime",
                        },
                    },
                    "asset_feed_spec": {
                        "optimization_type": "DOF_MESSAGING_DESTINATION",
                        "call_to_actions": [
                            {
                                "type": "MESSAGE_PAGE",
                                "value": {
                                    "app_destination": "MESSENGER",
                                    "link": "https://fb.com/messenger_doc/",
                                },
                            }
                        ],
                    },
                },
            },
            {
                "ref": "ad:vlpulse-ng-1",
                "node": "ad",
                "edge": "ads",
                "params": {
                    "name": "vlpulse-ng-1",
                    "adset_id": "${vlab:adset:Kwara - Men}",
                    "creative": {"creative_id": "${vlab:creative:vlpulse-ng-1}"},
                    "status": "PAUSED",
                },
            },
        ],
    }


def test_planning_twice_gives_the_same_bytes():
    """Purity, asserted rather than assumed. No clock, no ids, no set order."""
    kw = dict(
        account_id=ACCOUNT,
        name="Repeatable",
        adsets=_adsets(),
        ads=[_ad(), _ad(name="vlpulse-ng-2", adset="Kwara - Women")],
    )
    assert (
        tp.plan_template_campaign(**kw).to_json()
        == tp.plan_template_campaign(**kw).to_json()
    )


@pytest.mark.parametrize("kind", tp.CREATIVE_KINDS)
def test_every_planned_object_is_paused(kind):
    """The invariant the whole module rests on.

    Checked over every node type that HAS a status (creatives and images do
    not) and over every kind, because a status is one keyword argument away
    from being wrong and nothing else in the system would notice: adopt does
    not read template campaigns, so a delivering template spends money quietly
    until someone reads the billing.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Paused",
        adsets=_adsets(kind, promoted_object={"page_id": PAGE}),
        ads=[_ad(kind)],
    )
    statuses = [
        (c.node, c.params.get("status"))
        for c in plan.creates
        if c.node in ("campaign", "adset", "ad")
    ]
    assert statuses, "nothing was planned"
    assert all(s == "PAUSED" for _, s in statuses), statuses


def test_the_budget_ceiling_refuses_a_plan_rather_than_clamping_it():
    """Refused, not clamped. A clamp silently ignores what the caller asked for,
    and the interesting case is a typo -- 200000 for 2000 -- where quietly
    substituting a different number hides the mistake instead of surfacing it.
    """
    with pytest.raises(tp.TemplatePlanError, match="above the template ceiling"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Rich",
            adsets=[
                tp.AdsetSpec(
                    name="a",
                    targeting=_targeting([1]),
                    daily_budget=tp.MAX_DAILY_BUDGET + 1,
                )
            ],
        )


def test_a_missing_declared_property_fails_at_plan_time():
    """The dashboard's `PropertyMissingError`, moved to where it can be fixed.

    Without this the failure is a React error in the Variables form, hours
    later, with the template already on the account.
    """
    with pytest.raises(tp.TemplatePlanError, match="no 'geo_locations'"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Ungeo",
            adsets=[tp.AdsetSpec(name="a", targeting={"genders": [1], "age_min": 18})],
            properties=["genders", "age_min", "geo_locations"],
        )


def test_declaring_targeting_automation_is_a_warning_not_an_error():
    """The correction to `make_template_campaign.py`'s advice.

    Declaring it is legal, does nothing useful, and pins the dashboard's
    "properties drifted" banner on. See `DEFAULT_PROPERTIES`.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Declares TA",
        adsets=_adsets(),
        properties=list(tp.DEFAULT_PROPERTIES) + ["targeting_automation"],
    )
    assert any("banner on this variable forever" in w for w in plan.warnings)


def test_advantage_audience_is_off_on_every_planned_adset():
    """Off, deliberately, and set on the template as well as forced on extract.

    Left on, Meta's Advantage audience expansion is ON by default and delivery
    leaks outside the stratum -- which for a geographically stratified study
    means respondents from outside the region counted inside it.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="AA", adsets=_adsets(), ads=[_ad()]
    )
    automations = [
        c.params["targeting"]["targeting_automation"]
        for c in plan.creates
        if c.node == "adset"
    ]
    assert automations == [{"advantage_audience": 0}] * 2


def test_the_campaign_declares_is_adset_budget_sharing_enabled():
    """MEASURED: omitting it is a 400 with error_subcode 4834011 whenever the
    campaign carries no budget of its own, which a template never does.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="Budgets", adsets=_adsets()
    )
    campaign = next(c for c in plan.creates if c.node == "campaign")
    assert campaign.params["is_adset_budget_sharing_enabled"] is False


def test_the_marker_is_added_and_not_doubled():
    assert tp.template_campaign_name("Foo") == "Templates - Foo"
    assert tp.template_campaign_name("Templates - Foo") == "Templates - Foo"
    assert tp.is_template_campaign("Templates - Foo")
    assert not tp.is_template_campaign("Foo")
    assert not tp.is_template_campaign(None)


def test_two_adsets_with_one_name_are_refused():
    with pytest.raises(tp.TemplatePlanError, match="Two ad sets named"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Dupes",
            adsets=[
                tp.AdsetSpec(name="a", targeting=_targeting([1])),
                tp.AdsetSpec(name="a", targeting=_targeting([2])),
            ],
        )


def test_two_ads_with_one_name_are_refused():
    """The creative name is a join key: `mint_ref_token` is keyed on it and
    reconciliation matches ads by it.
    """
    with pytest.raises(tp.TemplatePlanError, match="join key"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Dupes",
            adsets=_adsets(),
            ads=[_ad(), _ad()],
        )


def test_a_whatsapp_adset_takes_its_page_from_the_ads_it_carries():
    """`promoted_object.page_id` and the creative's page can never disagree,
    because there is one source: the ad. That is the same rule
    `promoted_object_for` follows at run time via `template_page_id`.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="CTWA",
        adsets=[tp.AdsetSpec(name="a", targeting=_targeting([1]), kind=tp.WHATSAPP)],
        ads=[_ad(tp.WHATSAPP)],
    )
    adset = next(c for c in plan.creates if c.node == "adset")
    assert adset.params["promoted_object"] == {"page_id": PAGE}
    assert adset.params["destination_type"] == "WHATSAPP"


def test_a_whatsapp_adset_with_no_ad_and_no_page_is_refused():
    with pytest.raises(tp.TemplatePlanError, match="promoted_object.page_id"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="CTWA",
            adsets=[
                tp.AdsetSpec(name="a", targeting=_targeting([1]), kind=tp.WHATSAPP)
            ],
        )


def test_the_kind_to_destination_type_map_agrees_with_the_runtime():
    """One definition of the ad-set enum, checked against the other reader.

    `destination_type_for` takes a `DestinationConf` and this takes a kind
    string; they cannot be the same function, so they are asserted equal for
    every destination class instead.
    """
    cases = {
        tp.MESSENGER: FlyMessengerDestination(
            type="messenger",
            name="m",
            initial_shortcode="sc",
            welcome_message="hi",
            button_text="go",
        ),
        tp.WHATSAPP: FlyWhatsAppDestination(
            type="whatsapp",
            name="w",
            initial_shortcode="sc",
            welcome_message="hi",
            whatsapp_phone_number="+15419202635",
        ),
        tp.MULTI: FlyMultiDestination(
            type="multi",
            name="x",
            initial_shortcode="sc",
            welcome_message="hi",
            button_text="go",
            whatsapp_phone_number="+15419202635",
        ),
        tp.WEB: WebDestination(
            type="web", name="web", url_template="https://e/?r={ref}"
        ),
        tp.APP: AppDestination(
            type="app",
            name="app",
            facebook_app_id="1",
            app_install_link="https://store",
            deeplink_template="app://{ref}",
            app_install_state="not_installed",
            user_device=["android"],
            user_os=["Android"],
        ),
    }
    assert set(cases) == set(tp.CREATIVE_KINDS)
    for kind, dest in cases.items():
        assert tp.DESTINATION_TYPE_BY_KIND[kind] == destination_type_for(dest)


# ---------------------------------------------------------------------------
# The creative builder
# ---------------------------------------------------------------------------


def test_a_web_creative_puts_the_link_where_meta_wants_it():
    c = tp.build_creative(
        tp.WEB,
        name="w",
        page_id=PAGE,
        message="m",
        image_hash="h",
        link="https://survey.example/start",
    )
    link_data = c["object_story_spec"]["link_data"]
    assert link_data["link"] == "https://survey.example/start"
    assert link_data["call_to_action"] == {
        "type": "OPEN_LINK",
        "value": {"link": "https://survey.example/start"},
    }
    # No messaging destination to declare, so no asset_feed_spec.
    assert "asset_feed_spec" not in c


def test_an_app_creative_carries_the_install_cta_and_the_store_link():
    c = tp.build_creative(
        tp.APP,
        name="a",
        page_id=PAGE,
        message="m",
        image_hash="h",
        link="https://play.google.com/x",
        deeplink="myapp://survey?ref={ref}",
    )
    assert c["object_story_spec"]["link_data"]["call_to_action"] == {
        "type": "INSTALL_MOBILE_APP",
        "value": {"app_link": "myapp://survey?ref={ref}"},
    }
    assert c["object_story_spec"]["link_data"]["link"] == "https://play.google.com/x"


def test_a_multi_creative_carries_metas_two_destination_array():
    c = tp.build_creative(tp.MULTI, name="x", page_id=PAGE, message="m", image_hash="h")
    afs = c["asset_feed_spec"]
    assert afs["optimization_type"] == "DOF_MESSAGING_DESTINATION"
    assert {cta["value"]["app_destination"] for cta in afs["call_to_actions"]} == {
        "MESSENGER",
        "WHATSAPP",
    }
    # The single-valued CTA stays MESSAGE_PAGE, Meta's documented fallback.
    assert (
        c["object_story_spec"]["link_data"]["call_to_action"]
        == messenger_call_to_action()
    )


def test_a_video_creative_uses_video_data_and_spells_the_headline_title():
    c = tp.build_creative(
        tp.MESSENGER,
        name="v",
        page_id=PAGE,
        message="m",
        headline="H",
        video_id="99",
    )
    video = c["object_story_spec"]["video_data"]
    assert video["video_id"] == "99"
    assert video["title"] == "H"
    assert "link_data" not in c["object_story_spec"]


def test_a_creative_with_neither_an_image_nor_a_video_is_refused():
    with pytest.raises(tp.TemplatePlanError, match="exactly one"):
        tp.build_creative(tp.MESSENGER, name="x", page_id=PAGE, message="m")


def test_a_creative_with_both_an_image_and_a_video_is_refused():
    with pytest.raises(tp.TemplatePlanError, match="exactly one"):
        tp.build_creative(
            tp.MESSENGER,
            name="x",
            page_id=PAGE,
            message="m",
            image_hash="h",
            video_id="9",
        )


def test_a_creative_with_no_page_is_refused():
    with pytest.raises(tp.TemplatePlanError, match="page_id is required"):
        tp.build_creative(
            tp.MESSENGER, name="x", page_id="", message="m", image_hash="h"
        )


def test_declare_destination_can_be_turned_off():
    c = tp.build_creative(
        tp.MESSENGER,
        name="x",
        page_id=PAGE,
        message="m",
        image_hash="h",
        declare_destination=False,
    )
    assert "asset_feed_spec" not in c


# ---------------------------------------------------------------------------
# THE test: does what we build actually deploy?
# ---------------------------------------------------------------------------


def _study(destinations, creatives):
    return StudyConf(
        id="00000000-0000-0000-0000-000000000001",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account=ACCOUNT,
            opt_window=48,
        ),
        destinations=destinations,
        audiences=[],
        creatives=creatives,
        strata=[],
        recruitment=DestinationRecruitmentExperiment(
            ad_campaign_name_base="test-campaign",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="CONVERSATIONS",
            min_budget=1,
            budget_per_arm=100,
            max_sample_per_arm=100,
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 8, 1),
            destinations=[d.name for d in destinations],
        ),
    )


DESTINATIONS = {
    tp.MESSENGER: FlyMessengerDestination(
        type="messenger",
        name="mess",
        initial_shortcode="ngpulse",
        welcome_message="Hi! Tap to start.",
        button_text="Start",
    ),
    tp.WHATSAPP: FlyWhatsAppDestination(
        type="whatsapp",
        name="wa",
        initial_shortcode="ngpulse",
        welcome_message="Hi! Send the message to start.",
        whatsapp_phone_number="+15419202635",
    ),
    tp.MULTI: FlyMultiDestination(
        type="multi",
        name="both",
        initial_shortcode="ngpulse",
        welcome_message="Hi! Tap to start.",
        button_text="Start",
        whatsapp_phone_number="+15419202635",
    ),
    tp.WEB: WebDestination(
        type="web", name="web", url_template="https://survey.example/?r={ref}"
    ),
    tp.APP: AppDestination(
        type="app",
        name="app",
        facebook_app_id="123",
        app_install_link="https://play.google.com/store/apps/details?id=x",
        deeplink_template="myapp://survey?ref={ref}",
        app_install_state="not_installed",
        user_device=["android"],
        user_os=["Android"],
    ),
}


def _template_for(kind: str) -> Dict[str, Any]:
    """A creative this library builds, in the shape a study would store it."""
    return _as_meta_returns_it(
        tp.build_creative(
            kind,
            name="vlpulse-ng-1",
            page_id=PAGE,
            message="Tell us what you think.",
            headline="Chat with us",
            image_hash="7fabd5c7072f2242195f6f5dbbfb512c",
            link=(
                "https://survey.example/start"
                if kind == tp.WEB
                else "https://play.google.com/store/apps/details?id=x"
                if kind == tp.APP
                else None
            ),
            deeplink="myapp://survey?ref={ref}" if kind == tp.APP else None,
        )
    )


@pytest.mark.parametrize("kind", tp.CREATIVE_KINDS)
def test_a_built_creative_deploys_through_the_runtime(kind):
    """THE test. Build a creative, store it as a template, deploy it.

    `create_creative` is the real run-path entry point: it calls
    `refuse_template_destination_conflicts`, mints the ref, builds the welcome
    message and calls `_create_creative`. Nothing here is stubbed except the
    Meta network, which `create_creative` does not touch at all.

    What is asserted is what a deployed ad must have: the researcher's copy and
    image survived, the destination's CTA was injected, and (for messaging) the
    ref reached its carriers. A template that failed any of those would plan
    cleanly and produce an ad that recruits nobody.
    """
    destination = DESTINATIONS[kind]
    config = CreativeConf(
        name="vlpulse-ng-1", destination=destination.name, template=_template_for(kind)
    )
    study = _study([destination], [config])
    stratum = Stratum(
        id="Gender:Men",
        quota=1.0,
        creatives=[config],
        facebook_targeting={},
        metadata={"Gender": "Men"},
    )

    creative = create_creative(study, stratum, config, destination)

    story = creative["object_story_spec"]
    assert story["page_id"] == PAGE
    link_data = story["link_data"]
    # The researcher's half, copied verbatim.
    assert link_data["image_hash"] == "7fabd5c7072f2242195f6f5dbbfb512c"
    assert link_data["message"] == "Tell us what you think."
    assert link_data["name"] == "Chat with us"
    # The study conf's half, injected.
    assert link_data["call_to_action"]["type"] in {
        "MESSAGE_PAGE",
        "WHATSAPP_MESSAGE",
        "OPEN_LINK",
        "INSTALL_MOBILE_APP",
    }
    assert creative["name"] == "vlpulse-ng-1"

    if kind in (tp.MESSENGER, tp.MULTI):
        assert "ref=creative.vlpulse-ng-1" in creative["url_tags"]
    if kind in tp.MESSAGING_KINDS:
        assert "page_welcome_message" in link_data


def _mismatches():
    """(template kind, destination kind) pairs the runtime must refuse.

    Only pairs where the TEMPLATE ITSELF states a destination -- which is the
    three messaging kinds, via the `asset_feed_spec` `build_creative` emits.
    A web or app template states no messaging destination at all, so
    `refuse_template_destination_conflicts` has nothing to compare and lets
    every pairing through; that is not an oversight in this module, it is the
    documented shape of the check (`have` empty means "an ordinary Advantage+
    or plain image template. Nothing to disagree with"), and it is recorded as
    a known gap in planning/template-authoring.md.
    """
    return [
        (tp.MESSENGER, tp.WHATSAPP),
        (tp.MESSENGER, tp.MULTI),
        (tp.WHATSAPP, tp.MESSENGER),
        (tp.WHATSAPP, tp.MULTI),
        (tp.MULTI, tp.MESSENGER),
        (tp.MULTI, tp.WHATSAPP),
        (tp.MULTI, tp.WEB),
        (tp.MULTI, tp.APP),
    ]


@pytest.mark.parametrize("template_kind,destination_kind", _mismatches())
def test_a_template_pointed_at_the_wrong_destination_is_refused(
    template_kind, destination_kind
):
    """The half of the contract that protects a researcher from themselves.

    Meta's own rejection for this is subcode 2490279, "Inconsistent Campaign
    Destination Type With App Destination", and it names neither the template
    nor the creative -- which is why it costs hours and why this check exists.
    """
    destination = DESTINATIONS[destination_kind]
    config = CreativeConf(
        name="c",
        destination=destination.name,
        template=_template_for(template_kind),
    )
    with pytest.raises(Exception, match="asset_feed_spec|optimization_type"):
        refuse_template_destination_conflicts(config, destination)


@pytest.mark.parametrize("kind", tp.MESSAGING_KINDS)
def test_the_matching_destination_is_not_refused(kind):
    destination = DESTINATIONS[kind]
    config = CreativeConf(
        name="c", destination=destination.name, template=_template_for(kind)
    )
    refuse_template_destination_conflicts(config, destination)  # must not raise


@pytest.mark.parametrize("kind", tp.CREATIVE_KINDS)
def test_a_built_template_is_readable_by_the_runtimes_own_reader(kind):
    """`_create_creative` runs over the built template without raising.

    Deliberately NOT named "carries every field the runtime reads", which is
    what it was called until review pointed out that half of it was circular:
    `_as_meta_returns_it` constructs `actor_id` and the `CREATIVE_FIELD_LIST`
    subset, so asserting them back is asserting the fixture. The Meta read-back
    shape is an ASSUMPTION (see that helper) and `apply` warns at run time
    rather than trusting it; what is genuinely testable here is that the
    BUILDER's output survives the runtime's reader, and that is the last line.

    The two names in `REQUIRED_TEMPLATE_CREATIVE_FIELDS` are asserted anyway,
    because they encode which fields are indexed with no guard -- `actor_id` is
    a bare `KeyError` in `audiences.hydrate_audiences` and
    `object_story_spec` is indexed unconditionally here. Everything else on
    `CREATIVE_FIELD_LIST` is copied only `if field in config.template`.
    """
    template = _template_for(kind)
    for f in REQUIRED_TEMPLATE_CREATIVE_FIELDS:
        assert template.get(f), f
    assert set(template) <= set(CREATIVE_FIELD_LIST), set(template) - set(
        CREATIVE_FIELD_LIST
    )
    # The load-bearing line: the runtime's own reader, over what we built.
    built = _create_creative(
        CreativeConf(name="c", destination="d", template=template),
        call_to_action=messenger_call_to_action(),
    )
    # And it kept the researcher's half, which is what a template is for.
    story = built["object_story_spec"]
    assert story["page_id"] == PAGE
    carrier = story.get("link_data") or story.get("video_data")
    assert carrier["message"] == "Tell us what you think."


# ---------------------------------------------------------------------------
# Applying
# ---------------------------------------------------------------------------


def test_apply_creates_everything_in_order_and_resolves_the_placeholders(api):
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="Apply Me", adsets=_adsets(), ads=[_ad()]
    )
    sent_creative = next(c for c in plan.creates if c.node == "creative").params

    patcher, g = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}, {"id": "A2"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [_as_meta_returns_it(sent_creative, "CR1")],
        }
    )
    with patcher:
        result = tp.apply(plan, api)

    assert result.campaign_id == "C1"
    assert result.adsets == [
        {"id": "A1", "name": "Kwara - Men"},
        {"id": "A2", "name": "Kwara - Women"},
    ]
    assert [
        c["params"]["campaign_id"]
        for c in g.calls
        if c["path"].endswith("adsets") and c["method"] == "POST"
    ] == ["C1", "C1"]
    ad = g.posted("ads")[0]
    assert ad["adset_id"] == "A1"
    assert ad["creative"] == {"creative_id": "CR1"}
    # The blob a `creatives` conf needs, read back rather than echoed.
    assert result.ads[0]["template"]["actor_id"] == PAGE
    assert result.warnings == list(plan.warnings)


def test_apply_refuses_when_the_campaign_name_is_taken(api):
    """Duplicate names break `FacebookState.campaign` (`StateNameError`), so a
    reuse would not merely confuse a human -- it would break the run path of
    any study naming that campaign.
    """
    plan = tp.plan_template_campaign(account_id=ACCOUNT, name="Taken", adsets=_adsets())
    patcher, g = _graph(
        **{"GET campaigns": [{"data": [{"id": "OLD", "name": "Templates - Taken"}]}]}
    )
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="already exists"):
            tp.apply(plan, api)

    assert [c for c in g.calls if c["method"] == "POST"] == []


def test_apply_uploads_an_image_and_substitutes_its_hash(api, tmp_path):
    png = tmp_path / "ad.png"
    png.write_bytes(b"not-really-a-png")

    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="With Image",
        adsets=_adsets(),
        ads=[_ad(image_hash=None, image=str(png))],
    )
    # The upload is planned first: an orphan image is free, an orphan campaign
    # is debris on someone's account.
    assert plan.creates[0].node == "image"

    patcher, g = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST adimages": [{"images": {"ad.png": {"hash": "HASH123"}}}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}, {"id": "A2"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [{"id": "CR1", "actor_id": PAGE, "object_story_spec": {}}],
        }
    )
    with patcher:
        tp.apply(plan, api)

    creative = g.posted("adcreatives")[0]
    assert creative["object_story_spec"]["link_data"]["image_hash"] == "HASH123"
    upload = next(c for c in g.calls if c["path"].endswith("adimages"))
    assert upload["files"] == ["ad.png"]


def test_a_missing_image_file_fails_at_plan_time_not_half_way_through_an_apply():
    with pytest.raises(tp.TemplatePlanError, match="no such image file"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Ghost",
            adsets=_adsets(),
            ads=[_ad(image_hash=None, image="/nope/missing.png")],
        )


def test_apply_warns_when_meta_returns_a_creative_without_actor_id(api):
    """The one Meta assumption in this module, made loud rather than assumed.

    `audiences.hydrate_audiences` reads `template["actor_id"]` with a bare
    KeyError, so a template lacking it is a study that dies at audience-build
    time with a one-word exception.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="No Actor", adsets=_adsets(), ads=[_ad()]
    )
    patcher, _ = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}, {"id": "A2"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [{"id": "CR1", "object_story_spec": {"page_id": PAGE}}],
        }
    )
    with patcher:
        result = tp.apply(plan, api)

    assert any("actor_id" in w for w in result.warnings)


def test_plan_template_ads_targets_an_existing_marked_campaign(api):
    plan = tp.plan_template_ads(
        account_id=ACCOUNT, campaign_id="C1", adset_id="A1", ads=[_ad()]
    )
    assert plan.campaign_name is None
    assert plan.campaign_id == "C1"
    ad = next(c for c in plan.creates if c.node == "ad")
    # The ad set is pre-existing, so its id rides in the plan's seed rather
    # than being substituted into the create -- the placeholder syntax stays
    # uniform and `apply`'s "references something nothing creates" guard keeps
    # its teeth for every other ref.
    assert ad.params["adset_id"] == "${vlab:adset}"
    assert plan.seed == {"adset": "A1"}

    patcher, g = _graph(
        **{
            "GET C1": [{"id": "C1", "name": "Templates - Existing"}],
            "POST adcreatives": [{"id": "CR9"}],
            "POST ads": [{"id": "AD9"}],
            "GET CR9": [{"id": "CR9", "actor_id": PAGE, "object_story_spec": {}}],
        }
    )
    with patcher:
        result = tp.apply(plan, api)
    assert result.ads[0]["id"] == "AD9"
    assert g.posted("campaigns") == []


def test_plan_template_ads_refuses_a_campaign_without_the_marker(api):
    """The only thing between `vlab template creative` and a paused ad landing
    inside a live study's campaign.
    """
    plan = tp.plan_template_ads(
        account_id=ACCOUNT, campaign_id="C1", adset_id="A1", ads=[_ad()]
    )
    patcher, g = _graph(**{"GET C1": [{"id": "C1", "name": "vlab-live-study"}]})
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="does not start with"):
            tp.apply(plan, api)
    assert [c for c in g.calls if c["method"] == "POST"] == []


def test_a_meta_rejection_names_the_object_that_was_refused(api):
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="Doomed", adsets=_adsets()
    )
    error = FacebookRequestError(
        message="Call was not successful",
        request_context={},
        http_status=400,
        http_headers={},
        body='{"error": {"message": "Invalid region key", "code": 100}}',
    )
    patcher, _ = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [error],
        }
    )
    with patcher:
        with pytest.raises(tp.TemplateApplyError) as e:
            tp.apply(plan, api)

    assert "adset:Kwara - Men" in str(e.value)
    assert "vlab template delete C1" in str(e.value)


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------


def test_delete_refuses_a_campaign_without_the_marker(api):
    patcher, g = _graph(**{"GET C9": [{"id": "C9", "name": "vlab-hpv-nigeria"}]})
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="does not start with"):
            tp.delete_template_campaign(api, "C9")
    assert [c for c in g.calls if c["method"] == "DELETE"] == []


def test_delete_refuses_a_marked_campaign_that_is_delivering(api):
    patcher, g = _graph(
        **{
            "GET C9": [
                {"id": "C9", "name": "Templates - X", "effective_status": "ACTIVE"}
            ]
        }
    )
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="delivering"):
            tp.delete_template_campaign(api, "C9")
    assert [c for c in g.calls if c["method"] == "DELETE"] == []


def test_delete_removes_a_paused_marked_campaign(api):
    patcher, g = _graph(
        **{
            "GET C9": [
                {"id": "C9", "name": "Templates - X", "effective_status": "PAUSED"}
            ]
        }
    )
    with patcher:
        out = tp.delete_template_campaign(api, "C9")
    assert out == {"deleted": "C9", "name": "Templates - X"}
    assert [c["path"] for c in g.calls if c["method"] == "DELETE"] == ["C9"]


# ---------------------------------------------------------------------------
# Targeting validation
# ---------------------------------------------------------------------------


def test_validate_targeting_reads_and_creates_nothing(api):
    patcher, g = _graph(
        **{
            "GET reachestimate": [
                {"data": {"users_lower_bound": 900000, "estimate_ready": True}}
            ]
        }
    )
    with patcher:
        out = tp.validate_targeting(api, "1342820622846299", _targeting([1]))

    assert out["data"]["users_lower_bound"] == 900000
    assert [c["method"] for c in g.calls] == ["GET"]
    call = g.calls[0]
    assert call["path"] == "act_1342820622846299/reachestimate"
    assert json.loads(call["params"]["targeting_spec"]) == _targeting([1])


def test_delivery_estimate_needs_an_optimization_goal(api):
    with pytest.raises(tp.TemplatePlanError, match="optimization_goal"):
        tp.validate_targeting(api, ACCOUNT, _targeting([1]), edge=tp.DELIVERY_ESTIMATE)


def test_an_unknown_edge_is_refused(api):
    with pytest.raises(tp.TemplatePlanError, match="Unknown edge"):
        tp.validate_targeting(api, ACCOUNT, _targeting([1]), edge="whatever")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_a_session_with_an_app_secret_sends_appsecret_proof():
    from ..facebook.state import api_for_token

    api = api_for_token("TOK", "app-id", "app-secret")
    assert api._session.requests.params["access_token"] == "TOK"
    assert "appsecret_proof" in api._session.requests.params


def test_a_token_only_session_sends_no_proof():
    """A pipx user may hold nothing but a token. Meta requires the proof only
    for apps with "Require app secret" turned on, which is off by default; the
    vlab app's setting is not readable from this repository, so this is offered
    and documented rather than blessed.
    """
    from ..facebook.state import api_for_token

    api = api_for_token("TOK")
    assert api._session.requests.params["access_token"] == "TOK"
    assert "appsecret_proof" not in api._session.requests.params


def test_get_api_still_reads_both_keys_off_the_env():
    """The service's entry point is unchanged by the extraction."""
    from ..facebook.state import get_api

    env = {"FACEBOOK_APP_ID": "a", "FACEBOOK_APP_SECRET": "b"}.__getitem__
    api = get_api(env, "TOK")
    assert "appsecret_proof" in api._session.requests.params


def test_a_web_adset_on_the_messaging_defaults_is_warned_about():
    """Warned, not refused: Meta's own docs contradict each other about which
    objective/optimization_goal/destination_type triples are legal
    (`planning/click-to-whatsapp-ads.md` §1.1), and a hardcoded matrix in the
    planner would go silently wrong and start refusing plans Meta accepts.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Webby",
        adsets=[tp.AdsetSpec(name="a", targeting=_targeting([1]), kind=tp.WEB)],
        ads=[_ad(tp.WEB, adset="a")],
    )
    assert any("OUTCOME_TRAFFIC" in w for w in plan.warnings)


def test_an_app_adset_without_a_promoted_object_is_warned_about():
    """Unlike WhatsApp's Page, there is nothing on the creative to take the
    application id from -- it lives on the study's `destinations` conf.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Appy",
        adsets=[tp.AdsetSpec(name="a", targeting=_targeting([1]), kind=tp.APP)],
        ads=[_ad(tp.APP, adset="a")],
    )
    assert any("application_id" in w for w in plan.warnings)


def test_a_multi_adset_off_conversations_is_warned_about():
    """Meta's click-to-multidestination guide: CONVERSATIONS is the only
    optimization_goal it accepts, strictly narrower than single-destination
    click-to-WhatsApp.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Multi",
        adsets=[
            tp.AdsetSpec(
                name="a",
                targeting=_targeting([1]),
                kind=tp.MULTI,
                optimization_goal="LINK_CLICKS",
                promoted_object={"page_id": PAGE},
            )
        ],
        ads=[_ad(tp.MULTI, adset="a")],
    )
    assert any("CONVERSATIONS is the only one accepted" in w for w in plan.warnings)


def test_ad_copy_that_looks_like_a_placeholder_is_left_alone(api):
    """`_substitute` walks the researcher's own copy, so it must not eat it.

    A bare `${...}` syntax would either substitute this message or -- because
    an unknown ref is treated as a planner bug -- fail the apply outright on an
    ad that is perfectly fine. Namespacing the placeholder is what makes the
    unknown-ref guard safe to keep as a hard error.

    `${vlab:...}` itself IS reserved and still errors on an unknown ref; that
    is the point, and the next test covers it. Nothing else is.
    """
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT,
        name="Dollars",
        adsets=_adsets(),
        ads=[_ad(message="${campaign}", headline="$5 or ${creative:x}")],
    )
    patcher, g = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}, {"id": "A2"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [{"id": "CR1", "actor_id": PAGE, "object_story_spec": {}}],
        }
    )
    with patcher:
        tp.apply(plan, api)

    link_data = g.posted("adcreatives")[0]["object_story_spec"]["link_data"]
    assert link_data["message"] == "${campaign}"
    assert link_data["name"] == "$5 or ${creative:x}"


def test_a_placeholder_for_something_nothing_creates_is_a_planner_bug(api):
    """The guard the namespace exists to protect: it stays a hard error."""
    plan = tp.plan_template_campaign(
        account_id=ACCOUNT, name="Broken", adsets=_adsets()
    )
    broken = tp.TemplatePlan(
        account_id=plan.account_id,
        creates=plan.creates[:1]
        + (
            tp.Create(
                ref="adset:x",
                node="adset",
                edge="adsets",
                params={"name": "x", "campaign_id": tp.ref_placeholder("nowhere")},
            ),
        ),
        campaign_name=plan.campaign_name,
    )
    patcher, _ = _graph(
        **{"GET campaigns": [{"data": []}], "POST campaigns": [{"id": "C1"}]}
    )
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="nothing in it creates"):
            tp.apply(broken, api)


def test_a_web_video_creative_with_no_link_is_refused():
    """Review caught this: the "web needs a link" guard lived in
    `_structural_link`, which the video branch never calls -- so a web video
    creative planned cleanly and shipped `call_to_action.value.link = null`,
    for Meta to reject at `POST /adcreatives` with the campaign and its ad sets
    already created. Exactly the failure plan-time checks exist to prevent.
    """
    with pytest.raises(tp.TemplatePlanError, match="needs a link"):
        tp.build_creative(tp.WEB, name="w", page_id=PAGE, message="m", video_id="99")


def test_an_app_video_creative_with_no_link_is_refused():
    with pytest.raises(tp.TemplatePlanError, match="needs a link"):
        tp.build_creative(
            tp.APP,
            name="a",
            page_id=PAGE,
            message="m",
            video_id="99",
            deeplink="myapp://x",
        )


def test_an_adset_takes_a_page_only_from_ads_that_actually_hang_on_it():
    """An ad with no `adset` hangs on the FIRST ad set, and only that one.

    Review caught the old filter (`a.adset in (None, spec.name)`), which made
    such an ad a candidate Page for EVERY ad set -- so an ad set with no ads of
    its own silently inherited a Page from an ad hanging somewhere else, and
    the "no ad in this plan hangs on it" message became unreachable in the case
    it describes.
    """
    with pytest.raises(tp.TemplatePlanError, match="No ad in this plan hangs on it"):
        tp.plan_template_campaign(
            account_id=ACCOUNT,
            name="Orphan",
            adsets=[
                tp.AdsetSpec(name="first", targeting=_targeting([1])),
                tp.AdsetSpec(
                    name="second", targeting=_targeting([2]), kind=tp.WHATSAPP
                ),
            ],
            # No `adset`, so it hangs on "first" -- and must not lend its Page
            # to "second".
            ads=[_ad(tp.MESSENGER)],
        )


def test_a_plan_that_names_no_campaign_at_all_creates_nothing(api):
    """The `if/elif` in `apply` is where BOTH refusals live, so a plan matching
    neither arm would create objects with nothing checked. Not reachable from
    either constructor today; a future third one should have to notice.
    """
    plan = tp.TemplatePlan(account_id=ACCOUNT, creates=())
    patcher, g = _graph()
    with patcher:
        with pytest.raises(tp.TemplateApplyError, match="neither a campaign"):
            tp.apply(plan, api)
    assert g.calls == []


def test_a_meta_rejection_is_reported_without_the_whole_request_context():
    """`str(FacebookRequestError)` interpolates every parameter of the failed
    call, which buries the one sentence Meta actually said. `server/meta.py`
    forbids echoing it; this does the same thing for the same reason.
    """
    error = FacebookRequestError(
        message="Call was not successful",
        request_context={"params": {"targeting": {"secret": "sauce"}}},
        http_status=400,
        http_headers={},
        body=(
            '{"error": {"message": "Invalid region key", "code": 100,'
            ' "error_subcode": 4834011}}'
        ),
    )
    message = tp.meta_message(error)
    assert message == "Invalid region key (code 100, subcode 4834011)"
    assert "sauce" not in message
    # Anything that is not a Meta error keeps its own message.
    assert tp.meta_message(ValueError("connection reset")) == "connection reset"
