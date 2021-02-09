import json
import logging
import re
from datetime import datetime, timedelta
from typing import (Any, Callable, Dict, List, NamedTuple, Optional, Sequence,
                    Tuple, TypeVar, Union)

import pandas as pd
import typing_json
from environs import Env
from facebook_business.adobjects.targeting import Targeting
from toolz import groupby

from .audiences import hydrate_audiences
from .campaign_queries import (create_adopt_report, get_campaign_configs,
                               get_campaigns, get_user_info)
from .clustering import AdOptReport, get_budget_lookup, shape_df
from .facebook.state import (BudgetWindow, CampaignState, StateNameError,
                             get_api)
from .facebook.update import GraphUpdater, Instruction
from .marketing import (AudienceConf, CampaignConf, CreativeConf,
                        FacebookTargeting, Marketing, QuestionTargeting,
                        Stratum, StratumConf, TargetVar, UserInfo,
                        make_audience_conf, make_stratum_conf,
                        manage_audiences, validate_targeting)
from .responses import get_response_df

logging.basicConfig(level=logging.INFO)


def _get_ref(v: Union[TargetVar, QuestionTargeting]) -> Sequence[Optional[str]]:
    if isinstance(v, QuestionTargeting):
        return get_target_questions(v)

    if v.type in {"response", "translated_response"}:
        return [v.value]

    return [None]


def get_target_questions(qt: Optional[QuestionTargeting]) -> Sequence[str]:
    if qt is None:
        return []

    refs = [r for v in qt.vars for r in _get_ref(v)]
    return [r for r in refs if r is not None]


def get_df(
    db_conf: Dict[str, str],
    survey_user: str,
    strata: Sequence[Union[Stratum, AudienceConf]],
) -> Optional[pd.DataFrame]:

    # This makes no sense for AudienceConf, or at least a seq of them,
    # becase the questions in one sholdn't exclude the aud from another

    # Is this the case with strata as well if you have target_questions
    # that are different?? Yes, but usually they should be the same
    # for all strata. But then the code you have here is confusing
    # because it gets the union of all qs...

    # I mean, the query is question_ref is in %s, so it's only
    # problematic for when there is NO question wanted (any respondent)
    # that's the real problem

    # TODO - look at tests, what is the desired behavior for audiences/stratum
    # with no target_questions???? it shouldn't work at all...

    # TODO - for audience you should actually have a query that gets responses
    # who are only to the correct pageid! Because now each surveyuser can have
    # multiple pages, but that won't work for audiences with page scoped ids!

    shortcodes = {shortcode for stratum in strata for shortcode in stratum.shortcodes}
    questions = {
        q
        for stratum in strata
        for q in get_target_questions(stratum.question_targeting)
    }

    df = get_response_df(survey_user, shortcodes, questions, db_conf)

    if df is not None:
        return shape_df(df)
    return None


def get_confs_for_campaign(campaignid, db_conf):
    parsers = {
        "stratum": make_stratum_conf,
        "audience": make_audience_conf,
        "creative": lambda x: loads_typed_json(x, CreativeConf),
        "opt": lambda x: loads_typed_json(x, CampaignConf),
    }

    confs = get_campaign_configs(campaignid, db_conf)
    confs = groupby(
        lambda x: x[0],
        [
            (c["conf_type"], parsers[c["conf_type"]](conf))
            for c in confs
            for conf in c["conf"]
        ],
    )
    return {k: [vv for _, vv in v] for k, v in confs.items()}


DBConf = Dict[str, str]


class Malaria(NamedTuple):
    userinfo: UserInfo
    config: CampaignConf
    db_conf: DBConf
    state: CampaignState
    m: Marketing
    confs: Dict[str, Any]


def get_db_conf(env: Env) -> DBConf:
    return {
        "db": env("CHATBASE_DATABASE"),
        "user": env("CHATBASE_USER"),
        "host": env("CHATBASE_HOST"),
        "port": env("CHATBASE_PORT"),
        "password": env("CHATBASE_PASSWORD", None),
    }


def get_confs(
    campaignid: str, env: Env
) -> Tuple[UserInfo, CampaignConf, DBConf, Dict[str, Any]]:
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
    if not config.end_date:
        return None

    dt = datetime.strptime(config.end_date, "%Y-%m-%d")
    td = dt - datetime.now()
    days = td.days
    return days


def get_cluster_from_adset(adset_name: str) -> str:
    pat = r"(?<=vlab-).+"
    matches = re.search(pat, adset_name)
    if not matches:
        raise Exception(f"Cannot extract cluster id from adset: {adset_name}")

    return matches[0]


def load_basics(campaignid: str, env: Env) -> Malaria:
    userinfo, config, db_conf, confs = get_confs(campaignid, env)

    w = window(hours=config.opt_window)

    state = CampaignState(
        userinfo.token,
        get_api(env, userinfo.token),
        config.ad_account,
        config.ad_campaign,
        w,
    )

    m = Marketing(state, config)

    return Malaria(userinfo, config, db_conf, state, m, confs)


def run_instructions(instructions: Sequence[Instruction], state: CampaignState):
    updater = GraphUpdater(state)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def update_ads_for_campaign(
    malaria: Malaria,
) -> Tuple[Sequence[Instruction], Optional[AdOptReport]]:
    userinfo, config, db_conf, state, m, confs = malaria
    strata = hydrate_strata(state, confs["stratum"], confs["creative"])

    df = get_df(db_conf, userinfo.survey_user, strata)

    spend = {get_cluster_from_adset(n): i for n, i in state.spend.items()}

    budget_lookup, report = get_budget_lookup(
        df,
        strata,
        config.budget,
        config.min_budget,
        state.window,
        spend,
        state.total_spend,
        days_left=days_left(config),
        proportional=config.proportional,
    )

    return m.update_instructions(strata, budget_lookup), report


def update_audience_for_campaign(
    malaria: Malaria,
) -> Tuple[Sequence[Instruction], Optional[AdOptReport]]:

    userinfo, config, db_conf, state, m, confs = malaria
    audience_confs = confs["audience"]

    df = get_df(db_conf, userinfo.survey_user, audience_confs)

    if df is None:
        logging.info("No responses found, no audience updates made.")
        return [], None

    audiences = hydrate_audiences(df, m, audience_confs)

    return manage_audiences(state, audiences), None


def run_updates(
    fn: Callable[[Malaria], Tuple[Sequence[Instruction], Optional[AdOptReport]]]
) -> None:

    env = Env()
    db_conf = get_db_conf(env)
    campaigns = get_campaigns(db_conf)

    for c in campaigns:
        m = load_basics(c, env)
        instructions, report = fn(m)

        if report:
            create_adopt_report(c, "FACEBOOK_ADOPT", report, db_conf)

        run_instructions(instructions, m.state)


def update_audience() -> None:
    run_updates(update_audience_for_campaign)


def update_ads() -> None:
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
