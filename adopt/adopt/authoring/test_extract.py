"""Test-for-test translation of
`dashboard/src/pages/StudyConfPage/forms/variables/extract.test.ts`.

Every `it(...)` in that file has a function below with the corresponding name,
in the same order, with the same literals. Where the TS asserts `err.name`, the
Python asserts `type(err).__name__` — the closest thing Python has to JS's
per-instance error name.

The section at the bottom, below the divider, is NOT in the TS: it pins down
behaviour the TypeScript leaves implicit (JS truthiness, missing `targeting`,
`undefined` vs. an absent key) and that the port therefore had to decide.
"""

import json

import pytest

from adopt.authoring.extract import (
    AdsetNotFoundError,
    ExtractError,
    PropertyMissingError,
    diff_property_keys,
    extract_from_adset,
    is_level_in_sync,
    properties_on_some_level,
)

MOCK_ADSET = {
    "id": "adset-123",
    "name": "Test Adset",
    "targeting": {
        "geo_locations": {"cities": [{"key": "NG-BA", "name": "Bauchi"}]},
        "age_min": 18,
        "age_max": 65,
        "genders": [1],
        "targeting_automation": {
            "advantage_audience": 1,
            "individual_setting": {"age": 1, "gender": 0, "geo": 0},
        },
    },
}


# --- extractFromAdset ------------------------------------------------------


def test_should_extract_requested_properties_from_an_adset():
    result = extract_from_adset(MOCK_ADSET, ["geo_locations", "age_min", "age_max"])

    assert result == {
        "geo_locations": {"cities": [{"key": "NG-BA", "name": "Bauchi"}]},
        "age_min": 18,
        "age_max": 65,
        "targeting_automation": {"advantage_audience": 0},
    }


def test_should_always_force_targeting_automation_stripping_individual_setting():
    result = extract_from_adset(MOCK_ADSET, ["geo_locations"])

    assert result["targeting_automation"] == {"advantage_audience": 0}
    assert "individual_setting" not in result["targeting_automation"]


def test_should_always_include_targeting_automation_even_if_not_on_source_adset():
    # The TS sets `targeting_automation: undefined`, which on the JSON wire is
    # simply an absent key — there is no `undefined` to serialise.
    targeting = {
        k: v for k, v in MOCK_ADSET["targeting"].items() if k != "targeting_automation"
    }
    adset_without_ta = {**MOCK_ADSET, "targeting": targeting}

    result = extract_from_adset(adset_without_ta, ["geo_locations"])

    assert result["targeting_automation"] == {"advantage_audience": 0}


def test_should_handle_source_adset_with_advantage_audience_already_0():
    adset_already_disabled = {
        **MOCK_ADSET,
        "targeting": {
            **MOCK_ADSET["targeting"],
            "targeting_automation": {"advantage_audience": 0},
        },
    }

    result = extract_from_adset(adset_already_disabled, ["geo_locations"])

    assert result["targeting_automation"] == {"advantage_audience": 0}


def test_should_throw_adset_not_found_error_if_adset_is_null():
    with pytest.raises(AdsetNotFoundError) as excinfo:
        extract_from_adset(None, ["geo_locations"])

    assert excinfo.value.adset_name == "(unknown)"


def test_should_throw_adset_not_found_error_if_adset_is_undefined():
    # JS distinguishes null from undefined; JSON and Python have only None, so
    # this is the same call as the test above. Kept for test-for-test parity.
    with pytest.raises(AdsetNotFoundError):
        extract_from_adset(None, ["geo_locations"])


def test_should_throw_property_missing_error_if_a_requested_property_is_missing():
    with pytest.raises(PropertyMissingError):
        extract_from_adset(MOCK_ADSET, ["geo_locations", "custom_audiences"])

    with pytest.raises(PropertyMissingError) as excinfo:
        extract_from_adset(MOCK_ADSET, ["custom_audiences"])

    assert excinfo.value.property_key == "custom_audiences"
    assert excinfo.value.adset_name == "Test Adset"


def test_should_return_only_targeting_automation_for_adset_with_no_requested_properties():
    minimal_adset = {
        "id": "adset-456",
        "name": "Minimal Adset",
        "targeting": {
            "targeting_automation": {
                "advantage_audience": 1,
                "individual_setting": {"age": 1},
            },
        },
    }

    result = extract_from_adset(minimal_adset, [])
    assert result == {"targeting_automation": {"advantage_audience": 0}}


def test_should_omit_a_missing_property_that_is_optional_rather_than_throw():
    result = extract_from_adset(
        MOCK_ADSET, ["geo_locations", "custom_audiences"], ["custom_audiences"]
    )

    assert result == {
        "geo_locations": {"cities": [{"key": "NG-BA", "name": "Bauchi"}]},
        "targeting_automation": {"advantage_audience": 0},
    }
    assert "custom_audiences" not in result


def test_should_copy_an_optional_property_when_the_adset_has_it():
    result = extract_from_adset(MOCK_ADSET, ["geo_locations", "age_min"], ["age_min"])

    assert result["age_min"] == 18


def test_should_still_throw_for_a_missing_property_that_is_not_optional():
    with pytest.raises(PropertyMissingError) as excinfo:
        extract_from_adset(
            MOCK_ADSET,
            ["custom_audiences", "excluded_geo_locations"],
            ["custom_audiences"],
        )

    assert excinfo.value.property_key == "excluded_geo_locations"


# --- propertiesOnSomeLevel -------------------------------------------------
#
# The rule behind `optional`: a property is required of every level only when
# no level has it. One level with it makes it optional for the rest.

URBAN = {
    "id": "adset-urban",
    "name": "Argentina - Urban",
    "targeting": {
        "geo_locations": {"regions": [{"key": "1", "name": "Buenos Aires"}]},
        "excluded_geo_locations": {"regions": [{"key": "2", "name": "Pampa"}]},
    },
}
RURAL = {
    "id": "adset-rural",
    "name": "Argentina - Rural",
    "targeting": {"geo_locations": {"regions": [{"key": "2", "name": "Pampa"}]}},
}
LEVELS = [{"template_adset": "adset-urban"}, {"template_adset": "adset-rural"}]


def test_returns_the_properties_at_least_one_level_carries():
    result = properties_on_some_level(
        LEVELS,
        [URBAN, RURAL],
        ["geo_locations", "excluded_geo_locations", "custom_audiences"],
    )

    assert result == ["geo_locations", "excluded_geo_locations"]


def test_leaves_out_a_property_no_level_carries_so_it_stays_required():
    assert properties_on_some_level(LEVELS, [URBAN, RURAL], ["custom_audiences"]) == []


def test_lets_a_level_lacking_the_property_extract_once_another_level_has_it():
    optional = properties_on_some_level(
        LEVELS, [URBAN, RURAL], ["geo_locations", "excluded_geo_locations"]
    )
    result = extract_from_adset(
        RURAL, ["geo_locations", "excluded_geo_locations"], optional
    )

    assert result == {
        "geo_locations": {"regions": [{"key": "2", "name": "Pampa"}]},
        "targeting_automation": {"advantage_audience": 0},
    }


def test_ignores_a_level_whose_adset_is_not_found():
    result = properties_on_some_level(
        [{"template_adset": "adset-rural"}, {"template_adset": "adset-gone"}],
        [URBAN, RURAL],
        ["geo_locations", "excluded_geo_locations"],
    )

    assert result == ["geo_locations"]


def test_ignores_an_adset_with_no_targeting_object():
    bare = {"id": "adset-bare", "name": "Bare"}

    assert (
        properties_on_some_level([{"template_adset": "adset-bare"}], [bare], ["geo_locations"])
        == []
    )


def test_keeps_the_order_of_properties_not_of_levels():
    result = properties_on_some_level(
        LEVELS, [URBAN, RURAL], ["excluded_geo_locations", "geo_locations"]
    )

    assert result == ["excluded_geo_locations", "geo_locations"]


# --- error types -----------------------------------------------------------


def test_adset_not_found_error_should_have_correct_name_and_adset_name_field():
    error = AdsetNotFoundError("my-adset")
    assert type(error).__name__ == "AdsetNotFoundError"
    assert error.adset_name == "my-adset"
    assert "my-adset" in str(error)


def test_property_missing_error_should_have_correct_name_and_fields():
    error = PropertyMissingError("my-adset", "geo_locations")
    assert type(error).__name__ == "PropertyMissingError"
    assert error.adset_name == "my-adset"
    assert error.property_key == "geo_locations"
    assert "geo_locations" in str(error)


# --- isLevelInSync ---------------------------------------------------------


def test_returns_true_when_stored_and_would_apply_are_equal():
    obj = {"age_min": 18, "geo_locations": {"countries": ["US"]}}
    assert is_level_in_sync(obj, obj) is True


def test_returns_true_when_top_level_keys_are_in_different_orders():
    stored = {"age_max": 45, "age_min": 18, "geo_locations": {"countries": ["NG"]}}
    would_apply = {"age_min": 18, "age_max": 45, "geo_locations": {"countries": ["NG"]}}
    assert is_level_in_sync(stored, would_apply) is True


def test_returns_true_when_nested_keys_are_in_different_orders():
    stored = {"geo_locations": {"countries": ["NG"], "location_types": ["home"]}}
    would_apply = {"geo_locations": {"location_types": ["home"], "countries": ["NG"]}}
    assert is_level_in_sync(stored, would_apply) is True


def test_ignores_targeting_automation_when_comparing():
    stored = {"age_min": 18}
    would_apply = {"age_min": 18, "targeting_automation": {"advantage_audience": 0}}
    assert is_level_in_sync(stored, would_apply) is True


def test_returns_false_when_values_differ_for_the_same_key():
    stored = {"age_min": 18}
    would_apply = {"age_min": 25}
    assert is_level_in_sync(stored, would_apply) is False


def test_returns_false_when_stored_is_empty_and_would_apply_has_values():
    assert is_level_in_sync({}, {"age_min": 18}) is False


def test_returns_true_when_both_stored_and_would_apply_are_empty():
    assert is_level_in_sync({}, {}) is True


def test_is_level_in_sync_handles_null_or_non_object_inputs_without_throwing():
    assert is_level_in_sync(None, None) is True
    # The TS also asserts the undefined/undefined pair; both are None here.
    assert is_level_in_sync(None, None) is True
    assert is_level_in_sync(None, {"age_min": 18}) is False


# --- diffPropertyKeys ------------------------------------------------------


def test_returns_no_diff_when_stored_keys_match_current_properties():
    stored = {
        "age_min": 18,
        "genders": [1],
        "targeting_automation": {"advantage_audience": 0},
    }
    assert diff_property_keys(stored, ["age_min", "genders"]) == {
        "added": [],
        "removed": [],
        "keys_differ": False,
    }


def test_detects_added_properties():
    stored = {"age_min": 18}
    assert diff_property_keys(stored, ["age_min", "genders"]) == {
        "added": ["genders"],
        "removed": [],
        "keys_differ": True,
    }


def test_detects_removed_properties():
    stored = {"age_min": 18, "genders": [1]}
    assert diff_property_keys(stored, ["age_min"]) == {
        "added": [],
        "removed": ["genders"],
        "keys_differ": True,
    }


def test_treats_empty_current_as_removing_all_stored_keys():
    stored = {"age_min": 18, "genders": [1]}
    assert diff_property_keys(stored, []) == {
        "added": [],
        "removed": ["age_min", "genders"],
        "keys_differ": True,
    }


def test_ignores_targeting_automation_when_computing_stored_keys():
    stored = {"age_min": 18, "targeting_automation": {"advantage_audience": 0}}
    assert diff_property_keys(stored, ["age_min"]) == {
        "added": [],
        "removed": [],
        "keys_differ": False,
    }


def test_does_not_mutate_the_input_stored_object():
    stored = {"age_min": 18, "targeting_automation": {"advantage_audience": 0}}
    snapshot = json.dumps(stored)
    diff_property_keys(stored, ["age_min"])
    assert json.dumps(stored) == snapshot


def test_diff_property_keys_handles_null_or_non_object_inputs_without_throwing():
    assert diff_property_keys(None, ["age_min"]) == {
        "added": ["age_min"],
        "removed": [],
        "keys_differ": True,
    }
    assert diff_property_keys(None, []) == {
        "added": [],
        "removed": [],
        "keys_differ": False,
    }


# ===========================================================================
# Beyond the TypeScript: behaviour the port had to decide.
#
# None of these have a counterpart in extract.test.ts. They pin the answers
# given in extract.py's comments so a later edit cannot quietly change them.
# ===========================================================================


def test_errors_share_a_catchable_base_that_is_not_base_exception():
    # The whole point of ExtractError: `except Exception` catches these, unlike
    # study_conf.InvalidConfigError.
    for err in (AdsetNotFoundError("a"), PropertyMissingError("a", "b")):
        assert isinstance(err, ExtractError)
        assert isinstance(err, Exception)


def test_error_messages_match_the_typescript_text_exactly():
    assert (
        str(AdsetNotFoundError("my-adset"))
        == "Template adset my-adset not found on Meta"
    )
    assert (
        str(PropertyMissingError("my-adset", "age_min"))
        == "Adset my-adset has no age_min property"
    )


def test_falls_back_to_id_when_name_is_falsy():
    # JS `adset.name || adset.id`: an empty-string name is falsy and falls
    # through to the id. `or` reproduces that.
    for name in ("", None):
        adset = {"id": "adset-123", "name": name, "targeting": {}}
        with pytest.raises(PropertyMissingError) as excinfo:
            extract_from_adset(adset, ["age_min"])
        assert excinfo.value.adset_name == "adset-123"


def test_falls_back_to_id_when_name_key_is_absent():
    adset = {"id": "adset-123", "targeting": {}}
    with pytest.raises(PropertyMissingError) as excinfo:
        extract_from_adset(adset, ["age_min"])
    assert excinfo.value.adset_name == "adset-123"


def test_a_property_present_with_a_null_value_is_present():
    # `in` is a key-presence test in both languages: JSON null is a value, and
    # a key holding it is extracted, not reported missing. (This is the JSON
    # analogue of the JS `undefined`-valued key the TS `in` also accepts.)
    adset = {"id": "a", "targeting": {"age_min": None}}
    assert extract_from_adset(adset, ["age_min"]) == {
        "age_min": None,
        "targeting_automation": {"advantage_audience": 0},
    }


def test_missing_targeting_raises_type_error_when_properties_are_requested():
    # The TS throws a raw TypeError from `'age_min' in undefined`; we raise a
    # TypeError that says what happened.
    with pytest.raises(TypeError):
        extract_from_adset({"id": "adset-123"}, ["age_min"])
    with pytest.raises(TypeError):
        extract_from_adset({"id": "adset-123", "targeting": None}, ["age_min"])


def test_missing_targeting_is_fine_when_no_properties_are_requested():
    # The TS reads `adset.targeting` inside the loop, so an empty property list
    # never touches it. Same here.
    assert extract_from_adset({"id": "adset-123"}, []) == {
        "targeting_automation": {"advantage_audience": 0}
    }


def test_empty_dict_adset_is_not_an_adset_not_found_error():
    # `{}` is truthy in JS, so the TS falls past the `!adset` guard and dies on
    # the targeting read. An empty dict is falsy in Python, which is why the
    # guard tests `adset is None` rather than truthiness.
    with pytest.raises(TypeError):
        extract_from_adset({}, ["age_min"])


def test_extracted_keys_come_out_in_properties_order():
    result = extract_from_adset(MOCK_ADSET, ["age_max", "geo_locations", "age_min"])
    assert list(result.keys()) == [
        "age_max",
        "geo_locations",
        "age_min",
        "targeting_automation",
    ]


def test_requesting_targeting_automation_by_name_is_overwritten_by_the_forced_value():
    # The forced write is unconditional and last, so asking for the source
    # adset's targeting_automation gets you the policy value anyway.
    result = extract_from_adset(MOCK_ADSET, ["targeting_automation"])
    assert result == {"targeting_automation": {"advantage_audience": 0}}


def test_extract_does_not_mutate_the_source_adset():
    adset = {
        "id": "a",
        "targeting": {"age_min": 18, "targeting_automation": {"advantage_audience": 1}},
    }
    snapshot = json.dumps(adset)
    extract_from_adset(adset, ["age_min"])
    assert json.dumps(adset) == snapshot


def test_is_level_in_sync_treats_non_dicts_as_empty():
    # The TS `stripTargetingAutomation` returns {} for anything non-object;
    # here anything that is not a dict is {}, so two non-dicts are "in sync".
    assert is_level_in_sync("nonsense", None) is True
    assert is_level_in_sync([1, 2], {}) is True


def test_is_level_in_sync_compares_lists_by_order():
    # `==` is deep and order-insensitive on keys but order-sensitive on lists,
    # exactly like lodash isEqual.
    assert is_level_in_sync({"genders": [1, 2]}, {"genders": [2, 1]}) is False
    assert is_level_in_sync({"genders": [1, 2]}, {"genders": [1, 2]}) is True


def test_diff_property_keys_does_not_special_case_targeting_automation_in_current():
    # Faithful to the TS: `targeting_automation` is filtered out of the stored
    # keys but NOT out of `current`, so a variable that lists it as a property
    # reports it as added forever. Ported as-is; flagged, not fixed.
    stored = {"age_min": 18, "targeting_automation": {"advantage_audience": 0}}
    assert diff_property_keys(stored, ["age_min", "targeting_automation"]) == {
        "added": ["targeting_automation"],
        "removed": [],
        "keys_differ": True,
    }


def test_diff_property_keys_handles_non_dict_stored():
    assert diff_property_keys("nonsense", ["age_min"]) == {
        "added": ["age_min"],
        "removed": [],
        "keys_differ": True,
    }


def test_diff_property_keys_added_and_removed_ordering():
    # `added` follows `current` order, `removed` follows stored insertion order.
    stored = {"genders": [1], "age_min": 18}
    assert diff_property_keys(stored, ["zzz", "aaa"]) == {
        "added": ["zzz", "aaa"],
        "removed": ["genders", "age_min"],
        "keys_differ": True,
    }
