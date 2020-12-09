import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Union

import pandas as pd
import typing_json
from environs import Env
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.targeting import Targeting

from .audiences import hydrate_audiences
from .clustering import get_budget_lookup, shape_df
from .facebook.state import (BudgetWindow, CampaignState, StateNameError,
                             get_api)
from .facebook.update import GraphUpdater
# class Config(NamedTuple):
#     optimization_goal: str
#     destination_type: str
#     adset_hours: int
#     budget: float
#     min_budget: float
#     survey_user: str
#     opt_window: int
#     end_date: str
from .marketing import (AdoptConfig, AudienceConf, CreativeConf,
                        FacebookTargeting, Marketing, Stratum, StratumConf,
                        UserInfo, load_strata_conf, manage_audiences,
                        validate_targeting)
from .responses import get_ad_token, get_pageid, get_response_df

logging.basicConfig(level=logging.INFO)


def get_df(
    db_conf: Dict[str, str],
    survey_user: str,
    strata: List[Union[Stratum, AudienceConf]],
) -> pd.DataFrame:
    shortcodes = {shortcode for stratum in strata for shortcode in stratum.shortcodes}
    questions = {q.ref for stratum in strata for q in stratum.target_questions}
    survey_user = survey_user

    df = get_response_df(survey_user, shortcodes, questions, db_conf)

    if df is not None:
        return shape_df(df)
    return None


def get_confs(env):
    db_conf = {
        "db": env("CHATBASE_DATABASE"),
        "user": env("CHATBASE_USER"),
        "host": env("CHATBASE_HOST"),
        "port": env("CHATBASE_PORT"),
        "password": env("CHATBASE_PASSWORD", None),
    }

    c = {
        "optimization_goal": env("FACEBOOK_OPTIMIZATION_GOAL"),
        "destination_type": env("FACEBOOK_DESTINATION_TYPE"),
        "adset_hours": env.int("FACEBOOK_ADSET_HOURS"),
        "budget": env.float("MALARIA_BUDGET"),
        "min_budget": env.float("MALARIA_MIN_BUDGET"),
        "opt_window": env.int("MALARIA_OPT_WINDOW"),
        "end_date": env("MALARIA_END_DATE"),
        "ad_account": env("FACEBOOK_AD_ACCOUNT"),
        "ad_campaign": env("FACEBOOK_AD_CAMPAIGN"),
    }

    config = AdoptConfig(**c)

    survey_user = env("MALARIA_SURVEY_USER")
    pageid, instaid = get_pageid(survey_user, db_conf)

    c = {
        "survey_user": survey_user,
        "token": get_ad_token(survey_user, db_conf),
        "pageid": pageid,
        "instagramid": instaid,
    }

    userinfo = UserInfo(**c)

    return userinfo, config, db_conf


def window(hours=16):
    floor = lambda d: d.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = datetime.now() - timedelta(hours=hours)
    yesterday = floor(yesterday)
    today = datetime.now()
    return BudgetWindow(yesterday, today)


def days_left(config: AdoptConfig):
    dt = datetime.strptime(config.end_date, "%Y-%m-%d")
    td = dt - datetime.now()
    days = td.days
    return days


def get_cluster_from_adset(adset_name: str) -> str:
    pat = r"(?<=vlab-)\w+"
    matches = re.search(pat, adset_name)
    if not matches:
        raise Exception(f"Cannot extract cluster id from adset: {adset_name}")

    return matches[0]


def load_basics():
    env = Env()
    userinfo, config, db_conf = get_confs(env)

    w = window(hours=config.opt_window)

    state = CampaignState(
        userinfo.token,
        get_api(env, userinfo.token),
        config.ad_account,
        config.ad_campaign,
        w,
    )

    m = Marketing(state, userinfo, config)

    return userinfo, config, db_conf, state, m


def update_audience():
    userinfo, config, db_conf, state, m = load_basics()
    audience_confs = load_typed_json("config/audiences.json", List[AudienceConf])

    df = get_df(db_conf, userinfo.survey_user, audience_confs)

    audiences = hydrate_audiences(df, m, audience_confs)

    instructions = manage_audiences(state, audiences)

    updater = GraphUpdater(state)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def update_ads():
    userinfo, config, db_conf, state, m = load_basics()
    strata = load_stratum(state)

    df = get_df(db_conf, userinfo.survey_user, strata)

    spend = {get_cluster_from_adset(n): i for n, i in state.spend.items()}

    budget_lookup = get_budget_lookup(
        df,
        strata,
        config.budget,
        config.min_budget,
        state.window,
        spend,
        days_left=days_left(config),
    )

    instructions = m.update_instructions(strata, budget_lookup)

    updater = GraphUpdater(state)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def uniqueness(strata: List[StratumConf]):
    ids = [s.id for s in strata]
    if len(set(ids)) != len(ids):
        raise Exception("Strata IDs combinations are not unique")


T = TypeVar("T")


def load_typed_json(path: str, T) -> T:
    with open(path) as f:
        return typing_json.loads(f.read(), T)


def _add_aud(state, name) -> Optional[CustomAudience]:
    try:
        return {"id": state.get_audience(name).get_id()}
    except StateNameError:
        logging.info(
            f"Could not find audience: {name}. Omitting the audience from targeting"
        )
        return None


def add_audience_targeting(
    state: CampaignState, stratum: StratumConf
) -> FacebookTargeting:

    targeting = stratum.facebook_targeting

    targeting[Targeting.Field.custom_audiences] = [
        ca for s in stratum.audiences if (ca := _add_aud(state, s))
    ]
    targeting[Targeting.Field.excluded_custom_audiences] = [
        eca for s in stratum.excluded_audiences if (eca := _add_aud(state, s))
    ]

    return targeting


def hydrate_strata(
    state: CampaignState, strata: List[StratumConf], creatives: List[CreativeConf]
) -> List[Stratum]:

    # Validate strata
    uniqueness(strata)
    for s in strata:
        validate_targeting(s.facebook_targeting)

    creative_lookup = {c.name: c for c in creatives}

    strata_params: List[Dict[str, Any]] = [
        {
            **{
                k: v
                for k, v in s._asdict().items()
                if k not in {"audiences", "excluded_audiences"}
            },
            "creatives": [creative_lookup[c] for c in s.creatives],
            "facebook_targeting": add_audience_targeting(state, s),
        }
        for s in strata
    ]

    return [Stratum(**s) for s in strata_params]


def load_stratum(state: CampaignState) -> List[Stratum]:
    strata: List[StratumConf] = load_strata_conf("config/strata.json")
    creatives: List[CreativeConf] = load_typed_json(
        "config/creatives.json", List[CreativeConf]
    )
    return hydrate_strata(state, strata, creatives)
