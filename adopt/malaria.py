import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Union

import pandas as pd
import typing_json
from environs import Env
from facebook_business.adobjects.targeting import Targeting
from toolz import groupby

from .audiences import hydrate_audiences
from .campaign_queries import (get_campaign_configs, get_campaigns,
                               get_user_info)
from .clustering import get_budget_lookup, shape_df
from .facebook.state import (BudgetWindow, CampaignState, StateNameError,
                             get_api)
from .facebook.update import GraphUpdater
from .marketing import (AudienceConf, CampaignConf, CreativeConf,
                        FacebookTargeting, Marketing, Stratum, StratumConf,
                        UserInfo, make_stratum_conf, manage_audiences,
                        validate_targeting)
from .responses import get_response_df

logging.basicConfig(level=logging.INFO)


def get_df(
    db_conf: Dict[str, str],
    survey_user: str,
    strata: List[Union[Stratum, AudienceConf]],
) -> pd.DataFrame:
    shortcodes = {shortcode for stratum in strata for shortcode in stratum.shortcodes}
    questions = {q.ref for stratum in strata for q in stratum.target_questions}

    df = get_response_df(survey_user, shortcodes, questions, db_conf)

    if df is not None:
        return shape_df(df)
    return None


def get_confs_for_campaign(campaignid, db_conf):
    parsers = {
        "stratum": make_stratum_conf,
        "audience": lambda x: loads_typed_json(x, AudienceConf),
        "creative": lambda x: loads_typed_json(x, CreativeConf),
        "opt": lambda x: loads_typed_json(x, CampaignConf),
    }

    confs = get_campaign_configs(campaignid, db_conf)
    confs = groupby(
        lambda x: x[0],
        [(c["conf_type"], parsers[c["conf_type"]](c["conf"])) for c in confs],
    )
    return {k: [vv for _, vv in v] for k, v in confs.items()}


def get_db_conf(env: Env):
    return {
        "db": env("CHATBASE_DATABASE"),
        "user": env("CHATBASE_USER"),
        "host": env("CHATBASE_HOST"),
        "port": env("CHATBASE_PORT"),
        "password": env("CHATBASE_PASSWORD", None),
    }


def get_confs(campaignid: str, env: Env):
    db_conf = get_db_conf(env)
    userinfo = UserInfo(**get_user_info(campaignid, db_conf))
    confs = get_confs_for_campaign(campaignid, db_conf)
    config = confs["opt"][0]

    return userinfo, config, db_conf, confs


def window(hours=16):
    floor = lambda d: d.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = datetime.now() - timedelta(hours=hours)
    yesterday = floor(yesterday)
    today = datetime.now()
    return BudgetWindow(yesterday, today)


def days_left(config: CampaignConf):
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


def load_basics(campaignid, env):
    userinfo, config, db_conf, confs = get_confs(campaignid, env)

    w = window(hours=config.opt_window)

    state = CampaignState(
        userinfo.token,
        get_api(env, userinfo.token),
        config.ad_account,
        config.ad_campaign,
        w,
    )

    m = Marketing(state, userinfo, config)

    return userinfo, config, db_conf, state, m, confs


def update_ads_for_campaign(campaignid, env):
    userinfo, config, db_conf, state, m, confs = load_basics(campaignid, env)
    strata = hydrate_strata(state, confs["stratum"], confs["creative"])

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


def update_audience_for_campaign(campaignid, env):
    userinfo, config, db_conf, state, m, confs = load_basics(campaignid, env)
    audience_confs = confs["audience"]

    df = get_df(db_conf, userinfo.survey_user, audience_confs)

    audiences = hydrate_audiences(df, m, audience_confs)

    instructions = manage_audiences(state, audiences)

    updater = GraphUpdater(state)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def run_updates(fn):
    env = Env()
    db_conf = get_db_conf(env)
    campaigns = get_campaigns(db_conf)

    for c in campaigns:
        fn(c, env)


def update_audience():
    run_updates(update_audience_for_campaign)


def update_ads():
    run_updates(update_ads_for_campaign)


def uniqueness(strata: List[StratumConf]):
    ids = [s.id for s in strata]
    if len(set(ids)) != len(ids):
        raise Exception("Strata IDs combinations are not unique")


T = TypeVar("T")


def load_typed_json(path: str, T) -> T:
    with open(path) as f:
        return typing_json.loads(f.read(), T)


def loads_typed_json(d: Dict[Any, Any], T) -> T:
    return typing_json.loads(json.dumps(d), T)


def _add_aud(state, name) -> Optional[Dict[str, Any]]:
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
