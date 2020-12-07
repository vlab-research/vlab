import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import typing_json
from environs import Env

from .clustering import (get_budget_lookup, get_saturated_clusters,
                         only_target_users, shape_df)
from .facebook.state import BudgetWindow, CampaignState
from .facebook.update import GraphUpdater
from .marketing import (Cluster, CreativeGroup, Marketing, Stratum,
                        StratumConf, validate_targeting)
from .responses import get_response_df

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


def run_update_ads(cnf, df, state, m):

    # check if campaign,
    # if not, make campaign and recurse

    # check if all adsets,
    # if not, make adsets and quit
    # come up with some way to allocate spend to adsets....

    # continue

    strata = cnf["strata"]

    # load stratum from stratumconf

    spend = {get_cluster_from_adset(n): i for n, i in state.spend.items()}

    budget_lookup = get_budget_lookup(
        df,
        strata,
        cnf["budget"],
        cnf["min_budget"],
        state.window,
        spend,
        days_left=days_left(cnf),
    )

    instructions = [m.adset_instructions(s, budget_lookup[s.id]) for s in strata]
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


###
# layered creation
# 1. create campaign
# 2. create audiences
# 3. create lookalike audiences


# except StateNameError:
# create_audience(updater, aud)


def uniqueness(clusters: List[Cluster]):
    ids = [cl.id for cl in clusters]
    if len(set(ids)) != len(ids):
        raise Exception("Cluster IDs combinations are not unique")


## transform StratumConf into Stratum
def load_stratum(strata: List[StratumConf]) -> List[Stratum]:
    cg_lookup = load_creatives("config/creatives.json")

    # check uniqueness

    for s in strata:
        validate_targeting(s.facebook_targeting)

    creative_groups = [cg_lookup[s.creative_group] for s in strata]
    # 1. get CustomAudiences for audiences
