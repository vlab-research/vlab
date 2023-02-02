import json
import re
from typing import (List, NamedTuple, Optional, Tuple, Type, TypeVar,
                    get_type_hints)

import pandas as pd
from facebook_business.adobjects.targeting import Targeting
from facebook_business.adobjects.targetinggeolocation import \
    TargetingGeoLocation
from facebook_business.adobjects.targetinggeolocationcity import \
    TargetingGeoLocationCity
from facebook_business.adobjects.targetinggeolocationcustomlocation import \
    TargetingGeoLocationCustomLocation

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

        if source == "facebook":
            md_name = f"stratum_{name}"
            qt = {
                "op": "equal",
                "vars": [
                    {"type": "variable", "value": f"md:{md_name}"},
                    {"type": "constant", "value": c["name"]},
                ],
            }
            tvars.append(qt)

            md = {**md, md_name: c["name"]}

        if source == "survey":
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


def read_share_lookup(path, distribution_vars, tab_name):
    header = list(range(0, len(distribution_vars)))

    df = pd.read_excel(
        path,
        header=[0,1],
        index_col=0,
        sheet_name=tab_name,
    )

    df = df.dropna(axis=1)
    df.index.rename(distribution_vars[0], inplace=True)
    df = df.unstack()

    if isinstance(df.index, pd.MultiIndex):
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

    key = Targeting.Field.excluded_geo_locations if exclude is True else Targeting.Field.geo_locations

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
    }

    return Instruction("campaign", "create", params)
