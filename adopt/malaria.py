import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, NamedTuple
import pandas as pd
import typing_json
from environs import Env
from facebook_business.adobjects.customaudience import CustomAudience
from .facebook.update import Instruction, GraphUpdater
from .facebook.state import CampaignState, BudgetWindow
from .clustering import (
    get_saturated_clusters,
    only_target_users,
    shape_df,
    get_budget_lookup,
)
from .responses import get_response_df
from .marketing import (
    Marketing,
    CreativeGroup,
    Location,
    Cluster,
    validate_targeting,
    create_custom_audience,
)

logging.basicConfig(level=logging.INFO)


def get_df(cnf):
    surveys = [survey for stratum in cnf["strata"] for survey in stratum["surveys"]]

    questions = {
        q["ref"]
        for s in surveys
        for q in s.get("target_questions", []) + s.get("exclude_questions", [])
    }

    questions |= {s["cluster_question"]["ref"] for s in surveys}

    survey_user = cnf["survey_user"]
    shortcodes = {s["shortcode"] for s in surveys}

    df = get_response_df(survey_user, shortcodes, questions, cnf["chatbase"])

    if df is not None:
        return shape_df(df)
    return None


def lookup_clusters(saturated, lookup_loc):
    lookup = pd.read_csv(lookup_loc)
    return [d for d in lookup.disthash.unique() if d not in saturated]


def unsaturated(df, cnf, stratum):
    if df is None:
        return lookup_clusters([], cnf["lookup_loc"])

    saturated = get_saturated_clusters(df, stratum)
    return lookup_clusters(saturated, cnf["lookup_loc"])


def lookalike(df, stratum):
    if df is None:
        return [], []

    target = only_target_users(df, stratum["surveys"], "target_questions")
    target_users = target.userid.unique()

    anti = only_target_users(df, stratum["surveys"], "exclude_questions")
    anti_users = anti.userid.unique()

    return target_users.tolist(), anti_users.tolist()


def opt(cnf, anti=False):
    # opt is used in tests and nothing else
    # pick first stratum
    stratum = cnf["strata"][0]

    df = get_df(cnf)
    clusters = unsaturated(df, cnf, stratum)
    users, antis = lookalike(df, stratum)
    if anti:
        return clusters, users, antis
    return clusters, users


def get_conf(env):
    c = {
        "country": env("MALARIA_COUNTRY"),
        "budget": env.float("MALARIA_BUDGET"),
        "min_budget": env.float("MALARIA_MIN_BUDGET"),
        "survey_user": env("MALARIA_SURVEY_USER"),
        "lookup_loc": env("MALARIA_DISTRICT_LOOKUP"),
        "opt_window": env.int("MALARIA_OPT_WINDOW"),
        "end_date": env("MALARIA_END_DATE"),
        "respondent_audience": env("MALARIA_RESPONDENT_AUDIENCE"),
        "n_clusters": env.int("MALARIA_NUM_CLUSTERS"),
        "chatbase": {
            "db": env("CHATBASE_DATABASE"),
            "user": env("CHATBASE_USER"),
            "host": env("CHATBASE_HOST"),
            "port": env("CHATBASE_PORT"),
            "password": env("CHATBASE_PASSWORD", None),
        },
    }

    with open("config/strata.json") as f:
        s = f.read()
        c["strata"] = json.loads(s)["strata"]

    return c


def load_creatives(path: str) -> Dict[str, CreativeGroup]:
    with open(path) as f:
        s = f.read()

    d = typing_json.loads(s, Dict[str, CreativeGroup])
    return d


def load_cities(path):
    cities = pd.read_csv(path)
    cities = cities[cities.rad >= 1.0]
    return cities


def uniqueness(clusters: List[Cluster]):
    ids = [cl.id for cl in clusters]
    if len(set(ids)) != len(ids):
        raise Exception("Cluster IDs combinations are not unique")


# StratumConf

# locs should be either Lat/Lng rad OR Facebook location
#

# should be


class ClusterConf(NamedTuple):
    cluster: Cluster
    cg: CreativeGroup
    locs: List[Location]
    include_audience: bool


def base_cluster_conf(cnf) -> List[ClusterConf]:

    # TODO: get this dynamically somehow
    cluster_vars = ["disthash", "distname", "creative_group", "include_audience"]
    cities = load_cities(cnf["lookup_loc"])

    creative_config = "config/creatives.json"
    cg_lookup = load_creatives(creative_config)

    locs = [
        ClusterConf(
            Cluster(i, n),
            cg_lookup[cg],
            [Location(r.lat, r.lng, r.rad) for _, r in df.iterrows()],
            bool(au),
        )
        # In principle all the groupby vars should be the same,
        # so grouping by clusterid, clustername, and creative group
        # should return the same groups!! Important data assumption!
        for (i, n, cg, au), df in cities.groupby(cluster_vars)
    ]

    return locs


def add_users(state: CampaignState, m: Marketing, name: str, users: List[str]):
    updater = GraphUpdater(state)
    aud = state.get_audience(name)
    logging.info(f'Adding {len(users)} users to audience {aud.get("name")}.')
    instructions = m.add_users(aud, users)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def create_respondent_audience(cnf, state: CampaignState):
    name = cnf["respondent_audience"]
    updater = GraphUpdater(state)
    i = create_custom_audience(name, "virtual lab auto-generated audience")
    report = updater.execute(i)
    logging.info(report)


def update_respondent_audience(cnf, df, m: Marketing):
    users = df.userid.unique().tolist()
    name = cnf["respondent_audience"]
    add_users(m.state, m, name, users)


def update_audience():
    env = Env()
    cnf = get_conf(env)
    state = CampaignState(env)
    m = Marketing(env, state)
    df = get_df(cnf)

    for stratum in cnf["strata"]:
        users, anti_users = lookalike(df, stratum)
        name = stratum["name"]
        for u, n in [(users, name), (anti_users, f"anti-{name}")]:
            add_users(state, m, n, u)


def window(hours=16):
    floor = lambda d: d.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = datetime.now() - timedelta(hours=hours)
    yesterday = floor(yesterday)
    today = datetime.now()
    return BudgetWindow(yesterday, today)


def days_left(cnf):
    dt = datetime.strptime(cnf["end_date"], "%Y-%m-%d")
    td = dt - datetime.now()
    days = td.days
    return days


def get_cluster_from_adset(adset_name: str) -> str:
    pat = r"(?<=vlab-)\w+"
    matches = re.search(pat, adset_name)
    if not matches:
        raise Exception(f"Cannot extract cluster id from adset: {adset_name}")

    return matches[0]


def new_ads(
    m: Marketing,
    cluster_confs: List[ClusterConf],
    stratum: Dict[str, Any],
    budget_lookup: Dict[str, int],
    saturated_clusters: List[str],
    aud: Optional[CustomAudience],
    anti_aud: Optional[CustomAudience],
) -> List[Instruction]:

    # check uniqueness of clusterids
    uniqueness([cl for cl, _, _, _ in cluster_confs])

    # validate targeting keys
    targeting = stratum.get("targeting")
    if targeting:
        validate_targeting(targeting)

    def adsetter(cl, cg, ls, au):

        # Get budget (0 will pause adset)
        bu = budget_lookup.get(cl.id, 0)
        if cl.id in saturated_clusters:
            bu = 0

        # create adset (with audience if aud is specified)
        if au:
            return m.adset_instructions(cl, cg, ls, bu, targeting, aud, anti_aud)
        return m.adset_instructions(cl, cg, ls, bu, targeting, None, anti_aud)

    instructions = [adsetter(*t) for t in cluster_confs]
    return [x for y in instructions for x in y]


def create_lookalike(cnf, m: Marketing):
    stratum = cnf["strata"][0]
    name = stratum["name"]
    i = m.create_lookalike(name, cnf["country"])
    updater = GraphUpdater(m.state)
    report = updater.execute(i)
    logging.info(report)


def run_update_ads(cnf, df, state, m):

    # check if campaign,
    # if not, make campaign and recurse

    # check if all adsets,
    # if not, make adsets and quit
    # come up with some way to allocate spend to adsets....

    # continue

    # TODO: How to support multiple strata???
    stratum = cnf["strata"][0]

    spend = {get_cluster_from_adset(n): i for n, i in state.spend.items()}

    budget_lookup = get_budget_lookup(
        df,
        stratum,
        cnf["budget"],
        cnf["min_budget"],
        cnf["n_clusters"],
        days_left(cnf),
        state.window,
        spend,
    )

    saturated = get_saturated_clusters(df, stratum)

    aud, anti_aud = m.get_lookalike(stratum["name"]), state.get_audience(
        cnf["respondent_audience"]
    )

    cluster_confs = base_cluster_conf(cnf)
    instructions = new_ads(
        m, cluster_confs, stratum, budget_lookup, saturated, aud, anti_aud
    )

    updater = GraphUpdater(state)

    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def update_ads():
    env = Env()
    cnf = get_conf(env)
    df = get_df(cnf)

    # make budget
    # TODO: this doesn't work from cold start
    # -- it should generally have some other way
    # of getting clusters, if no spend.
    w = window(hours=cnf["opt_window"])
    state = CampaignState(env, w)
    m = Marketing(env, state)

    run_update_ads(cnf, df, state, m)
