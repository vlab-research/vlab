import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, TypeVar

import pandas as pd
import typing_json
from environs import Env

from .clustering import get_budget_lookup, shape_df
from .facebook.state import BudgetWindow, CampaignState
from .facebook.update import GraphUpdater
from .marketing import (CreativeConf, Marketing, Stratum, StratumConf,
                        load_strata_conf, validate_targeting)
from .responses import get_ad_token, get_response_df

logging.basicConfig(level=logging.INFO)


def get_df(cnf: Dict[str, Any], strata: List[Stratum]) -> pd.DataFrame:
    shortcodes = {shortcode for stratum in strata for shortcode in stratum.shortcodes}
    questions = {q.ref for stratum in strata for q in stratum.target_questions}
    survey_user = cnf["survey_user"]

    df = get_response_df(survey_user, shortcodes, questions, cnf["chatbase"])

    if df is not None:
        return df
        # return shape_df(df)
    return None


def get_conf(env):
    c = {
        "budget": env.float("MALARIA_BUDGET"),
        "min_budget": env.float("MALARIA_MIN_BUDGET"),
        "survey_user": env("MALARIA_SURVEY_USER"),
        "opt_window": env.int("MALARIA_OPT_WINDOW"),
        "end_date": env("MALARIA_END_DATE"),
        "chatbase": {
            "db": env("CHATBASE_DATABASE"),
            "user": env("CHATBASE_USER"),
            "host": env("CHATBASE_HOST"),
            "port": env("CHATBASE_PORT"),
            "password": env("CHATBASE_PASSWORD", None),
        },
    }

    return c


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


def run_update_ads(cnf, df, state, m, strata):
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

    instructions = [
        i for s in strata for i in m.adset_instructions(s, budget_lookup[s.id])
    ]

    updater = GraphUpdater(state)

    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def update_ads():
    env = Env()
    cnf = get_conf(env)
    df = get_df(cnf)

    w = window(hours=cnf["opt_window"])

    token = get_ad_token(cnf["survey_user"], cnf["chatbase"])
    state = CampaignState(env, token, w)

    m = Marketing(env, state)
    strata = load_stratum()

    run_update_ads(cnf, df, state, m, strata)


T = TypeVar("T")


def uniqueness(strata: List[StratumConf]):
    ids = [s.id for s in strata]
    if len(set(ids)) != len(ids):
        raise Exception("Strata IDs combinations are not unique")


def load_typed_json(path: str, T) -> T:
    with open(path) as f:
        return typing_json.loads(f.read(), T)


def hydrate_strata(
    strata: List[StratumConf], creatives: List[CreativeConf]
) -> List[Stratum]:

    # Validate strata
    uniqueness(strata)
    for s in strata:
        validate_targeting(s.facebook_targeting)

    creative_lookup = {c.name: c for c in creatives}

    strata_params: List[Dict[str, Any]] = [
        {
            **s._asdict(),
            "creatives": [creative_lookup[c] for c in s.creatives],
        }
        for s in strata
    ]

    return [Stratum(**s) for s in strata_params]


# transform StratumConf into Stratum
def load_stratum() -> List[Stratum]:
    strata: List[StratumConf] = load_strata_conf("config/strata.json")
    creatives: List[CreativeConf] = load_typed_json(
        "config/creatives.json", List[CreativeConf]
    )
    return hydrate_strata(strata, creatives)
