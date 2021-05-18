import re
from itertools import product

import pandas as pd

from adopt.marketing import CreativeConf


def hyphen_case(s):
    return s.replace(" ", "-").lower().strip()


geo_pat = re.compile(r"GEO\s*-?\s*(.+)")


def get_geo_name(g):
    m = re.search(geo_pat, g["name"])
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


def format_group_product(group, share_lookup):
    facebook_targeting = {}
    tvars = []
    md = {}
    conf = {"audiences": [], "excluded_audiences": []}

    id_list = []
    names = []

    for name, source, c in group:
        id_list += [name, c["name"]]
        names += [c["name"]]

        if source == "facebook":
            md_name = f"stratum_{name}"
            facebook_targeting = {**facebook_targeting, **c["params"]}
            qt = {
                "op": "equal",
                "vars": [
                    {"type": "response", "value": f"md:{md_name}"},
                    {"type": "constant", "value": c["name"]},
                ],
            }
            tvars.append(qt)

            md = {**md, md_name: c["name"]}

        if source == "survey":
            tvars.append(c["question_targeting"])
            conf["audiences"] += c["audiences"]
            conf["excluded_audiences"] += c["excluded_audiences"]

    # TODO: ADD FINISHED_QUESTION_REF SOMEWHERE IN CONFIGURATION!!!

    conf = {
        "facebook_targeting": facebook_targeting,
        "question_targeting": {"op": "and", "vars": tvars},
        "metadata": md,
        **conf,
    }

    variables = [name for name, _, _ in group]
    try:
        share = (
            share_lookup[variables + ["percentage"]]
            .set_index(variables)
            .loc[tuple(names)][0]
        )
    except KeyError as e:
        raise Exception(f"Could not find share for stratum: {names}") from e

    id_ = "-".join([hyphen_case(s) for s in id_list])

    return id_, share, conf


def _creative_conf(name, image, body, headline, welcome_message, button_text, form):
    return {
        "name": name,
        "image": image["name"],
        "image_hash": image["hash"],
        "body": body,
        "link_text": headline,
        "welcome_message": welcome_message,
        "button_text": button_text,
        "form": form,
    }


def generate_creative_confs(path, initial_shortcode, images):
    df = pd.read_csv(path)
    image_confs = [
        {**d, "image": images[d["image"]]} for d in df.to_dict(orient="records")
    ]
    creatives = [
        CreativeConf(**_creative_conf(**{**c, "form": initial_shortcode}))
        for c in image_confs
    ]
    confs = [c._asdict() for c in creatives]
    return confs, image_confs


def read_general_conf(path):
    return {
        k: v["value"]
        for k, v in pd.read_csv(path, index_col=[0]).to_dict(orient="index").items()
    }


def parse_conf_list(s):
    return [w.strip() for w in s.split(",")]
