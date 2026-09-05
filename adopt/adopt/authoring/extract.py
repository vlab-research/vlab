"""Pull `facebook_targeting` off a template ad set — a port of the dashboard's
`dashboard/src/pages/StudyConfPage/forms/variables/extract.ts`.

Same three jobs as the TypeScript: extract the requested targeting properties
from a Meta ad set (`extract_from_adset`), tell whether a saved level still
matches what an Apply would write right now (`is_level_in_sync`), and diff the
*set of keys* a saved level was built from against the variable's current
property list (`diff_property_keys`). Typed errors, rather than a bare string,
so the caller can render a specific, actionable message.

Everything here works on the JSON wire shape — plain dicts and lists — for the
reasons given in this package's `__init__` docstring. The TypeScript is `any`
at every one of these boundaries, and conformance is defined against the JSON,
not against a model.

Where JavaScript semantics do not survive the trip (truthiness, `in` on
`undefined`, `isEqual` vs `==`) the divergence is called out in a comment at
the point it bites. Nothing is "fixed" on the way across: the dashboard and
this module have to agree, so a TypeScript oddity is reproduced, not repaired.
"""

from typing import Any, Dict, List, Optional, TypedDict

__all__ = [
    "ExtractError",
    "AdsetNotFoundError",
    "PropertyMissingError",
    "PropertyKeyDiff",
    "extract_from_adset",
    "is_level_in_sync",
    "diff_property_keys",
]


class ExtractError(Exception):
    """Common base for every error this module raises.

    Deliberately an `Exception`, not a `BaseException`. `study_conf.InvalidConfigError`
    inherits from `BaseException` and that is the anti-pattern this repo is
    moving away from: it slips through every `except Exception` in the service
    and past Starlette's exception middleware, so a bad config reaches the
    caller as a bare 500 while the message that would have explained it goes to
    the log (planning/agent-study-authoring.md §11.4).
    A caller that wants to catch everything from here catches `ExtractError`;
    a caller that catches `Exception` gets these too, which is what it wants.
    """


class AdsetNotFoundError(ExtractError):
    """The template ad set was not returned by Meta at all."""

    def __init__(self, adset_name: str) -> None:
        super().__init__(f"Template adset {adset_name} not found on Meta")
        self.adset_name = adset_name


class PropertyMissingError(ExtractError):
    """The ad set exists, but a requested targeting property is not on it."""

    def __init__(self, adset_name: str, property_key: str) -> None:
        super().__init__(f"Adset {adset_name} has no {property_key} property")
        self.adset_name = adset_name
        self.property_key = property_key


def extract_from_adset(
    adset: Optional[Dict[str, Any]],
    properties: List[str],
    optional: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Extract the requested properties from an ad set's targeting.

    :param adset: the ad set as it comes back from the Meta API. Needs `id` and
        `targeting`; `name` is used for error messages when present.
    :param properties: property keys to extract, e.g. `["geo_locations", "age_min"]`.
    :param optional: properties whose absence is tolerated: a missing one is
        left out of the result rather than raised. `properties_on_some_level`
        is where a caller gets this list. The TS default is `[]`; `None` here
        so the two-argument call the conformance fixtures record is unchanged.
    :returns: the extracted properties, in `properties` order, plus a forced
        `targeting_automation`.
    :raises AdsetNotFoundError: if `adset` is None.
    :raises PropertyMissingError: if a requested, non-optional property is not
        present.
    :raises TypeError: if `adset` has no dict `targeting` and at least one
        property was requested. The TypeScript throws a TypeError here too
        (`'x' in undefined`); this raises one with a message that says what
        actually went wrong.
    """
    # The TS guard is `if (!adset)`, JS truthiness. It cannot be transcribed as
    # `if not adset`: an empty object is *truthy* in JS but an empty dict is
    # falsy in Python, and `{}` must fall through to the targeting read (and
    # its TypeError) exactly as it does in the TS. On the JSON wire shape the
    # only falsy values an ad set slot can hold are `null`/absent, so testing
    # identity against None covers the real inputs without the `{}` divergence.
    if adset is None:
        raise AdsetNotFoundError("(unknown)")

    # JS `adset.name || adset.id` falls through on any falsy name — an empty
    # string or a null name lands on the id. `or` reproduces that for the values
    # a JSON name can hold. Typed `Any` because it is whatever the JSON held;
    # the TS interpolates it into the message without checking either.
    label: Any = adset.get("name") or adset.get("id")

    tolerated = optional or []

    extracted: Dict[str, Any] = {}

    for property_key in properties:
        # Read `targeting` per iteration, as the TS does. It matters: with an
        # empty `properties` list the TS never touches `adset.targeting`, so an
        # ad set with no targeting at all succeeds and returns only the forced
        # `targeting_automation`. Hoisting this check above the loop would turn
        # that success into an error.
        targeting = adset.get("targeting")
        if not isinstance(targeting, dict):
            raise TypeError(
                f"Adset {label} has no targeting object; cannot extract "
                "properties from it"
            )

        # `property in adset.targeting` in the TS is a KEY PRESENCE test, not a
        # value test: a key explicitly set to `undefined` counts as present in
        # JS and passes this check (its `undefined` value is then copied out).
        # JSON has no `undefined`, so in Python a key is either in the dict or
        # not, and `in` is the same test. A key present with value `None` (JSON
        # `null`) is present in both languages and is copied through as-is.
        if property_key not in targeting:
            if property_key in tolerated:
                continue
            raise PropertyMissingError(label, property_key)

        extracted[property_key] = targeting[property_key]

    # Always force Advantage+ Audience off. We never use Advantage+ audience —
    # it imposes constraints (e.g. age_min <= 25 as a "control" via
    # individual_setting) that we'd have to remember and validate against. By
    # always sending {advantage_audience: 0} without individual_setting, we
    # avoid all Advantage+ audience rules while still using the targeting
    # properties pulled from the source ad set. This is a deliberate policy
    # decision, not a fallback — which is why it overwrites whatever the source
    # ad set had, including a `targeting_automation` the caller asked for by
    # name in `properties`.
    extracted["targeting_automation"] = {"advantage_audience": 0}

    return extracted


def properties_on_some_level(
    levels: List[Dict[str, Any]],
    adsets: List[Dict[str, Any]],
    properties: List[str],
) -> List[str]:
    """The subset of `properties` that at least one level's ad set carries.

    A variable declares its properties once, but its levels come from
    different ad sets and Meta only writes a targeting key when it is set.
    `excluded_geo_locations` is the usual case: the "Urban" level excludes the
    rural regions, the "Rural" level excludes nothing, and Meta stores nothing
    for it. That absence is the level's real targeting, not an authoring
    mistake, so the level copies what it has and omits the rest. A property
    that *no* level carries is a different thing -- the variable is asking for
    data none of its ad sets have -- and stays an error. The result is what a
    caller passes to `extract_from_adset` as `optional`.

    A level whose ad set is not in `adsets` contributes nothing; it reports
    `AdsetNotFoundError` on its own. So does an ad set with no dict
    `targeting` -- the TS tests `t && typeof t === 'object'`, which is what
    `isinstance(..., dict)` is on the JSON wire shape.
    """
    targetings = []
    for level in levels or []:
        adset_id = level.get("template_adset")
        adset = next((a for a in (adsets or []) if a.get("id") == adset_id), None)
        targeting = adset.get("targeting") if adset is not None else None
        if isinstance(targeting, dict):
            targetings.append(targeting)
    return [p for p in (properties or []) if any(p in t for t in targetings)]


def _strip_targeting_automation(obj: Any) -> Dict[str, Any]:
    """A shallow copy of `obj` without `targeting_automation`; `{}` for a non-dict.

    The TS test is `!obj || typeof obj !== 'object'`, which also lets arrays
    through (and spreads them into index-keyed objects). `isinstance(obj, dict)`
    is the honest analog for JSON-shaped data: a targeting blob is an object or
    it is nothing. The copy is why neither caller mutates its input.
    """
    if not isinstance(obj, dict):
        return {}
    clone = dict(obj)
    clone.pop("targeting_automation", None)
    return clone


def is_level_in_sync(stored: Any, would_apply: Any) -> bool:
    """True iff `stored` and `would_apply` are the same targeting, ignoring the
    always-emitted `targeting_automation` block.

    Used by the level UI to detect drift between what the user saved and what
    Apply would write right now.

    The TS goes through lodash `isEqual` rather than `JSON.stringify` because a
    fresh Apply builds keys in `variable.properties` order while the saved blob
    may have a different order — the two are otherwise equivalent, but a
    stringify comparison would call them out of sync. Python's `==` on
    dicts/lists is the same deep, order-insensitive-on-keys comparison: key
    order is irrelevant on both sides, at every level of nesting, while list
    order is significant on both sides. So `==` is the port of `isEqual`, and
    the reason for not writing `json.dumps(...) == json.dumps(...)` is the same
    reason the TS gives.

    One deep-equality divergence, harmless on real JSON but worth knowing:
    Python considers `True == 1`, so `{"x": true}` and `{"x": 1}` compare equal
    here and unequal under `isEqual`. Meta returns one or the other for a given
    field, never both, so this has no effect in practice.
    """
    return _strip_targeting_automation(stored) == _strip_targeting_automation(
        would_apply
    )


class PropertyKeyDiff(TypedDict):
    """What `diff_property_keys` returns. A plain dict at runtime."""

    added: List[str]
    removed: List[str]
    keys_differ: bool


def diff_property_keys(stored: Any, current: List[str]) -> PropertyKeyDiff:
    """Diff the key set that produced `stored` against the currently-selected
    `current` properties.

    `targeting_automation` is engine noise, not a user choice, so it never
    counts as a stored key. The returned `keys_differ` is what triggers the
    level's two-line banner in the dashboard; when only values drift, the level
    renders the one-line banner instead.

    Note the field is `keys_differ` here and `keysDiffer` in the TS: this is a
    Python API, and the conformance harness maps the names.

    `added` comes out in `current` order and `removed` in stored-key (that is,
    insertion) order — both inherited from the TS, which filters the two lists
    rather than differencing sets. Neither input is mutated.
    """
    stored_keys = [
        k
        for k in (stored.keys() if isinstance(stored, dict) else [])
        if k != "targeting_automation"
    ]
    current_keys = list(current or [])

    # The TS compares `[...keys].sort().join('|')` on each side. Comparing the
    # sorted lists directly is equivalent, and strictly better: joining is only
    # ambiguous if a key itself contains "|", where e.g. ["a|b"] and ["a", "b"]
    # both join to "a|b". Meta targeting keys are identifiers, so the two
    # implementations cannot disagree on any real input.
    keys_differ = sorted(stored_keys) != sorted(current_keys)

    added = [k for k in current_keys if k not in stored_keys]
    removed = [k for k in stored_keys if k not in current_keys]

    return {"added": added, "removed": removed, "keys_differ": keys_differ}
