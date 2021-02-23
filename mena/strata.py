import re
from itertools import product


def hyphen_case(s):
    return s.replace(" ", "-").lower().strip()


geo_pat = re.compile(r"GEO ?-?\s*(.+)")


def get_geo_name(g):
    try:
        return g["targeting"]["geo_locations"]["regions"][0]["name"]
    except KeyError:
        pass

    m = re.search(geo_pat, g["name"])
    if m is None:
        raise Exception(f"Couldnt make geo name from: {g['name']}")
    return m[1]


def conf_for_export(conf):
    conf["geo_locations"] = conf["geo_locations"].export_all_data()
    if conf.get("excluded_geo_locations"):
        conf["excluded_geo_locations"] = conf[
            "excluded_geo_locations"
        ].export_all_data()
    return conf


def format_group_product(group, share_lookup):
    conf = {
        k: v
        for keys, (name, conf) in group
        for k, v in conf["targeting"].items()
        if k in keys
    }

    keys = [n for _, (n, _) in group]
    age, gender, geo = keys
    share = share_lookup[gender][age][geo]
    name = "-".join([hyphen_case(k) for k in keys])

    return (name, share, conf_for_export(conf))


def get_groups(template_state, share_lookup):

    age_sets = [a for a in template_state.adsets if "Age" in a["name"]]
    geo_sets = [a for a in template_state.adsets if "GEO" in a["name"]]
    gender_sets = [a for a in template_state.adsets if "Gender" in a["name"]]

    geo_sets = [(get_geo_name(g), g) for g in geo_sets]

    age_sets = [(str(g["targeting"]["age_min"]), g) for g in age_sets]

    gender_sets = [(str(g["targeting"]["genders"][0]), g) for g in gender_sets]

    groups = [
        (["age_max", "age_min"], age_sets),
        (["genders"], gender_sets),
        (["excluded_geo_locations", "geo_locations"], geo_sets),
    ]

    groups = [[(keys, s) for s in sets] for keys, sets in groups]
    groups = list(product(*groups))
    groups = [format_group_product(g, share_lookup) for g in groups]

    return groups
