"""The negative control the review of PR #254 asked for
(planning/agent-study-authoring.md §12.5): "the nine seeded divergences ...
left no artifact. The merge-precedence reversal is reproducible (190 of 1,147
fail); the nine mutations are not."

`test_conformance.py` proves the port agrees with the real TypeScript on every
recorded case. That is only convincing if the fixtures are actually capable of
catching a wrong port -- a differential suite that passes because the fixtures
are too narrow to exercise the difference is worse than no suite, because it
looks green for the wrong reason. This module seeds ten deliberate mutations
into the port (via `monkeypatch`, reverted after each test) and asserts that
at least one fixture in `conformance_fixtures.json` fails against each one.
If a mutation stops being detectable -- because a fixture was narrowed, or the
comparator was loosened -- this file fails and says which mutation got away.

Each mutation targets one specific way a port CAN silently diverge from its
reference implementation, chosen to cover the failure modes the review
actually found or worried about:

    1. one-ULP quota            floating-point drift in a derived number
    2. False stringified as "0" `_js_str`'s bool branch, not its truthiness
    3. an extra output key       the comparator's dict key-set check
    4. reordered strata          the comparator's list order-sensitivity
    5. wrong `propertyKey`       a typed exception's payload, not just its type
    6. a suppressed exception    "helpfully" swallowing an error the TS raises
    7. a renamed result key      keys_differ -> keysDiffer (see RESULT_KEYS
                                 in test_conformance.py -- this is the
                                 TypeScript's own spelling, reintroduced)
    8. number returned as string a JSON type change the comparator must catch
    9. swapped merge winner      existing_strata's fields vs freshly-derived
                                 defaults, for the three preserved fields
   10. reversed shallow-merge    the exact case the merge-precedence comment
       precedence                in strata.py warns about; also the headline
                                 example from the *first* attempt at a
                                 negative control (190/1,147 cases failed)

Every mutation re-resolves the target function from its module at call time
(`getattr(mod, name)`, not a name captured in a closure at import time) so that
`monkeypatch.setattr(module, name, ...)` is actually observed -- `strata.py`
calls `format_group_product` and `_js_str` as bare module-global names, which
Python looks up fresh on every call, so this works without needing to patch
every call site individually.
"""

import math
from typing import Any, Callable, Dict, List, Tuple

from . import extract as extract_mod
from . import strata as strata_mod
from .test_conformance import DOC, ERROR_FIELDS, _args, _expected, _mismatch

# fn name (as recorded in the fixtures) -> (module, attribute) to resolve it
# from at call time. Deliberately not `test_conformance.FUNCTIONS`: that dict
# is built once, at import time, so it holds the *original* function objects
# and would not observe a `monkeypatch.setattr` on the module.
_FUNCTION_LOOKUP: Dict[str, Tuple[Any, str]] = {
    "format_group_product": (strata_mod, "format_group_product"),
    "create_strata_from_variables": (strata_mod, "create_strata_from_variables"),
    "strata_staleness_hint": (strata_mod, "strata_staleness_hint"),
    "get_finish_question_ref": (strata_mod, "get_finish_question_ref"),
    "extract_from_adset": (extract_mod, "extract_from_adset"),
    "properties_on_some_level": (extract_mod, "properties_on_some_level"),
    "is_level_in_sync": (extract_mod, "is_level_in_sync"),
    "diff_property_keys": (extract_mod, "diff_property_keys"),
}


def _diverges(case: Dict[str, Any]) -> bool:
    """True iff the (possibly mutated) port disagrees with this one recorded
    TypeScript case. Same checks as `test_conformance._check`, but returning a
    bool instead of asserting, so a mutation test can ask "did ANY of these
    fixtures notice?" rather than fail on the first one that does.
    """
    mod, attr = _FUNCTION_LOOKUP[case["fn"]]
    fn: Callable[..., Any] = getattr(mod, attr)
    args = _args(case)

    if "error" in case:
        recorded = case["error"]
        try:
            fn(*args)
        except Exception as raised:  # noqa: BLE001 - mirrors test_conformance
            if type(raised).__name__ != recorded["name"]:
                return True
            for ts_field, attribute in ERROR_FIELDS.items():
                if ts_field not in recorded:
                    continue
                got = getattr(raised, attribute, "<attribute missing>")
                if got != recorded[ts_field]:
                    return True
            return False
        else:
            # The TypeScript raises here; a port that does not has diverged,
            # whether that is the mutation under test or a real regression.
            return True

    try:
        actual = fn(*args)
    except Exception:  # noqa: BLE001 - the TS did not raise for this case
        return True

    return _mismatch(actual, _expected(case)) is not None


def _any_diverges(cases: List[Dict[str, Any]]) -> bool:
    return any(_diverges(c) for c in cases)


def _strata_cases(*, fn: str = None, error: bool = False) -> List[Dict[str, Any]]:
    cases = DOC["strata"]
    if fn is not None:
        cases = [c for c in cases if c["fn"] == fn]
    return [c for c in cases if ("error" in c) == error]


def _extract_cases(*, fn: str = None, error_name: str = None) -> List[Dict[str, Any]]:
    cases = DOC["extract"]
    if fn is not None:
        cases = [c for c in cases if c["fn"] == fn]
    if error_name is not None:
        cases = [c for c in cases if c.get("error", {}).get("name") == error_name]
    return cases


def test_detector_reports_no_divergence_without_any_mutation() -> None:
    """Sanity check for `_diverges` itself, before trusting it below: replaying
    every fixture against the real, unmutated port must find nothing --
    `test_conformance.py` already asserts this case by case. A `_diverges`
    that always returned `True` (a bug in this file, not the port) would make
    every mutation test below pass for the wrong reason.
    """
    assert not _any_diverges(DOC["strata"])
    assert not _any_diverges(DOC["extract"])


def test_one_ulp_quota_perturbation_is_detected(monkeypatch) -> None:
    # Nudges the derived quota by the smallest representable step. The
    # comparator does this on purpose (see its module docstring: "both
    # runtimes are IEEE doubles ... so a float mismatch is a real ordering
    # difference, not something to paper over with a tolerance") -- a quota
    # bug this small would otherwise hide behind a tolerant comparison.
    original = strata_mod.format_group_product

    def mutated(levels, finish_question_ref):
        result = original(levels, finish_question_ref)
        result = dict(result)
        result["quota"] = math.nextafter(result["quota"], math.inf)
        return result

    monkeypatch.setattr(strata_mod, "format_group_product", mutated)
    cases = _strata_cases(fn="format_group_product") + _strata_cases(
        fn="create_strata_from_variables"
    )
    assert _any_diverges(cases)


def test_false_stringified_as_0_is_detected(monkeypatch) -> None:
    # `_js_str`'s job is JS's `${value}` coercion, where `${false}` is
    # `"false"`, not `"0"`. Targets the boolean-name fixtures added
    # specifically for this (see authoring-conformance.ts, "2.5. Review
    # follow-ups") -- this test also therefore guards against those fixtures
    # being narrowed away later.
    original = strata_mod._js_str

    def mutated(value):
        if value is False:
            return "0"
        return original(value)

    monkeypatch.setattr(strata_mod, "_js_str", mutated)
    cases = [c for c in DOC["strata"] if "boolean-false" in c["name"]]
    assert cases, "expected boolean-false fixtures from the extended generator"
    assert _any_diverges(cases)


def test_extra_key_in_stratum_output_is_detected(monkeypatch) -> None:
    original = strata_mod.format_group_product

    def mutated(levels, finish_question_ref):
        result = dict(original(levels, finish_question_ref))
        result["__debug"] = True
        return result

    monkeypatch.setattr(strata_mod, "format_group_product", mutated)
    cases = _strata_cases(fn="format_group_product") + _strata_cases(
        fn="create_strata_from_variables"
    )
    assert _any_diverges(cases)


def test_reordered_strata_output_is_detected(monkeypatch) -> None:
    original = strata_mod.create_strata_from_variables

    def mutated(*args, **kwargs):
        return list(reversed(original(*args, **kwargs)))

    monkeypatch.setattr(strata_mod, "create_strata_from_variables", mutated)
    cases = _strata_cases(fn="create_strata_from_variables")
    assert _any_diverges(cases)


def test_wrong_property_key_in_raised_error_is_detected(monkeypatch) -> None:
    original_init = extract_mod.PropertyMissingError.__init__

    def mutated_init(self, adset_name, property_key):
        original_init(self, adset_name, "WRONG_PROPERTY_KEY")

    monkeypatch.setattr(extract_mod.PropertyMissingError, "__init__", mutated_init)
    cases = _extract_cases(error_name="PropertyMissingError")
    assert cases
    assert _any_diverges(cases)


def test_suppressed_property_missing_error_is_detected(monkeypatch) -> None:
    # A plausible "helpful" bug: instead of raising when a requested property
    # is absent, fill it with None and carry on. Silently swallows exactly the
    # signal that tells an agent its template ad set is missing a property.
    original = extract_mod.extract_from_adset

    def mutated(adset, properties):
        try:
            return original(adset, properties)
        except extract_mod.PropertyMissingError:
            targeting = (adset or {}).get("targeting") or {}
            extracted = {p: targeting.get(p) for p in properties}
            extracted["targeting_automation"] = {"advantage_audience": 0}
            return extracted

    monkeypatch.setattr(extract_mod, "extract_from_adset", mutated)
    cases = _extract_cases(error_name="PropertyMissingError")
    assert cases
    assert _any_diverges(cases)


def test_renamed_result_key_is_detected(monkeypatch) -> None:
    # Reintroduces the TypeScript's own spelling (`keysDiffer`) as the port's
    # output key, which is exactly what `test_conformance.RESULT_KEYS`
    # translates away -- so this doubles as a check that the translation is
    # load-bearing and not a no-op.
    original = extract_mod.diff_property_keys

    def mutated(stored, current):
        result = dict(original(stored, current))
        result["keysDiffer"] = result.pop("keys_differ")
        return result

    monkeypatch.setattr(extract_mod, "diff_property_keys", mutated)
    cases = _extract_cases(fn="diff_property_keys")
    assert _any_diverges(cases)


def test_quota_returned_as_string_is_detected(monkeypatch) -> None:
    original = strata_mod.format_group_product

    def mutated(levels, finish_question_ref):
        result = dict(original(levels, finish_question_ref))
        result["quota"] = str(result["quota"])
        return result

    monkeypatch.setattr(strata_mod, "format_group_product", mutated)
    cases = _strata_cases(fn="format_group_product") + _strata_cases(
        fn="create_strata_from_variables"
    )
    assert _any_diverges(cases)


def test_swapped_merge_winner_is_detected(monkeypatch) -> None:
    """`create_strata_from_variables` is supposed to keep EXISTING (saved)
    creatives/audiences/excluded_audiences and overwrite everything derived
    with FRESH values (see the long comment at the merge site in strata.py).
    Swap which side wins for the three preserved fields -- discard the user's
    edits, keep the freshly generated defaults instead -- and confirm at least
    one merge fixture notices.
    """
    original = strata_mod.create_strata_from_variables

    def mutated(
        variables,
        finish_question_ref=None,
        creatives=None,
        audiences=None,
        existing_strata=None,
    ):
        merged = original(
            variables, finish_question_ref, creatives, audiences, existing_strata
        )
        if not existing_strata:
            return merged
        # Fields are re-derived from scratch, then substituted in over the
        # correctly-merged result: this can't be done by re-reading
        # `existing_strata` directly, because it is keyed by stratum id and
        # so is `merged` -- swapping in the *fresh* value at each id is the
        # actual bug this simulates (Regenerate discarding user edits).
        fresh_only = original(
            variables, finish_question_ref, creatives, audiences, None
        )
        fresh_by_id = {s["id"]: s for s in fresh_only}
        swapped = []
        for stratum in merged:
            fresh = fresh_by_id.get(stratum["id"])
            if fresh is None:
                swapped.append(stratum)
                continue
            stratum = dict(stratum)
            for field in ("creatives", "audiences", "excluded_audiences"):
                stratum[field] = fresh[field]
            swapped.append(stratum)
        return swapped

    monkeypatch.setattr(strata_mod, "create_strata_from_variables", mutated)
    cases = [
        c
        for c in _strata_cases(fn="create_strata_from_variables")
        if len(c["args"]) > 4 and c["args"][4]  # existing_strata present
    ]
    assert cases
    assert _any_diverges(cases)


def test_reversed_shallow_merge_precedence_is_detected(monkeypatch) -> None:
    """The headline example from the *first* attempt at a negative control
    (planning/agent-study-authoring.md §12.1: "reversing the shallow-merge
    precedence in the port fails 190 cases") -- pinned here so the claim has
    an artifact. Levels are merged in reverse order, so the FIRST variable's
    targeting key wins a collision instead of the last, exactly the
    precedence `format_group_product`'s comment warns is a property of the
    design and must not be touched.
    """
    original = strata_mod.format_group_product

    def mutated(levels, finish_question_ref):
        result = dict(original(levels, finish_question_ref))
        targeting: Dict[str, Any] = {}
        for level in reversed(levels):
            targeting.update(level.get("facebook_targeting") or {})
        result["facebook_targeting"] = targeting
        return result

    monkeypatch.setattr(strata_mod, "format_group_product", mutated)
    cases = _strata_cases(fn="format_group_product") + _strata_cases(
        fn="create_strata_from_variables"
    )
    assert _any_diverges(cases)
