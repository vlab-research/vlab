"""Differential test: every case in `conformance_fixtures.json` replayed here.

The fixtures are not expectations someone wrote down — they are recordings of
the *real* TypeScript (`dashboard/src/pages/StudyConfPage/forms/strata/strata.ts`
and `.../variables/extract.ts`) running over 1,100+ inputs: every literal from
`strata.spec.ts` and `extract.test.ts`, a set of hand-written edge cases, and a
seeded pseudo-random sweep. Each record is `(name, fn, args, result | error)`.
This module calls the Python port with the same args and asserts the same
output, which is the only thing that makes the port trustworthy — the same
discipline that validated `adopt/server/slugify.py` against `gosimple/slug`.

Regenerate with `make -C adopt authoring-fixtures` whenever the TypeScript
changes; the generator is `dashboard/scripts/authoring-conformance.ts` and its
header documents which inputs are deliberately excluded (the ones whose
TypeScript behaviour is a TypeError).

Three spellings are translated, and only three: the recorded errors carry the
TypeScript's `adsetName`/`propertyKey`, `diffPropertyKeys` returns
`keysDiffer`, and `formatGroupProduct`'s intermediate levels carry
`variableName` where the port reads `variable_name` (see `LEVEL_KEYS`). None
of the three is a wire-format name. Everything else must match exactly, floats included — both
runtimes are IEEE doubles multiplying the same numbers in the same order, so a
float mismatch is a real ordering difference, not something to paper over with
a tolerance.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import pytest

from . import extract as extract_mod
from . import strata as strata_mod

FIXTURES = Path(__file__).with_name("conformance_fixtures.json")
DOC = json.loads(FIXTURES.read_text())

FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "format_group_product": strata_mod.format_group_product,
    "create_strata_from_variables": strata_mod.create_strata_from_variables,
    "strata_staleness_hint": strata_mod.strata_staleness_hint,
    "get_finish_question_ref": strata_mod.get_finish_question_ref,
    "extract_from_adset": extract_mod.extract_from_adset,
    "is_level_in_sync": extract_mod.is_level_in_sync,
    "diff_property_keys": extract_mod.diff_property_keys,
}

ERROR_TYPES: Dict[str, Type[extract_mod.ExtractError]] = {
    "AdsetNotFoundError": extract_mod.AdsetNotFoundError,
    "PropertyMissingError": extract_mod.PropertyMissingError,
}

# TypeScript field name -> Python attribute, for the recorded exceptions.
ERROR_FIELDS = {"adsetName": "adset_name", "propertyKey": "property_key"}

# TypeScript result key -> Python result key. One entry, by design.
RESULT_KEYS = {"keysDiffer": "keys_differ"}

# `format_group_product` takes "intermediate levels": a level dict plus the name
# of the variable it came from. The TypeScript calls that key `variableName`
# (`IntermediateLevel`), the port calls it `variable_name`. The shape is
# internal — `create_strata_from_variables` builds it and nothing puts it on the
# wire — so this is the same kind of spelling difference as `keysDiffer`, and
# the harness translates it rather than the port carrying a JS name.
LEVEL_KEYS = {"variableName": "variable_name"}

# The functions whose TypeScript return type is a plain boolean. `True == 1` in
# Python, so the recorded booleans are checked by identity, not equality.
BOOLEAN_FNS = {"strata_staleness_hint", "is_level_in_sync"}


def _params(section: str) -> List[Any]:
    return [pytest.param(case, id=case["name"]) for case in DOC[section]]


def _expected(case: Dict[str, Any]) -> Any:
    """The recorded TypeScript result, in Python spelling."""
    result = case["result"]
    if case["fn"] == "diff_property_keys" and isinstance(result, dict):
        return {RESULT_KEYS.get(k, k): v for k, v in result.items()}
    return result


def _args(case: Dict[str, Any]) -> List[Any]:
    """The recorded TypeScript args, in Python spelling."""
    args = case["args"]
    if case["fn"] == "format_group_product":
        levels = [
            {LEVEL_KEYS.get(k, k): v for k, v in level.items()} for level in args[0]
        ]
        return [levels] + args[1:]
    return args


def _mismatch(actual: Any, expected: Any, path: str = "") -> Optional[str]:
    """First structural difference between the two, or None.

    Deliberately stricter than `==`: `True == 1` and `1 == 1.0` both hold in
    Python, and a port that returned `1` where the TypeScript returned `true`
    would otherwise slip through. Numbers still compare across int/float,
    because JavaScript has one number type — a quota product of `3` there is
    `3` or `3.0` here depending on the operands, and both are correct.
    """
    where = path or "<result>"

    if isinstance(expected, bool) or isinstance(actual, bool):
        if actual is not expected:
            return f"{where}: expected {expected!r}, got {actual!r}"
        return None

    if expected is None or actual is None:
        if actual is not expected:
            return f"{where}: expected {expected!r}, got {actual!r}"
        return None

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            got = type(actual).__name__
            return f"{where}: expected an object, got {got} {actual!r}"
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        if missing or extra:
            return f"{where}: keys differ (missing {missing}, unexpected {extra})"
        for key in expected:
            found = _mismatch(actual[key], expected[key], f"{where}.{key}")
            if found:
                return found
        return None

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return f"{where}: expected a list, got {type(actual).__name__} {actual!r}"
        if len(actual) != len(expected):
            return f"{where}: expected {len(expected)} items, got {len(actual)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            found = _mismatch(a, e, f"{where}[{i}]")
            if found:
                return found
        return None

    if isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)):
            return f"{where}: expected a number, got {type(actual).__name__} {actual!r}"
        # Exact: no tolerance. See the module docstring.
        if actual != expected:
            return f"{where}: expected {expected!r}, got {actual!r}"
        return None

    if type(actual) is not type(expected) or actual != expected:
        return f"{where}: expected {expected!r}, got {actual!r}"
    return None


def _check(case: Dict[str, Any]) -> None:
    fn = FUNCTIONS[case["fn"]]
    args = _args(case)
    context = f"case {case['name']} ({case['fn']}) args={json.dumps(case['args'])}"

    if "error" in case:
        recorded = case["error"]
        with pytest.raises(ERROR_TYPES[recorded["name"]]) as excinfo:
            fn(*args)
        raised = excinfo.value
        assert type(raised).__name__ == recorded["name"], context
        for ts_field, attribute in ERROR_FIELDS.items():
            if ts_field not in recorded:
                continue
            got = getattr(raised, attribute, "<attribute missing>")
            assert got == recorded[ts_field], (
                f"{context}\nTypeScript {ts_field}={recorded[ts_field]!r}, "
                f"Python {attribute}={got!r}"
            )
        return

    actual = fn(*args)
    expected = _expected(case)

    if case["fn"] in BOOLEAN_FNS:
        assert isinstance(actual, bool), f"{context}\nexpected a bool, got {actual!r}"

    found = _mismatch(actual, expected)
    assert found is None, (
        f"{context}\n{found}\n"
        f"TypeScript: {json.dumps(expected, sort_keys=True)}\n"
        f"Python:     {json.dumps(actual, sort_keys=True, default=repr)}"
    )


@pytest.mark.parametrize("case", _params("strata"))
def test_strata_conformance(case: Dict[str, Any]) -> None:
    _check(case)


@pytest.mark.parametrize("case", _params("extract"))
def test_extract_conformance(case: Dict[str, Any]) -> None:
    _check(case)


# A truncated or half-written regeneration is the failure mode a fixture-driven
# suite hides best: every case still passes, there are just fewer of them. These
# floors are the counts the committed fixture file was generated with.
MINIMUM_CASES = {"strata": 589, "extract": 567}
MINIMUM_RANDOM_CASES = 500


def test_fixture_case_counts() -> None:
    for section, minimum in MINIMUM_CASES.items():
        assert len(DOC[section]) >= minimum, (
            f"{section} has {len(DOC[section])} cases, expected at least "
            f"{minimum} — regenerate with `make -C adopt authoring-fixtures`"
        )
        random_cases = [c for c in DOC[section] if c["name"].startswith("random/")]
        assert len(random_cases) >= MINIMUM_RANDOM_CASES, (
            f"{section} has {len(random_cases)} seeded random cases, "
            f"expected at least {MINIMUM_RANDOM_CASES}"
        )


def test_fixture_covers_every_function() -> None:
    covered = {c["fn"] for c in DOC["strata"] + DOC["extract"]}
    assert covered == set(FUNCTIONS), f"uncovered: {set(FUNCTIONS) - covered}"


def test_fixture_covers_both_error_types() -> None:
    raised = {c["error"]["name"] for c in DOC["extract"] if "error" in c}
    assert raised == set(ERROR_TYPES), f"unrecorded: {set(ERROR_TYPES) - raised}"


def test_fixture_covers_both_boolean_outcomes() -> None:
    for fn in BOOLEAN_FNS:
        results = {
            c["result"]
            for c in DOC["strata"] + DOC["extract"]
            if c["fn"] == fn and "result" in c
        }
        assert results == {True, False}, f"{fn} only ever returned {results}"


def test_fixture_case_names_are_unique() -> None:
    names = [c["name"] for c in DOC["strata"] + DOC["extract"]]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, f"duplicate case names: {duplicates}"
