"""Tests for `authoring/geo.py`, the salvaged radius-targeting helper.

Two things are being asserted, and they are different in kind:

1. That the output composes with `create_strata_from_variables`. That is the
   whole reason the salvage changed `params` to `facebook_targeting`, so it is
   tested end to end rather than by inspecting a key.
2. That every row shape the notebook corpus actually passed still works --
   `list(df.iterrows())` above all, since twenty notebooks pass exactly that.
"""

import pandas as pd
import pytest
from facebook_business.adobjects.targeting import Targeting
from facebook_business.adobjects.targetinggeolocation import TargetingGeoLocation
from facebook_business.adobjects.targetinggeolocationcustomlocation import (
    TargetingGeoLocationCustomLocation,
)

from .geo import (
    CUSTOM_LOCATIONS,
    DISTANCE_UNIT,
    EXCLUDED_GEO_LOCATIONS,
    GEO_LOCATIONS,
    LATITUDE,
    LOCATION_TYPES,
    LONGITUDE,
    RADIUS,
    GeoError,
    create_location,
    location_levels,
)
from .strata import create_strata_from_variables

TOWNS = pd.DataFrame(
    [
        {"name": "Aba", "state": "Abia", "lat": 5.11, "lng": 7.36, "rad": 4.0},
        {"name": "Umuahia", "state": "Abia", "lat": 5.52, "lng": 7.49, "rad": 3.0},
    ]
)


# ---------------------------------------------------------------------------
# The field names are Meta's, and stay Meta's
# ---------------------------------------------------------------------------


def test_the_literal_field_names_equal_the_facebook_sdk_constants():
    """The module uses literals so it need not import the Meta SDK; this is
    what makes that safe rather than a guess that happens to hold today."""
    assert GEO_LOCATIONS == Targeting.Field.geo_locations
    assert EXCLUDED_GEO_LOCATIONS == Targeting.Field.excluded_geo_locations
    assert LOCATION_TYPES == TargetingGeoLocation.Field.location_types
    assert CUSTOM_LOCATIONS == TargetingGeoLocation.Field.custom_locations
    assert LATITUDE == TargetingGeoLocationCustomLocation.Field.latitude
    assert LONGITUDE == TargetingGeoLocationCustomLocation.Field.longitude
    assert RADIUS == TargetingGeoLocationCustomLocation.Field.radius
    assert DISTANCE_UNIT == TargetingGeoLocationCustomLocation.Field.distance_unit


# ---------------------------------------------------------------------------
# create_location
# ---------------------------------------------------------------------------


def test_create_location_is_the_four_keys_meta_wants():
    assert create_location(5.11, 7.36, 4.0) == {
        "latitude": 5.11,
        "longitude": 7.36,
        "radius": 4.0,
        "distance_unit": "kilometer",
    }


def test_create_location_takes_another_unit():
    assert create_location(1, 2, 3, distance_unit="mile")["distance_unit"] == "mile"


# ---------------------------------------------------------------------------
# Row shapes
# ---------------------------------------------------------------------------


def test_a_list_of_iterrows_pairs_works():
    """The shape twenty notebooks pass: `list(df.iterrows())`."""
    level = location_levels("Abia", list(TOWNS.iterrows()))
    locs = level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS]
    assert [loc["latitude"] for loc in locs] == [5.11, 5.52]


def test_a_dataframe_works_directly():
    """The change from the original. `df.iterrows()` is no longer required."""
    level = location_levels("Abia", TOWNS)
    locs = level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS]
    assert [loc["longitude"] for loc in locs] == [7.36, 7.49]


def test_bare_series_work():
    """What the three later notebooks that rewrote this function passed."""
    rows = [row for _, row in TOWNS.iterrows()]
    level = location_levels("Abia", rows)
    assert len(level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS]) == 2


def test_dicts_work():
    level = location_levels("here", [{"lat": 1.0, "lng": 2.0, "rad": 3.0}])
    assert level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS] == [
        {"latitude": 1.0, "longitude": 2.0, "radius": 3.0, "distance_unit": "kilometer"}
    ]


def test_the_long_spellings_work():
    """`reno-weber-2023-geotargeting.ipynb` had a `radius` column, not `rad`."""
    level = location_levels(
        "here", [{"latitude": 1.0, "longitude": 2.0, "radius": 3.0}]
    )
    assert level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS][0][
        "radius"
    ] == 3.0


def test_a_row_with_no_coordinates_says_so():
    with pytest.raises(GeoError) as e:
        location_levels("here", [{"town": "Aba"}])
    assert "lat" in str(e.value)


# ---------------------------------------------------------------------------
# The level itself
# ---------------------------------------------------------------------------


def test_location_types_is_forced_to_home():
    """Not Meta's default of home+recent: a stratum is where people live."""
    level = location_levels("Abia", TOWNS)
    assert level["facebook_targeting"][GEO_LOCATIONS][LOCATION_TYPES] == ["home"]


def test_exclude_writes_the_excluded_key():
    level = location_levels("Abia", TOWNS, exclude=True)
    assert EXCLUDED_GEO_LOCATIONS in level["facebook_targeting"]
    assert GEO_LOCATIONS not in level["facebook_targeting"]


def test_quota_is_absent_unless_given():
    """Absent, not defaulted: a level with no quota must fail loudly at the
    compiler rather than silently recruiting a zero share."""
    assert "quota" not in location_levels("Abia", TOWNS)
    assert location_levels("Abia", TOWNS, quota=0.25)["quota"] == 0.25


def test_no_rows_is_an_empty_level_not_an_error():
    """`cities_lookup.get(region, [])` in curiouslearning-multicountry-pilot-3."""
    level = location_levels("nowhere", [])
    assert level["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS] == []


def test_none_rows_is_also_empty():
    assert (
        location_levels("nowhere", None)["facebook_targeting"][GEO_LOCATIONS][
            CUSTOM_LOCATIONS
        ]
        == []
    )


# ---------------------------------------------------------------------------
# The point of the salvage: it composes with the compiler
# ---------------------------------------------------------------------------


def test_a_geo_level_drops_straight_into_the_strata_compiler():
    """The reason `params` became `facebook_targeting`.

    A `variables` conf built out of `location_levels` is compiled by exactly
    the same function the dashboard's Regenerate button calls, and the
    resulting stratum carries the radius targeting.
    """
    variables = [
        {
            "name": "location",
            "properties": ["geo_locations"],
            "levels": [
                location_levels(state, group, quota=0.5)
                for state, group in TOWNS.groupby("state")
            ],
        }
    ]

    strata = create_strata_from_variables(variables, "finished")

    assert len(strata) == 1
    stratum = strata[0]
    assert stratum["id"] == "location:Abia"
    assert stratum["quota"] == 0.5
    assert stratum["metadata"] == {"location": "Abia"}
    locs = stratum["facebook_targeting"][GEO_LOCATIONS][CUSTOM_LOCATIONS]
    assert len(locs) == 2


def test_targeting_a_region_minus_its_cities_composes_by_merging_two_levels():
    """The `exclude=True` pattern, which was three notebooks' whole reason for
    the flag: the compiler's shallow merge puts both keys on one stratum."""
    variables = [
        {
            "name": "region",
            "properties": ["geo_locations", "excluded_geo_locations"],
            "levels": [
                {
                    **location_levels("Abia", TOWNS, exclude=True),
                    "quota": 1.0,
                    "facebook_targeting": {
                        **location_levels("Abia", TOWNS, exclude=True)[
                            "facebook_targeting"
                        ],
                        GEO_LOCATIONS: {"regions": [{"key": "123"}]},
                    },
                }
            ],
        }
    ]

    stratum = create_strata_from_variables(variables, "finished")[0]
    targeting = stratum["facebook_targeting"]
    assert targeting[GEO_LOCATIONS] == {"regions": [{"key": "123"}]}
    assert len(targeting[EXCLUDED_GEO_LOCATIONS][CUSTOM_LOCATIONS]) == 2
