"""Radius geo-targeting: a list of points becomes one targeting level.

Salvaged from the notebook era (`adopt/configuration.py`, superseded) because it
is the clearest example of what plan §6.D says the SDK is for. The dashboard's
Variables form cannot express "target these 47 towns by latitude, longitude and
radius"; a CSV and four lines of Python can, and did, repeatedly --
`upswell-generic-geo.ipynb`, `curiouslearning-*-make-strata.ipynb`,
`mosul-rct-make-strata.ipynb` and about twenty others. Rejecting a server-side
"compile study" endpoint was precisely so that this kind of composition stays
possible; keeping the helper is the other half of that decision.

TWO DELIBERATE CHANGES FROM THE ORIGINAL
----------------------------------------

**The output is a variable LEVEL, not a `{"name", "params"}` pair.** The old
function emitted `params`, which only the old `configuration.format_group_product`
knew how to read. The compiler that replaced it,
`adopt.authoring.strata.create_strata_from_variables`, reads
`facebook_targeting` and `quota` -- the dashboard's level shape and the wire
shape of a `variables` conf. Emitting `params` here would have salvaged a
helper that composes with nothing. So the key is `facebook_targeting`, and the
result drops straight into `{"name": ..., "levels": [...]}`.

**`rows` is anything row-shaped**, not specifically `list(df.iterrows())`. The
original destructured `for _, r in rows`, which welded it to that one call. It
is the single thing notebook authors kept rewriting: three later notebooks ship
their own copy differing only in taking bare records. A DataFrame, an iterable
of Series, of `(index, Series)` pairs, of dicts, or of anything with `.lat` all
work here.

Nothing else changed. `location_types: ["home"]` is still forced, and the
`exclude` flag still writes `excluded_geo_locations` instead of
`geo_locations` -- "target this region, minus its cities" was a real pattern
and the two halves are composed by merging two levels' targeting, which is what
the strata compiler's shallow merge already does.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

__all__ = ["create_location", "location_levels", "GeoError"]

# Meta's targeting field names. Written as literals rather than imported from
# `facebook_business.adobjects` so that this module -- which a caller may want
# in a notebook or a validation step with no Meta SDK in the picture -- has no
# import cost and no version coupling. `test_geo.py` asserts each one equals the
# SDK constant it names, so the literals cannot drift from the enum silently.
GEO_LOCATIONS = "geo_locations"  # Targeting.Field.geo_locations
EXCLUDED_GEO_LOCATIONS = "excluded_geo_locations"  # Targeting.Field.excluded_geo_locations
LOCATION_TYPES = "location_types"  # TargetingGeoLocation.Field.location_types
CUSTOM_LOCATIONS = "custom_locations"  # TargetingGeoLocation.Field.custom_locations
LATITUDE = "latitude"  # TargetingGeoLocationCustomLocation.Field.latitude
LONGITUDE = "longitude"  # TargetingGeoLocationCustomLocation.Field.longitude
RADIUS = "radius"  # TargetingGeoLocationCustomLocation.Field.radius
DISTANCE_UNIT = "distance_unit"  # TargetingGeoLocationCustomLocation.Field.distance_unit

# "home" rather than Meta's default of "home,recent" -- a study stratified by
# where people LIVE must not recruit a traveller who happened to be in the
# radius last week, because their stratum assignment would then be wrong and
# the estimate is computed per stratum. Every notebook that used this passed
# it; it is forced here so that nobody can forget.
HOME = "home"

DEFAULT_DISTANCE_UNIT = "kilometer"


class GeoError(Exception):
    """A row that does not carry the three numbers a radius needs."""


def create_location(
    lat: float,
    lng: float,
    rad: float,
    distance_unit: str = DEFAULT_DISTANCE_UNIT,
) -> Dict[str, Any]:
    """One Meta custom location: a point and a radius around it.

    Public, unlike its ancestor -- fourteen notebooks defined a byte-identical
    private copy of this because it was not exported, which is about as clear a
    signal as a corpus gives. It is separately useful from `location_levels`
    whenever the surrounding envelope differs (a level built by hand, a
    `geo_locations` merged with `regions`).
    """
    return {
        LATITUDE: lat,
        LONGITUDE: lng,
        RADIUS: rad,
        DISTANCE_UNIT: distance_unit,
    }


def location_levels(
    name: str,
    rows: Any,
    exclude: bool = False,
    quota: Optional[float] = None,
    distance_unit: str = DEFAULT_DISTANCE_UNIT,
) -> Dict[str, Any]:
    """A variable level targeting (or excluding) every point in `rows`.

    :param name: the level's name. It becomes part of every stratum id built
        from this level, and stratum ids are Meta ad set names, so it is not
        cosmetic -- changing it later deletes an ad set and creates another.
    :param rows: anything row-shaped; see the module docstring. Each row needs
        a latitude, a longitude and a radius, read as `lat`/`lng`/`rad` and
        falling back to `latitude`/`longitude`/`radius`.
    :param exclude: write `excluded_geo_locations` rather than `geo_locations`.
    :param quota: the level's share of the sample. Optional because a caller
        that sets quotas from a share lookup (`authoring.sheets.read_share_lookup`)
        assigns them in a second pass; omit it and the key is absent rather
        than defaulted, so a level with no quota fails loudly at
        `create_strata_from_variables` instead of silently recruiting a zero
        share.

    An empty `rows` yields an empty `custom_locations` list rather than an
    error: "this region has no city overlaps" is a legitimate answer when the
    rows come from a groupby, and one notebook relied on exactly that
    (`cities_lookup.get(region, [])`). It is Meta that will reject the ad set,
    with a message about it, if that empty level is ever deployed.
    """
    locations = [
        create_location(*_lat_lng_rad(row), distance_unit=distance_unit)
        for row in _iter_rows(rows)
    ]

    key = EXCLUDED_GEO_LOCATIONS if exclude else GEO_LOCATIONS

    level: Dict[str, Any] = {
        "name": name,
        "facebook_targeting": {
            key: {
                LOCATION_TYPES: [HOME],
                CUSTOM_LOCATIONS: locations,
            }
        },
    }
    if quota is not None:
        level["quota"] = quota
    return level


# ---------------------------------------------------------------------------
# Reading a row, whatever a row turns out to be
# ---------------------------------------------------------------------------

_LAT = ("lat", "latitude")
_LNG = ("lng", "longitude", "lon", "long")
_RAD = ("rad", "radius")


def _iter_rows(rows: Any) -> Iterable[Any]:
    if rows is None:
        return []

    # A DataFrame, without importing pandas: `iterrows` is distinctive enough,
    # and this module has no other reason to depend on it.
    iterrows = getattr(rows, "iterrows", None)
    if callable(iterrows):
        return [row for _, row in iterrows()]

    out = []
    for row in rows:
        # `df.iterrows()` yields `(index, Series)`. Unwrapping it here is what
        # keeps every notebook's `list(df.iterrows())` working unchanged while
        # letting new callers pass the records directly. A 2-tuple whose second
        # element is itself row-shaped can only be that pairing: a row with two
        # fields would not answer to `lat`.
        if isinstance(row, tuple) and len(row) == 2 and _has_lat(row[1]):
            out.append(row[1])
        else:
            out.append(row)
    return out


def _has_lat(row: Any) -> bool:
    try:
        _get(row, _LAT)
    except GeoError:
        return False
    return True


def _lat_lng_rad(row: Any) -> Sequence[float]:
    return (_get(row, _LAT), _get(row, _LNG), _get(row, _RAD))


def _get(row: Any, names: Sequence[str]) -> Any:
    for name in names:
        # Subscript first: a pandas Series answers to both, and a dict only to
        # the first. Attribute access on a Series whose column collides with a
        # method name (`Series.count`, say) would silently return the method.
        if isinstance(row, Mapping) or hasattr(row, "__getitem__"):
            try:
                return row[name]
            except (KeyError, IndexError, TypeError):
                pass
        if hasattr(row, name):
            return getattr(row, name)
    raise GeoError(
        f"Row {row!r} has none of {list(names)}; a radius location needs a "
        "latitude, a longitude and a radius."
    )
