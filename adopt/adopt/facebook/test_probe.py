from typing import Dict

from . import field_contract
from .probe import (
    DIFFERS,
    DROPPED,
    OK,
    classify,
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
