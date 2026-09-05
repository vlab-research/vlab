"""The strata compiler: variables (a design) -> strata (the cells of that design).

A line-by-line port of
`dashboard/src/pages/StudyConfPage/forms/strata/strata.ts`. The TypeScript is
the source of truth; `strata.spec.ts` is the conformance suite and is
translated test-for-test into `test_strata.py`. When the TypeScript changes,
change this file to match rather than "improving" on it here -- a study
authored by an agent must land in the database indistinguishable from one
authored by a human clicking Regenerate in the dashboard.

Everything below works on the JSON wire shape (plain dicts and lists), not on
the pydantic models -- see this package's `__init__` for why. Pydantic models
are accepted as input and dumped to JSON first, because callers holding a
`StudyConf` should not have to remember which shape a function wants.

Vocabulary, since the two words look interchangeable and are not:

    variable  one dimension of the design ("gender"), carrying its levels.
    level     one value of that dimension ("men"), carrying the Facebook
              targeting that reaches it and the share of the sample it should
              get (`quota`).
    stratum   one cell of the full factorial -- one level from every variable.
              Its targeting is the levels' targeting merged; its quota is the
              product of theirs.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel

# The JSON wire shape. Deliberately not a TypedDict: the TypeScript types these
# boundaries `any` (facebook_targeting, metadata, question_targeting), and
# narrowing here would reject confs the dashboard happily writes.
Json = Dict[str, Any]


def _as_dict(value: Any) -> Any:
    """Accept a pydantic model where a wire-shape dict is expected.

    `mode="json"` and not `mode="python"`: the conformance fixtures are JSON
    produced by the real TypeScript, so dates/enums/Decimals have to land in
    their JSON spellings, not as Python objects that merely compare equal to
    themselves.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _js_str(value: Any) -> str:
    """What a JS template literal `${value}` would produce.

    Level and variable names are typed `string` in `types/conf.ts`, so for
    every conf that type-checks this is the identity. It exists for the
    non-string values that reach here off the wire anyway -- a level named
    `18` in YAML, or `1.0`, or `yes` -- where JS would interpolate "18", "1"
    and "true", and so must we. The result is the stratum `id`, which is the
    merge key against saved strata and the value the dashboard reads back, so
    a divergence here is not cosmetic: an agent writing `age:1.0` produces a
    stratum the dashboard (which would compute `age:1`) can never match.

    Coverage: bool, None, int and float. Floats follow JS `Number#toString`
    for the range a level name could plausibly hold (integral floats print
    without the ".0"; others print their shortest round-trip repr, which is
    what Python's `repr` gives too). Exponent-notation thresholds (>= 1e21,
    < 1e-6) are not reproduced; nothing names a level that way.
    """
    if isinstance(value, str):
        return value
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return {float("inf"): "Infinity", float("-inf"): "-Infinity"}.get(value, "NaN")
        if value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


def format_group_product(levels: List[Json], finish_question_ref: str) -> Json:
    """Compile one combination of levels -- one per variable -- into a stratum.

    `levels` are level dicts each carrying an extra `variable_name` key naming
    the variable it came from (the TypeScript's `IntermediateLevel.variableName`).
    Order is significant throughout: it fixes the id, and it decides who wins
    the shallow merges below.
    """
    if not levels:
        # The TypeScript reduces `metadata` with no initial value, so an empty
        # combination throws `TypeError: Reduce of empty array`. Unreachable
        # from `create_strata_from_variables` (a variable with no levels
        # produces no combinations at all), but the function is public, so it
        # fails the same way here rather than inventing an empty stratum.
        raise ValueError("format_group_product needs at least one level")

    tvars = [
        {
            "op": "equal",
            "vars": [
                {"type": "variable", "value": _js_str(level["variable_name"])},
                # The constant keeps the level's raw value: the TypeScript
                # interpolates the variable name but not this one.
                {"type": "constant", "value": level["name"]},
            ],
        }
        for level in levels
    ]

    # Shallow merges, in level order, later levels overwriting earlier keys --
    # JS object spread. Two variables that target the same Facebook key (two
    # age variables, say) do NOT combine; the last one simply wins. That is a
    # property of the design, not of this code.
    metadata: Json = {}
    for level in levels:
        # A JS computed key `{[l.variableName]: ...}` is stringified; the value
        # `l.name` is not. Same asymmetry here, for the same non-string inputs
        # `_js_str` exists for.
        metadata[_js_str(level["variable_name"])] = level["name"]

    id_string = ",".join(
        f"{_js_str(level['variable_name'])}:{_js_str(level['name'])}"
        for level in levels
    )

    targeting: Json = {}
    for level in levels:
        # `{...undefined}` is a no-op in JS; a level with no targeting
        # contributes nothing rather than exploding.
        targeting.update(level.get("facebook_targeting") or {})

    # 1.0 rather than 1 so the product is a float even when every level quota
    # is integral -- JS has one number type and the fixtures are floats.
    quota = 1.0
    for level in levels:
        quota *= level["quota"]

    finish_filter = {
        "op": "answered",
        "vars": [{"type": "variable", "value": finish_question_ref}],
    }

    return {
        "id": id_string,
        "quota": quota,
        "facebook_targeting": targeting,
        "metadata": metadata,
        # A respondent counts toward this stratum only once they have answered
        # the finish question -- the equality terms say who they are, this says
        # they finished.
        "question_targeting": {"op": "and", "vars": [*tvars, finish_filter]},
    }


def _cartesian_product(groups: Sequence[Sequence[Json]]) -> List[List[Json]]:
    """The TypeScript's `cartesianProduct`, which is `itertools.product` order.

    The TS folds left with `a.flatMap(d => b.map(e => [d, e].flat()))`: the
    leftmost group is the outermost loop and its element is held fixed while
    the groups to its right vary, exactly like `product`. A group with no
    elements collapses the whole fold to `[]` there too (`flatMap` over an
    empty `b`, or an empty accumulator), so one variable with no levels means
    no strata at all.
    """
    if not groups:
        # `[].reduce` with no initial value throws in JS. `product()` with no
        # arguments would instead yield one empty combination, which would then
        # blow up in `format_group_product`; refuse it here where the message
        # can say what happened.
        raise ValueError("cartesian product of no variables is undefined")

    return [list(combo) for combo in product(*groups)]


def create_strata_from_variables(
    variables: Iterable[Any],
    finish_question_ref: Optional[str] = None,
    creatives: Optional[Iterable[Any]] = None,
    audiences: Optional[Iterable[Any]] = None,
    existing_strata: Optional[Iterable[Any]] = None,
) -> List[Json]:
    """The full factorial of `variables`, as strata.

    Returns `[]` for no variables and `[]` for a missing/empty
    `finish_question_ref` -- there is no stratum to write without a question
    that says a respondent finished, and the dashboard calls this on every
    keystroke while the form is half-filled.

    `existing_strata`, when given, is merged in by stratum id: the user's
    edits survive, everything derived is recomputed. See the comment at the
    merge itself.
    """
    variables = [_as_dict(v) for v in (variables or [])]
    if not variables:
        return []

    if not finish_question_ref:
        return []

    # JS `creatives ? ... : []`. An empty list is truthy in JS and falsy in
    # Python, but mapping an empty list yields an empty list either way, so
    # `or []` is equivalent here for every input the TypeScript accepts.
    all_creatives = [_as_dict(c)["name"] for c in (creatives or [])]
    all_audiences = [_as_dict(a)["name"] for a in (audiences or [])]

    groups = [
        [{**level, "variable_name": variable["name"]} for level in variable["levels"]]
        for variable in variables
    ]

    new_strata = [
        {
            "audiences": [],
            # New strata exclude every audience by default: a study's audiences
            # are people it has already reached, and the point of the default
            # is not to pay to reach them twice.
            "excluded_audiences": all_audiences,
            "creatives": all_creatives,
            **format_group_product(combination, finish_question_ref),
        }
        for combination in _cartesian_product(groups)
    ]

    existing_strata = [_as_dict(s) for s in (existing_strata or [])]
    if not existing_strata:
        return new_strata

    # Merge by stratum ID: preserve user-edited fields from existing strata,
    # overwrite derived fields with fresh values. Later duplicates win, as in
    # `new Map(...)`.
    existing_by_id = {s["id"]: s for s in existing_strata}

    merged: List[Json] = []
    for new_stratum in new_strata:
        existing = existing_by_id.get(new_stratum["id"])
        if existing is None:
            merged.append(new_stratum)
            continue

        # Preserve user-edited fields: creatives, audiences, excluded_audiences.
        # Overwrite derived fields: facebook_targeting, question_targeting,
        # quota, metadata.
        #
        # quota is DERIVED (product of the level quotas of the variables that
        # make up this stratum), so Regenerate must recompute it. Preserving it
        # meant that editing a level quota in Variables and clicking Regenerate
        # silently kept the old quota -- there was no way to propagate a changed
        # split to an existing study. Hand-edits to a stratum quota are still
        # possible, they just don't survive the next Regenerate, which is what
        # "Regenerates strata from current variables" means.
        stratum = dict(new_stratum)
        for field in ("creatives", "audiences", "excluded_audiences"):
            # Deliberate, small divergence: the TypeScript assigns `undefined`
            # when the existing stratum lacks the field, which JSON.stringify
            # then drops on the way to the server. Python has no `undefined`,
            # so a missing field leaves the freshly computed default in place
            # instead of erasing it. Every stratum off the wire has all three
            # (they are required in `StratumConf` and in `types/conf.ts`), so
            # this only differs for hand-built input.
            if field in existing:
                stratum[field] = existing[field]
        merged.append(stratum)

    return merged


def strata_staleness_hint(
    variables: Iterable[Any], saved_strata: Optional[Iterable[Any]] = None
) -> bool:
    """Would regenerating change the saved strata? A hint for the UI banner.

    A hint, not a diff: it answers cheaply and errs toward "yes", because the
    cost of a spurious banner is a click and the cost of a missing one is a
    study recruiting on a split its author already changed.

    Raises `ValueError` when `saved_strata` carry no `answered` term -- see
    `get_finish_question_ref`.
    """
    variables = [_as_dict(v) for v in (variables or [])]
    saved_strata = [_as_dict(s) for s in (saved_strata or [])]

    if not saved_strata:
        return len(variables) > 0

    # Generate what the strata would be from current variables (without merging)
    # Use a dummy finishQuestionRef if one doesn't exist in savedStrata.
    finish_ref = get_finish_question_ref(saved_strata)
    if not finish_ref:
        finish_ref = "dummy"

    fresh_strata = create_strata_from_variables(variables, finish_ref)

    # Check 1: different set of stratum IDs.
    saved_ids = [s["id"] for s in saved_strata]
    fresh_ids = [s["id"] for s in fresh_strata]

    if len(saved_ids) != len(fresh_ids):
        return True

    for stratum_id in saved_ids:
        if stratum_id not in fresh_ids:
            return True

    # Check 2: facebook_targeting changed for any stratum that exists in both.
    # Deep equality rather than a serialized comparison, so that backend JSON
    # key-order differences (Go sorts map keys alphabetically) don't falsely
    # flag strata as stale. Python's `==` on dicts/lists IS lodash `isEqual`
    # for JSON-shaped data; the two disagree only on NaN (`isEqual` says equal,
    # `==` says not) and on types JSON cannot carry anyway.
    for saved_stratum in saved_strata:
        fresh_stratum = _find_by_id(fresh_strata, saved_stratum["id"])
        if fresh_stratum is not None and fresh_stratum.get(
            "facebook_targeting"
        ) != saved_stratum.get("facebook_targeting"):
            return True

    # Check 3: quota changed for any stratum that exists in both. Without this,
    # editing only the level quotas in Variables (same levels, same targeting)
    # left the strata silently out of date with no banner -- the study kept
    # recruiting on the old split. Compare with a tolerance: quotas are products
    # of floats that round-trip through JSON, so exact equality would flag
    # spurious staleness (0.1 * 3 != 0.3).
    for saved_stratum in saved_strata:
        fresh_stratum = _find_by_id(fresh_strata, saved_stratum["id"])
        if fresh_stratum is None:
            continue
        if "quota" not in saved_stratum:
            # Absent key: JS reads `undefined`, `fresh - undefined` is NaN, and
            # `NaN > 1e-9` is false, i.e. not stale. Skipping mirrors that.
            continue
        saved_quota = saved_stratum["quota"]
        if saved_quota is None:
            # JSON null is a different case from a missing key: JS coerces
            # `null` to 0 in arithmetic, so `fresh - null === fresh` and the
            # stratum reads as stale whenever the fresh quota is non-zero.
            # Conflating the two here (a `.get("quota")` returning None for
            # both) gave the wrong answer for `quota: null` -- caught in review
            # of the port, not by the fixtures, which never emit null quotas.
            saved_quota = 0
        if abs(fresh_stratum["quota"] - saved_quota) > 1e-9:
            return True

    return False


def _find_by_id(strata: Sequence[Json], stratum_id: Any) -> Optional[Json]:
    return next((s for s in strata if s["id"] == stratum_id), None)


def get_finish_question_ref(strata: Iterable[Any]) -> str:
    """The question ref every stratum's `answered` term points at.

    Read off the first stratum only, as in the TypeScript: the ref is a
    property of the study, and strata that disagreed about it would be
    incoherent rather than interestingly different.

    Returns `""` for no strata. Raises `ValueError` when the first stratum has
    no `answered` term or no `question_targeting` at all: the TypeScript throws
    a `TypeError` there (`finishFilter.vars` on `undefined`), so raising keeps
    the behaviour, and a caller cannot do anything useful with a wrong-but-
    plausible `""` -- it would be written into every regenerated stratum.
    """
    strata = [_as_dict(s) for s in (strata or [])]
    # `strata[0]` is None, not `not strata[0]`: JS `!s` is false for `{}`, so
    # an empty first stratum falls through to the property access and throws.
    # Treating `{}` as "no strata" here returned "" instead, which the caller
    # would then write into every regenerated stratum as the finish ref.
    if not strata or strata[0] is None:
        return ""

    s = strata[0]
    targeting_vars = (s.get("question_targeting") or {}).get("vars") or []
    finish_filter = next((v for v in targeting_vars if v.get("op") == "answered"), None)
    if finish_filter is None:
        raise ValueError(
            f"stratum {s.get('id')!r} has no 'answered' term in its question_targeting; "
            "cannot tell which question marks a respondent finished"
        )

    return finish_filter["vars"][0]["value"]
