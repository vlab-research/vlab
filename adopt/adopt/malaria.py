import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd
from environs import Env
from facebook_business.adobjects.targeting import Targeting

from .audiences import hydrate_audiences
from .budget import AdOptReport, get_budget_lookup, get_budget_lookup_with_db
from .campaign_queries import (
    DBConf,
    create_adopt_report,
    get_campaign_configs,
    get_user_info,
)
from .facebook.state import DateRange, FacebookState, StateNameError, get_api
from .facebook.update import GraphUpdater, Instruction
from .marketing import manage_audiences, update_instructions, validate_targeting
from .recruitment_data import (
    day_start,
    get_active_studies,
    load_recruitment_data,
)
from .responses import get_inference_data
from .study_conf import CreativeConf, FacebookTargeting, Stratum, StratumConf, StudyConf

logging.basicConfig(level=logging.INFO)


def get_df(
    db_conf: DBConf,
    survey_user: str,
    study_id: str,
) -> Optional[pd.DataFrame]:
    return get_inference_data(survey_user, study_id, db_conf)


def get_db_conf(env: Env) -> DBConf:
    return env("PG_URL")


def get_study_conf(db_conf, study_id: str) -> StudyConf:
    user_info = get_user_info(study_id, db_conf)
    confs = get_campaign_configs(study_id, db_conf)
    cd = {v["conf_type"]: v["conf"] for v in confs}

    # str() around study_id temp, is UUID in some tests now
    params = {"id": str(study_id), "user": user_info, **cd}
    return StudyConf(**params)


def make_window(hours, now):
    start = now - timedelta(hours=hours)
    start = day_start(start)
    return DateRange(start, now)


def run_instructions(instructions: Sequence[Instruction], state: FacebookState):
    updater = GraphUpdater(state)
    for i in instructions:
        report = updater.execute(i)
        logging.info(report)


def update_ads_for_campaign(
    db_conf: DBConf, study: StudyConf, state: FacebookState
) -> Tuple[Sequence[Instruction], Optional[AdOptReport]]:
    strata = hydrate_strata(state, study.strata, study.creatives)
    now = datetime.utcnow()

    inf_start, inf_end = study.recruitment.get_inference_window(now)

    df = get_inference_data(
        study.user.survey_user, study.id, db_conf, inf_start, inf_end
    )

    window = make_window(study.general.opt_window, now)

    # Extract efficiency_weight from recruitment config (default to 1.0 if not present)
    efficiency_weight = getattr(study.recruitment, 'efficiency_weight', 1.0)

    budget_lookup, report = get_budget_lookup_with_db(
        df,
        strata,
        study.recruitment.opt_budget,
        study.recruitment.incentive_per_respondent,
        study.recruitment.opt_sample_size,
        window,
        db_conf,
        study.id,
        efficiency_weight,
    )

    # Generate and store respondents over time report
    try:
        from .campaign_queries import create_respondents_over_time_report
        respondents_report = calculate_respondents_over_time_report(
            df, study.strata, inf_start, inf_end
        )
        create_respondents_over_time_report(study.id, respondents_report, db_conf)
        logging.info(f"Created respondents over time report for study {study.id}")
    except BaseException as e:
        logging.error(f"Error creating respondents over time report: {e}")

    # Generate and store cost over time report
    try:
        from .campaign_queries import create_cost_over_time_report
        cost_report = calculate_cost_over_time_report(
            df, study.strata, db_conf, study.id,
            study.recruitment.incentive_per_respondent
        )
        create_cost_over_time_report(study.id, cost_report, db_conf)
        logging.info(f"Created cost over time report for study {study.id}")
    except BaseException as e:
        logging.error(f"Error creating cost over time report: {e}")

    min_budget = study.recruitment.min_budget
    budget = study.recruitment.spend_for_day(strata, min_budget, budget_lookup, now)

    return update_instructions(study, state, strata, budget), report


def update_audience_for_campaign(
    db_conf: DBConf, study: StudyConf, state: FacebookState
) -> Tuple[Sequence[Instruction], Optional[AdOptReport]]:
    # NOTE: audience ignores inference_window from recruitment... Odd???

    df = get_df(db_conf, study.user.survey_user, study.id)

    if df is None:
        df = pd.DataFrame([], columns=[])
        # logging.info("No responses found, no audience updates made.")
        # return [], None

    audiences = hydrate_audiences(study, df, study.audiences)

    return manage_audiences(state, audiences), None


def update_recruitment_data_for_campaign(
    db_conf: DBConf, study: StudyConf, state: FacebookState
):
    # TODO: actually this shouldn't run for just active studies
    #       it should run for all studies for whom we're missing
    #       recruitment data...

    # also we need a way to select based on pipeline design.

    now = datetime.utcnow()
    load_recruitment_data(db_conf, study, state, now)
    return None, None


AdoptJob = Callable[
    [DBConf, StudyConf, FacebookState],
    Tuple[Sequence[Instruction], Optional[AdOptReport]],
]


def load_basics(
    study_id: str, db_conf: DBConf, env: Env
) -> Tuple[StudyConf, FacebookState]:
    study = get_study_conf(db_conf, study_id)

    state = FacebookState(
        get_api(env, study.user.token), study.general.ad_account, study.campaign_names
    )

    return study, state


def calculate_respondents_over_time_report(
    df: pd.DataFrame,
    strata: list[StratumConf],
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    Calculate respondents over time data for storage as a report.

    Args:
        df: Inference data (already loaded during optimization)
        strata: List of stratum configurations
        start_date: Study recruitment start date
        end_date: Study recruitment end date

    Returns:
        Dict matching RespondentsOverTimeResponse structure
    """
    from .segments_progress import get_user_start_times, build_segments_progress_data
    from .responses import create_time_buckets
    from .budget import prep_df_for_budget

    # Filter data by stratum
    filtered_df = prep_df_for_budget(df, strata)
    if filtered_df is None or filtered_df.empty:
        return {"data": []}

    # Calculate respondents over time
    user_start_times = get_user_start_times(filtered_df)
    buckets = create_time_buckets(start_date, end_date, "hour")

    data = build_segments_progress_data(
        user_start_times=user_start_times,
        buckets=buckets,
        strata_ids=[s.id for s in strata],
    )

    return {"data": data}


def calculate_cost_over_time_report(
    df: Optional[pd.DataFrame],
    strata: list[StratumConf],
    db_conf: DBConf,
    study_id: str,
    incentive_per_respondent: float,
) -> list[dict]:
    """
    Calculate cost over time data for storage.

    Args:
        df: Inference data (already loaded during optimization)
        strata: List of stratum configurations
        db_conf: Database configuration
        study_id: ID of the study
        incentive_per_respondent: Cost of incentive per respondent

    Returns:
        List matching CostOverTimeResponse structure
    """
    from .budget import prep_df_for_budget
    from .segments_progress import get_user_start_times
    from .cost_over_time import count_new_respondents_by_day, calculate_cost_over_time
    from .recruitment_data import get_spend_by_date

    if df is None or df.empty:
        return []

    # Get user start times (same logic as respondents_over_time)
    filtered_df = prep_df_for_budget(df, strata)
    if filtered_df is None or filtered_df.empty:
        return []

    user_start_times = get_user_start_times(filtered_df)
    new_respondents_by_day = count_new_respondents_by_day(user_start_times)

    # Get spend by day from database
    spend_by_day = get_spend_by_date(db_conf, study_id)

    return calculate_cost_over_time(
        spend_by_day, new_respondents_by_day, incentive_per_respondent
    )


def run_updates(fn: AdoptJob) -> None:
    env = Env()
    db_conf = get_db_conf(env)

    now = datetime.utcnow()
    studies = get_active_studies(db_conf, now)

    logging.info(f"Got {len(studies)} active studies to update")

    for s in studies:
        try:
            study, state = load_basics(s, db_conf, env)
            logging.info(f"Updating {study.general.name}")

            instructions, report = fn(db_conf, study, state)

            if instructions is None:
                continue

            if report:
                create_adopt_report(s, "FACEBOOK_ADOPT", report, db_conf)

            run_instructions(instructions, state)

        except BaseException as e:
            logging.error(f"Error updating campaign {s}. Error: {e}")


def update_audience() -> None:
    run_updates(update_audience_for_campaign)


def update_ads() -> None:
    run_updates(update_ads_for_campaign)


def update_recruitment_data() -> None:
    run_updates(update_recruitment_data_for_campaign)


def uniqueness(strata: List[StratumConf]):
    ids = [s.id for s in strata]
    if len(set(ids)) != len(ids):
        raise Exception("Strata IDs combinations are not unique")


def _add_aud(state, name) -> Optional[Dict[str, Any]]:
    try:
        return {"id": state.get_audience(name).get_id()}
    except StateNameError:
        logging.info(
            f"Could not find audience: {name}. Omitting the audience from targeting"
        )
        return None


def add_audience_targeting(
    state: FacebookState, stratum: StratumConf
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
    state: FacebookState, strata: List[StratumConf], creatives: List[CreativeConf]
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
                for k, v in s.dict().items()
                if k not in {"audiences", "excluded_audiences"}
            },
            "creatives": [creative_lookup[c] for c in s.creatives],
            "facebook_targeting": add_audience_targeting(state, s),
        }
        for s in strata
    ]

    return [Stratum(**s) for s in strata_params]
