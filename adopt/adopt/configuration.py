"""SUPERSEDED — the notebook-era study configuration helpers.

This module predates the dashboard. It built a study from an Excel workbook
(`parse_kv_sheet`, `parse_row_sheet`, `read_share_lookup`) and derived strata
with its own `format_group_product`, which does NOT agree with what the
dashboard produces and what production studies are built with:

  * metadata keys are `stratum_<var>`, the dashboard's are `<var>`;
  * question-targeting variable refs are `md:stratum_<var>`, the dashboard's
    are the bare variable name;
  * stratum ids are hyphen-joined `var-level-var-level`, the dashboard's are
    `var:level,var:level`;
  * quotas come from an Excel share lookup, the dashboard's are the product of
    the level quotas.

The dashboard's derivation is now ported, with a conformance suite against the
TypeScript, in `adopt.authoring` (`strata.py`, `extract.py`). Use that. Do not
use `format_group_product` here to build strata for a study the dashboard will
also touch — the two will disagree and the dashboard's staleness banner will
flag every stratum.

THE SALVAGE HAPPENED. THE PIECES WORTH KEEPING NOW LIVE IN `adopt.authoring`:

  * `read_share_lookup`, `parse_kv_sheet`, `parse_row_sheet`
        -> `adopt.authoring.sheets`
  * `location_levels`, `create_location`  (create_location is now PUBLIC)
        -> `adopt.authoring.geo`

Use those. They were moved during Phase 3 (the SDK), which is what §10 and
§12.4 of `planning/agent-study-authoring.md` said would give them a consumer to
shape their API around, and both changed slightly in the move — `location_levels`
emits `facebook_targeting` rather than `params`, so it composes with
`adopt.authoring.strata.create_strata_from_variables`, and it takes any
row-shaped input rather than specifically `list(df.iterrows())`. `planning/vlab-sdk.md`
records what was salvaged, what was dropped and why.

What was deliberately NOT salvaged, and stays here only so the ~46 notebooks in
`~/Documents/vlab-research/campaigns/` that import this module keep working:

  * `format_group_product` — superseded by `adopt.authoring.strata`, with the
    four disagreements listed above.
  * `get_adsets`, `_get_adsets`, `get_relevant_part`, `fb_property_lookup`,
    `get_geo_name`, `make_variable_extraction`, `extraction_confs` — the
    "scrape targeting out of a hand-built template campaign" workflow, replaced
    by `GET /{org}/meta/adsets` plus `adopt.authoring.extract.extract_from_adset`.
  * `create_campaign` — a stale duplicate of `marketing.create_campaign`, and
    broken besides: it references `Instruction`, which this module never
    imports, so calling it is a `NameError`.
  * `TargetingConf`, `respondent_audience_name`, `hyphen_case`,
    `conf_for_export`, `_creative_conf`, `stringify_column`, `origin_of` —
    notebook-era conventions, or helpers with no caller.

Nothing in production imports this module; its only importers are
`test_configuration.py` (the `read_share_lookup` Excel tests, which still pass
and still guard this copy of that reader — `authoring/test_sheets.py` has the
same five against the new home) and `test_studies.py` (whose uses are
commented out).
"""

import json
import re
from typing import List, NamedTuple, Optional, Tuple, Type, TypeVar, get_type_hints

import pandas as pd
from facebook_business.adobjects.targeting import Targeting
from facebook_business.adobjects.targetinggeolocation import TargetingGeoLocation
from facebook_business.adobjects.targetinggeolocationcity import (
    TargetingGeoLocationCity,
)
from facebook_business.adobjects.targetinggeolocationcustomlocation import (
    TargetingGeoLocationCustomLocation,
)

from .study_conf import CreativeConf, GeneralConf


class TargetingConf(NamedTuple):
    template_campaign_name: Optional[str]
    distribution_vars: list[str]


def origin_of(type_: Type) -> Optional[Type]:
    origin = getattr(type_, "__origin__", None)

    # In Python 3.6, the origin of Tuple type is `List` but in Python 3.7 it is `list`.
    if origin is List:
        return list
    # In Python 3.6, the origin of Tuple type is `Tuple` but in Python 3.7 it is `tuple`.
    elif origin is Tuple:
        return tuple
    else:
        return origin  # type: ignore


def hyphen_case(s):
    try:
        return s.replace(" ", "-").lower().strip()
    except AttributeError:
        return str(s)


def make_variable_extraction(name):
    return re.compile(rf"{name}\s*-?\s*(.+)")


# TRIM from variable extraction


def get_geo_name(g):
    m = re.search(make_variable_extraction("GEO"), g["name"])
    if m is not None:
        return m[1]

    try:
        return g["targeting"]["geo_locations"]["regions"][0]["name"]
    except KeyError:
        raise Exception(f"Couldnt make geo name from: {g['name']}")


def conf_for_export(conf):
    conf["geo_locations"] = conf["geo_locations"].export_all_data()
    if conf.get("excluded_geo_locations"):
        conf["excluded_geo_locations"] = conf[
            "excluded_geo_locations"
        ].export_all_data()
    return conf


fb_property_lookup = {
    "age": ["age_max", "age_min"],
    "gender": ["genders"],
    "location": ["excluded_geo_locations", "geo_locations"],
    "education": ["flexible_spec", "exclusions"],
}


def get_relevant_part(keys, adset_conf):
    conf = {k: v for k, v in adset_conf["targeting"].items() if k in keys}

    return conf


extraction_confs = [
    ("age", "Age", lambda g: str(g["targeting"]["age_min"])),
    ("gender", "Gender", lambda g: str(g["targeting"]["genders"][0])),
    ("location", "GEO", get_geo_name),
]


def _get_adsets(template_state, name, pattern, fn):
    sets = [(fn(a), a) for a in template_state.adsets if pattern in a["name"]]
    sets = [(n, get_relevant_part(fb_property_lookup[name], a)) for n, a in sets]
    return [{"name": n, "params": c} for n, c in sets]


def get_adsets(template_state, confs):
    return [{"levels": _get_adsets(template_state, *c)} for c in confs]


def format_group_product(group, share_lookup, base_targeting, finish_filter=None):
    facebook_targeting = base_targeting.copy()
    tvars = []
    md = {}
    conf = {"audiences": [], "excluded_audiences": []}

    id_list = []
    names = []

    for name, source, c in group:
        id_list += [name, c["name"]]
        names += [c["name"]]

        if "params" in c:
            facebook_targeting = {**facebook_targeting, **c["params"]}

        if "facebook" in source:
            md_name = f"stratum_{name}"
            md = {**md, md_name: c["name"]}

            if source == "facebook":
                qt = {
                    "op": "equal",
                    "vars": [
                        {"type": "variable", "value": f"md:{md_name}"},
                        {"type": "constant", "value": c["name"]},
                    ],
                }
                tvars.append(qt)

        if "survey" in source:
            tvars.append(c["question_targeting"])
            conf["audiences"] += c.get("audiences", [])
            conf["excluded_audiences"] += c.get("excluded_audiences", [])

    if finish_filter:
        tvars.append(finish_filter)

    conf = {
        "facebook_targeting": facebook_targeting,
        "question_targeting": {"op": "and", "vars": tvars},
        "metadata": md,
        **conf,
    }

    variables = [name for name, _, _ in group]
    try:
        share = share_lookup.set_index(variables).loc[tuple(names)][0]

    except KeyError as e:
        raise Exception(f"Could not find share for stratum: {names}") from e

    id_ = "-".join([hyphen_case(s) for s in id_list])

    return id_, share, conf


def _creative_conf(c):
    return {
        "name": c["name"],
        "image_hash": c["image_hash"],
        "body": c["body"],
        "link_text": c["headline"],
        "welcome_message": c["welcome_message"],
        "button_text": c["button_text"],
        "tags": c["tags"],
    }


def stringify_column(col):
    if isinstance(col, tuple):
        return tuple([str(i) for i in col])
    return str(col)


def read_single_value_share_lookup(path, var_name, tab_name):
    df = pd.read_excel(
        path,
        sheet_name=tab_name,
    )
    df = df.dropna(axis=1)
    df.columns = [var_name, "percentage"]

    return df


def read_share_lookup(path, distribution_vars, tab_name):
    if len(distribution_vars) == 1:
        return read_single_value_share_lookup(path, distribution_vars[0], tab_name)

    # 2 levels needs some level dropping. Who knows why.
    if len(distribution_vars) == 2:
        df = pd.read_excel(
            path,
            header=[0, 1],
            index_col=0,
            sheet_name=tab_name,
        )
        df = df.dropna(axis=1)
        df.columns = df.columns.droplevel(1)

    # should handle many levels
    header = list(range(0, len(distribution_vars) - 1))

    if len(distribution_vars) > 2:
        df = pd.read_excel(
            path,
            header=header,
            index_col=0,
            sheet_name=tab_name,
        )
        df = df.dropna(axis=1)

    # Crazy pandas magic. Probably worth redoing from scratch
    df.index.rename(distribution_vars[0], inplace=True)
    df = df.unstack()
    df.index = df.index.reorder_levels(distribution_vars)
    stringified_vals = [tuple([str(v) for v in t]) for t in df.index]
    df.index = pd.MultiIndex.from_tuples(stringified_vals, names=df.index.names)

    return df.reset_index(name="percentage")


def cast_strings(type_, dict_):
    res = dict_.copy()

    hints = get_type_hints(type_)
    for k, v in dict_.items():
        # quick hack to allow for Optional...
        if pd.isna(v):
            res[k] = None
            continue

        t = hints[k]

        if isinstance(v, str):
            if origin_of(t) == list:
                res[k] = [x.strip() for x in v.split(",")]

            if origin_of(t) == dict:
                res[k] = json.loads(v)
                continue

            if t not in (int, float, str, bool):
                continue

            res[k] = t(v)

    return res


def parse_kv_sheet(path, sheet_name, type_):
    df = pd.read_excel(path, sheet_name=sheet_name, index_col=[0])
    x = {k: v["value"] for k, v in df.to_dict(orient="index").items()}

    x = cast_strings(type_, x)
    d = type_(**x)
    return d


T = TypeVar("T")


def parse_row_sheet(path, sheet_name, type_: T) -> list[T]:
    df = pd.read_excel(path, sheet_name=sheet_name)
    rows = df.to_dict(orient="records")
    rows = [cast_strings(type_, x) for x in rows]
    rows = [type_(**x) for x in rows]
    return rows


def respondent_audience_name(config: GeneralConf) -> str:
    return f"{config.name}-respondents"


def create_location(lat, lng, rad):
    return {
        TargetingGeoLocationCustomLocation.Field.latitude: lat,
        TargetingGeoLocationCustomLocation.Field.longitude: lng,
        TargetingGeoLocationCustomLocation.Field.radius: rad,
        TargetingGeoLocationCustomLocation.Field.distance_unit: "kilometer",
    }


def location_levels(name, rows, exclude=False):
    locs = [create_location(r.lat, r.lng, r.rad) for _, r in rows]

    key = (
        Targeting.Field.excluded_geo_locations
        if exclude is True
        else Targeting.Field.geo_locations
    )

    params = {
        key: {
            TargetingGeoLocation.Field.location_types: ["home"],
            TargetingGeoLocation.Field.custom_locations: locs,
        }
    }

    return {"name": name, "params": params}


def create_campaign(name):
    params = {
        "name": name,
        "objective": "MESSAGES",
        "status": "PAUSED",
        "special_ad_categories": [],
        "is_adset_budget_sharing_enabled": False,
    }

    return Instruction("campaign", "create", params)
