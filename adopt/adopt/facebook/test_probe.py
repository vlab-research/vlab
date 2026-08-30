import json
from datetime import datetime
from typing import Dict

from ..malaria import hydrate_strata
from ..study_conf import (
    CreativeConf,
    FlyMessengerDestination,
    FlyMultiDestination,
    GeneralConf,
    SimpleRecruitment,
    Stratum,
    StratumConf,
    StudyConf,
    UserInfo,
)
from . import field_contract
from .probe import (
    DIFFERS,
    DROPPED,
    OK,
    classify,
    constructed_creatives,
    render_dropped_block,
    summarise,
    update_contract,
)

FIELDS = ["object_story_spec", "url_tags", "degrees_of_freedom_spec"]


def test_classify_reports_matching_leaves_as_ok():
    desired = {"url_tags": "ref=foo", "object_story_spec": {"page_id": "111"}}
    source = {"url_tags": "ref=foo", "object_story_spec": {"page_id": "111"}}

    verdicts = {p: v for p, v, _, _ in classify(desired, source, FIELDS)}

    assert verdicts == {".url_tags": OK, ".object_story_spec.page_id": OK}


def test_classify_reports_a_key_facebook_did_not_return_as_dropped():
    desired = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {"image_text_translation": {"enroll_status": "OPT_IN"}}
        }
    }
    source = {
        "degrees_of_freedom_spec": {
            "creative_features_spec": {"standard_enhancements": {"enroll_status": "OPT_OUT"}}
        }
    }

    findings = classify(desired, source, FIELDS)
    path = ".degrees_of_freedom_spec.creative_features_spec.image_text_translation"

    assert (path, DROPPED) in [(p, v) for p, v, _, _ in findings]


def test_classify_reports_changed_values_as_differs():
    findings = classify({"url_tags": "ref=new"}, {"url_tags": "ref=old"}, FIELDS)

    assert findings == [(".url_tags", DIFFERS, "ref=new", "ref=old")]


def test_classify_ignores_extra_keys_from_facebook():
    # Facebook returns far more than we set; only what we send is our business.
    desired = {"object_story_spec": {"page_id": "111"}}
    source = {"object_story_spec": {"page_id": "111", "server_thing": "x"}}

    assert [v for _, v, _, _ in classify(desired, source, FIELDS)] == [OK]


def test_classify_treats_reordered_lists_as_equal():
    # Facebook reorders list values; _eq sorts before comparing, so must we.
    desired = {"object_story_spec": {"tags": [{"id": "2"}, {"id": "1"}]}}
    source = {"object_story_spec": {"tags": [{"id": "1"}, {"id": "2"}]}}

    assert [v for _, v, _, _ in classify(desired, source, FIELDS)] == [OK]


def test_summarise_separates_declared_from_undeclared_drops():
    declared = ".degrees_of_freedom_spec.creative_features_spec.image_text_translation"
    findings = [
        (declared, DROPPED, {"enroll_status": "OPT_IN"}, None),
        (".url_tags", DROPPED, "ref=foo", None),
    ]

    rows = summarise(findings)

    assert rows[declared]["declared_dropped"] is True
    assert rows[".url_tags"]["declared_dropped"] is False


def test_summarise_flags_a_declaration_facebook_now_honours_as_stale():
    declared = ".degrees_of_freedom_spec.creative_features_spec.image_text_translation"

    rows = summarise([(declared, OK, {"enroll_status": "OPT_IN"}, {"enroll_status": "OPT_IN"})])

    assert rows[declared]["verdict"] == "stale"


def test_summarise_reports_a_path_dropped_on_any_ad():
    # One clean ad does not make the field safe to compare.
    rows = summarise([(".url_tags", OK, "a", "a"), (".url_tags", DROPPED, "a", None)])

    assert rows[".url_tags"]["verdict"] == DROPPED


def test_rendered_block_is_valid_python_and_round_trips():
    paths = {
        "a.b.c": "short reason",
        "d.e": "a much longer reason " * 8,
    }

    ns: Dict = {"Dict": Dict}
    exec(render_dropped_block(paths), ns)

    assert set(ns["DROPPED"]) == set(paths)
    # Reasons survive wrapping intact apart from whitespace normalisation.
    assert " ".join(ns["DROPPED"]["d.e"].split()) == " ".join(paths["d.e"].split())


def test_update_contract_adds_undeclared_drops():
    rows = {
        ".url_tags": {"verdict": DROPPED, "declared_dropped": False, "ads": 3, "hits": 3},
    }

    new = update_contract(rows, "2026-07-31")

    assert new is not None
    assert '"url_tags"' in new
    assert "2026-07-31" in new
    # The existing declaration is preserved.
    assert "image_text_translation" in new


def test_update_contract_removes_stale_declarations():
    declared = next(iter(field_contract.DROPPED))
    rows = {f".{declared}": {"verdict": "stale", "declared_dropped": True, "ads": 1, "hits": 1}}

    new = update_contract(rows, "2026-07-31")

    assert new is not None
    assert declared not in new


def test_update_contract_is_a_noop_when_nothing_changed():
    rows = {
        f".{p}": {"verdict": DROPPED, "declared_dropped": True, "ads": 1, "hits": 1}
        for p in field_contract.DROPPED
    }

    assert update_contract(rows, "2026-07-31") is None


# ---------------------------------------------------------------------------
# constructed_creatives -- `adopt-probe --print-creative`.
#
# The point of these is that the creative adopt would send is inspectable
# without a deploy and without Meta. See
# planning/creative-construction-contract.md; on 2026-08-30 three destination
# bugs on one study were learned one release at a time for want of exactly
# this.
# ---------------------------------------------------------------------------


# A minimal Ads Manager template: page and image, no destination of its own.
# Construction reads object_story_spec.page_id, so {} is not a usable stand-in.
def _template(**extra):
    return {
        "object_story_spec": {"page_id": "page-123", "link_data": {"image_hash": "h"}},
        **extra,
    }


def _multi_dest(name="multi", shortcode="vlpulseng"):
    return FlyMultiDestination(
        type="multi",
        name=name,
        initial_shortcode=shortcode,
        welcome_message="Welcome!",
        button_text="Start",
        whatsapp_phone_number="+1-541-920-2635",
    )


def _messenger_dest(name="messenger", shortcode="vlpulseng"):
    return FlyMessengerDestination(
        type="messenger",
        name=name,
        initial_shortcode=shortcode,
        welcome_message="Welcome!",
        button_text="Start",
    )


def _study(destinations, creatives, strata=()):
    return StudyConf(
        id="study-1",
        user=UserInfo(survey_user="user", token="token"),
        general=GeneralConf(
            name="test-study",
            credentials_key="page-1",
            credentials_entity="facebook_page",
            ad_account="act_1",
            opt_window=48,
        ),
        destinations=destinations,
        audiences=[],
        creatives=creatives,
        strata=list(strata),
        recruitment=SimpleRecruitment(
            ad_campaign_name="test-campaign",
            objective="OUTCOME_ENGAGEMENT",
            optimization_goal="CONVERSATIONS",
            min_budget=1,
            budget=100,
            max_sample=100,
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 9, 1),
        ),
    )


def _stratum(creatives, id="stratum-1"):
    return Stratum(
        id=id,
        quota=1.0,
        creatives=creatives,
        facebook_targeting={},
        metadata={"gender": "men"},
    )


def _app_destinations(spec):
    return {
        cta["value"]["app_destination"]
        for cta in spec["asset_feed_spec"]["call_to_actions"]
    }


def test_print_creative_shows_all_three_places_a_destination_is_stated():
    """The invariant the whole contract exists to protect.

    Meta requires the ad set's destination_type, the creative's single-valued
    call_to_action and asset_feed_spec's call_to_actions to agree, and rejects
    the ad with subcode 2490279 when they do not, naming none of them. All
    three have to be visible in one output or the check cannot be made by
    reading it.
    """
    creative = CreativeConf(destination="multi", name="Smiling", template=_template())
    study = _study([_multi_dest()], [creative])

    entries = constructed_creatives(study, [_stratum([creative])])

    assert len(entries) == 1
    assert entries[0]["campaign"] == "test-campaign"
    assert entries[0]["stratum"] == "stratum-1"
    assert entries[0]["adset_destination_type"] == "MESSAGING_MESSENGER_WHATSAPP"

    spec = entries[0]["creatives"][0]["spec"]
    assert _app_destinations(spec) == {"MESSENGER", "WHATSAPP"}
    assert (
        spec["object_story_spec"]["link_data"]["call_to_action"]["type"]
        == "MESSAGE_PAGE"
    )


def test_print_creative_carries_the_ref_into_the_welcome_message():
    creative = CreativeConf(destination="multi", name="Smiling", template=_template())
    study = _study([_multi_dest()], [creative])

    entries = constructed_creatives(study, [_stratum([creative])])
    spec = entries[0]["creatives"][0]["spec"]

    welcome = spec["asset_feed_spec"]["additional_data"]["page_welcome_message"]
    assert "Smiling" in welcome


def test_print_creative_output_is_json_serialisable():
    # It is printed as JSON; a Facebook SDK object anywhere in the tree would
    # make the whole mode useless at exactly the moment it is needed.
    creative = CreativeConf(destination="multi", name="Smiling", template=_template())
    study = _study([_multi_dest()], [creative])

    entries = constructed_creatives(study, [_stratum([creative])])

    json.dumps(entries, sort_keys=True)


def test_print_creative_filters_without_misreporting_the_adset():
    """--creative narrows what is printed, not what the ad set would be.

    destination_type is an ad-set field agreed across all of a stratum's
    creatives, so deriving it from the filtered subset would print a value
    production never sends -- the exact failure mode the probe exists to
    catch, reintroduced by the tool doing the catching.
    """
    a = CreativeConf(destination="multi", name="A", template=_template())
    b = CreativeConf(destination="multi", name="B", template=_template())
    study = _study([_multi_dest()], [a, b])

    entries = constructed_creatives(
        study, [_stratum([a, b])], creative_name="A"
    )

    assert [c["creative"] for c in entries[0]["creatives"]] == ["A"]
    assert entries[0]["adset_destination_type"] == "MESSAGING_MESSENGER_WHATSAPP"


def test_print_creative_filters_by_stratum():
    creative = CreativeConf(destination="multi", name="Smiling", template=_template())
    study = _study([_multi_dest()], [creative])
    strata = [_stratum([creative], id="a"), _stratum([creative], id="b")]

    entries = constructed_creatives(study, strata, stratum_id="b")

    assert [e["stratum"] for e in entries] == ["b"]


def test_print_creative_reports_a_refused_creative_without_hiding_its_siblings():
    """One refusal must not stop the run.

    Three bugs cost three releases because each hypothesis could only be tested
    by deploying and each rejection surfaced one problem. A mode that raises on
    the first refusal has the same shape.
    """
    good = CreativeConf(destination="multi", name="Good", template=_template())
    # An Advantage+ template: one asset_feed_spec holds one optimization_type,
    # so its variants and a constructed destination array cannot both apply.
    bad = CreativeConf(
        destination="multi",
        name="Bad",
        template=_template(
            asset_feed_spec={
                "optimization_type": "DEGREES_OF_FREEDOM",
                "bodies": [{"text": "hello"}],
            }
        ),
    )
    study = _study([_multi_dest()], [good, bad])

    entries = constructed_creatives(study, [_stratum([good, bad])])
    rows = {c["creative"]: c for c in entries[0]["creatives"]}

    assert "spec" in rows["Good"]
    assert "error" in rows["Bad"]
    assert "Bad" in rows["Bad"]["error"]


def test_print_creative_reports_a_stratum_that_cannot_be_paired():
    creative = CreativeConf(destination="nowhere", name="Smiling", template=_template())
    study = _study([_messenger_dest()], [creative])

    entries = constructed_creatives(study, [_stratum([creative])])

    assert "error" in entries[0]
    assert "nowhere" in entries[0]["error"]


def test_hydration_for_print_creative_needs_no_facebook_state():
    """The production shape: real strata name vlab-managed audiences.

    vl-pulse-nigeria-smoke's strata each exclude a respondents audience, and
    resolving one is a Graph API call -- so hydrating them the normal way needs
    Facebook credentials that --print-creative otherwise has no use for. A
    creative never reads targeting, so the mode skips that step entirely; this
    is the assertion that it can.
    """
    creative = CreativeConf(destination="multi", name="Smiling", template=_template())
    conf = StratumConf(
        id="stratum-1",
        quota=1.0,
        creatives=["Smiling"],
        audiences=[],
        excluded_audiences=["VL Pulse Nigeria - Smoke respondents"],
        facebook_targeting={"genders": [1]},
        metadata={"gender": "men"},
    )

    strata = hydrate_strata(None, [conf], [creative], resolve_audiences=False)

    assert strata[0].facebook_targeting == {"genders": [1]}
    assert [c.name for c in strata[0].creatives] == ["Smiling"]
