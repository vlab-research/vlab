import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd
from environs import Env
from facebook_business.adobjects.targeting import Targeting

from .audiences import hydrate_audiences
from .authoring.validate import study_conf_from_sections
from .budget import AdOptReport, get_budget_lookup, get_budget_lookup_with_db
from .campaign_queries import (
    DBConf,
    create_ad_attribution,
    create_adopt_report,
    get_ad_attributions,
    get_campaign_configs,
    get_user_info,
)
from .facebook.state import DateRange, FacebookState, StateNameError, get_api
from .facebook.update import GraphUpdater, Instruction
from .marketing import (
    ad_provenance,
    manage_audiences,
    update_instructions,
    validate_targeting,
)
from .recruitment_data import (
    day_start,
    get_active_studies,
    load_recruitment_data,
)
from .responses import get_inference_data
from .study_conf import (
    CreativeConf,
    FacebookTargeting,
    Stratum,
    StratumConf,
    StudyConf,
    missing_targeting_variables,
    thins_its_ref_without_reading_the_mapping,
)

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
    """The stored confs, assembled into the object the whole run path uses.

    The assembly itself lives in `authoring.validate.study_conf_from_sections`
    so that `POST /{org}/studies/{slug}/validate` and the SDK's `vlab validate`
    build a study exactly the way the cron does. It used to be three lines
    inline here, and a validator that reproduced them would have been a second
    definition of "these sections are a study", free to drift from this one —
    which is the drift that made the TypeScript compiler a problem (see
    planning/agent-study-authoring.md §4). This function keeps the two things
    validation cannot do: the database read, and the credential lookup.
    """
    user_info = get_user_info(study_id, db_conf)
    confs = get_campaign_configs(study_id, db_conf)
    cd = {v["conf_type"]: v["conf"] for v in confs}

    # str() around study_id temp, is UUID in some tests now
    return study_conf_from_sections(cd, study_id, user_info)


def make_window(hours, now):
    start = now - timedelta(hours=hours)
    start = day_start(start)
    return DateRange(start, now)


def heal_ad_attributions(
    study: StudyConf, state: FacebookState, db_conf: DBConf
) -> List[str]:
    """Write a mapping row for every live ad that has none. Returns the ad ids.

    **This is the only thing that writes to ad_attributions.** That is the
    design, not an accident of refactoring, and it is worth stating because the
    alternative was tried and failed.

    The row used to be written at the moment of creation, by an imperative step
    that read the ad id out of Facebook's response to an ad-create instruction.
    That gives one chance per ad, to one writer, in one code path: an ad that
    reached Facebook by any other route was unmapped forever -- not "until the
    next run", forever, because reconciliation creates an ad once and the ad now
    exists.

    On 2026-08-30 all eight ads of `vl-pulse-nigeria-smoke` and `-smoke-wa` were
    created through the dashboard's Optimize tab, which POSTs one hand-built
    instruction at a time and never had the provenance to write a row from.
    `ad_attributions` held zero rows in all of production, and swoosh dropped
    every respondent those ads recruited:

        ref token fd7b8a8199 (read from metadata vt) has no ad_attributions
        row for this study; respondent ... is not attributed to any stratum

    Reading the ads that exist, rather than remembering the ones this process
    made, removes the whole class. A writer that has to be present at the
    creation can be absent; one that reconciles cannot. So there is no second
    writer to keep in step -- no provenance threaded through instructions, no
    ad id captured out of a Graph response, no path that has to remember.

    **It only ever adds.** Nothing here deletes or updates. Rows must outlive
    their ads -- respondents keep arriving from ads that no longer exist,
    because a page post can be reshared indefinitely -- so an ad's absence from
    Facebook is never evidence its row should go (invariant 2, stated on the
    table itself in devops/migrations/20260816000000_add_ad_attributions.up.sql).
    A row already present wins by
    `ON CONFLICT DO NOTHING`, so healing can never overwrite a true
    frozen-at-creation snapshot with a reconstruction.

    **A healed row is built from the conf as it reads now**, which is the only
    source left -- Meta stores the ad, not the vocabulary vlab meant by it. So
    if the stratum's metadata changed between the ad being built and this
    running, the row carries today's answer rather than that day's. Narrow, and
    only reachable under ref_mode "encoded": a dotted ref carries the metadata
    itself, so editing it changes the creative and reconciliation rewrites the
    ad. Worth knowing, not worth guarding -- the alternative to a slightly stale
    row is no row and a silent undercount, and `created` already says when the
    row was written for anyone who needs to compare it against the ad's age.

    Strata are hydrated **without** resolving audiences. Healing needs only the
    stratum id, its metadata and its creatives -- never its targeting -- and
    making it depend on a Graph lookup would mean a study with a missing custom
    audience could not repair its attribution. The repair path must not share
    failure modes with the thing being repaired.

    An ad whose (adset name, ad name) pair no longer appears in the conf cannot
    be healed: there is nothing left to say what it meant. That is logged rather
    than skipped quietly, because it is the one case this function cannot fix.
    """
    strata = hydrate_strata(
        None, study.strata, study.creatives, resolve_audiences=False
    )

    existing = {r["ad_id"] for r in get_ad_attributions(study.id, db_conf)}

    healed: List[str] = []
    unmatched: List[Tuple[str, str]] = []

    for campaign_name in study.campaign_names:
        try:
            campaign_state = state.campaign_state(campaign_name)
            live = campaign_state.campaign_state
        except StateNameError:
            # No campaign yet, so no ads and nothing to heal. Not a failure:
            # every study looks like this before its first run.
            continue

        # campaign_state.campaign_name, not the loop variable, for the same
        # reason update_instructions_for_campaign uses it: in a destination
        # experiment the campaign name selects the arm, and the provenance must
        # be built from exactly the value the ads were.
        provenance = ad_provenance(study, campaign_state.campaign_name, strata)

        for adset, ads in live:
            for ad in ads:
                if ad["id"] in existing:
                    continue

                prov = provenance.get((adset["name"], ad["name"]))
                if prov is None:
                    unmatched.append((ad["id"], f'{adset["name"]}/{ad["name"]}'))
                    continue

                create_ad_attribution(ad["id"], prov, db_conf)
                healed.append(ad["id"])

    if healed:
        logging.warning(
            f"heal_ad_attributions: wrote {len(healed)} missing mapping row(s) "
            f"for study {study.id}: {healed}. These ads existed on Facebook "
            "with no ad_attributions row, so their respondents were being "
            "dropped from stratum counts."
        )

    if unmatched:
        logging.error(
            f"heal_ad_attributions: {len(unmatched)} live ad(s) in study "
            f"{study.id} have no mapping row and cannot be given one -- the "
            "current conf describes no (stratum, creative) pair by that name: "
            f"{unmatched}. Their respondents are not attributable."
        )

    return healed


def run_instructions(
    instructions: Sequence[Instruction], state: FacebookState, db_conf: DBConf
):
    """Execute instructions against Facebook. Writes nothing to the database.

    `db_conf` is unused and kept only so the signature does not churn its
    callers. It used to write ad_attributions rows here, from ids Facebook
    returned; `heal_ad_attributions` does that now, from the ads that exist.
    """
    updater = GraphUpdater(state)
    logging.info(f"Executing {len(instructions)} instruction(s)")
    for i in instructions:
        logging.info(
            f"Executing: {i.node}/{i.action} id={i.id} params={i.params}"
        )
        logging.info(updater.execute(i))


def warn_on_incomplete_targeting(study: StudyConf) -> None:
    """Say so when a stratum targets a variable nothing in the study supplies.

    Such a predicate can never match: the stratum counts zero and the optimizer
    reallocates its budget away from a segment that may be recruiting perfectly
    well. Nothing errors, which is exactly why it needs saying out loud.

    A warning, not a raise — see missing_targeting_variables for why.
    """
    for stratum_id, missing in missing_targeting_variables(study).items():
        logging.warning(
            f"Stratum '{stratum_id}' targets variable(s) {sorted(missing)} that no "
            "inference_data extraction conf produces. Its question_targeting can "
            "never match, so it will count zero respondents and the optimizer will "
            "move its budget elsewhere. Check the study's inference_data conf."
        )


def warn_on_thinned_ref_without_mapping(study: StudyConf) -> None:
    """Say so when a study thins its ref but nothing reads the mapping.

    Thinning the ref only works if the study also reads the ad -> stratum
    mapping, through a `mapping: "ad_table_lookup"` extraction conf. One without
    the other leaves the study with no attribution at all: the ref no longer
    carries the stratum and nothing looks the token up, so every stratum counts
    zero and the optimizer reallocates on empty data.

    A warning, not a raise — a study recruiting uniformly needs no stratum
    attribution and is entitled to a thin ref.
    """
    thinned = thins_its_ref_without_reading_the_mapping(study)

    if thinned:
        logging.warning(
            f"Destination(s) {thinned} no longer carry stratum metadata in "
            "their ref, but this study has no inference_data conf with "
            'mapping: "ad_table_lookup". Nothing will attribute its respondents '
            "to a stratum: every stratum will count zero and the optimizer will "
            "reallocate on empty data. Either add the lookup confs, or set the "
            "destination's ref_mode to 'metadata'."
        )


def update_ads_for_campaign(
    db_conf: DBConf, study: StudyConf, state: FacebookState
) -> Tuple[Sequence[Instruction], Optional[AdOptReport]]:
    # Before anything else, and unconditionally. Healing is not part of
    # optimizing -- it is the run paying off whatever the last one failed to
    # record, whichever entrypoint that was. Putting it here rather than in
    # run_updates is what gets the dashboard's Optimize tab covered too: both
    # the cron and the API call this one function.
    heal_ad_attributions(study, state, db_conf)

    strata = hydrate_strata(state, study.strata, study.creatives)
    warn_on_incomplete_targeting(study)
    warn_on_thinned_ref_without_mapping(study)
    now = datetime.utcnow()

    inf_start, inf_end = study.recruitment.get_inference_window(now)

    df = get_inference_data(
        study.user.survey_user, study.id, db_conf, inf_start, inf_end
    )

    window = make_window(study.general.opt_window, now)

    # Extract efficiency_weight from recruitment config (default to 1.0 if not present)
    efficiency_weight = getattr(study.recruitment, 'efficiency_weight', 1.0)
    optimizer_version = getattr(study.recruitment, 'optimizer_version', 'closed_form')

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
        optimizer_version=optimizer_version,
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

    # Written here rather than by run_updates so that an optimization run
    # recorded itself the same way whoever asked for it. The dashboard's
    # Optimize tab reaches this function too, and used to leave no
    # FACEBOOK_ADOPT report at all -- so the allocation a researcher acted on
    # from the UI was the one allocation with no record of having happened.
    if report:
        create_adopt_report(study.id, "FACEBOOK_ADOPT", report, db_conf)

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

    return study, fresh_state(study, env)


def fresh_state(study: StudyConf, env: Env) -> FacebookState:
    """A FacebookState that has not read anything yet.

    CampaignState caches its adsets and ads on first access, which is what
    makes a reconciliation run cheap and is exactly wrong after that run has
    created something: the cached list predates the new ad. Anything that needs
    to see what Facebook holds *now* takes one of these rather than reusing the
    state it already has.
    """
    return FacebookState(
        get_api(env, study.user.token), study.general.ad_account, study.campaign_names
    )


def calculate_respondents_over_time_report(
    df: Optional[pd.DataFrame],
    strata: list[StratumConf],
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    Calculate respondents over time data for storage as a report.

    Args:
        df: Inference data (already loaded during optimization), can be None
        strata: List of stratum configurations
        start_date: Study recruitment start date
        end_date: Study recruitment end date (not used; instead we use the max timestamp from data)

    Returns:
        Dict matching RespondentsOverTimeResponse structure
    """
    from .segments_progress import get_user_start_times, build_segments_progress_data
    from .responses import create_time_buckets
    from .budget import prep_df_for_budget

    # Handle case where no inference data is available
    if df is None or df.empty:
        return {"data": []}

    # Filter data by stratum
    filtered_df = prep_df_for_budget(df, strata)
    if filtered_df is None or filtered_df.empty:
        return {"data": []}

    # Calculate respondents over time
    user_start_times = get_user_start_times(filtered_df)

    # Filter to only users belonging to the configured strata before computing the end date.
    # user_start_times can contain ad interaction events for users outside the current strata,
    # which would produce a far-future end date and thousands of empty hourly buckets.
    strata_ids = [s.id for s in strata]
    matching_user_start_times = user_start_times[user_start_times['stratum_id'].isin(strata_ids)]
    if matching_user_start_times.empty:
        return {"data": []}

    # Anchor bucket range to actual interaction data, not the configured study dates.
    # start_date can be set years in the past (e.g., to capture historical campaign data),
    # which would generate thousands of empty leading buckets.
    actual_start_date = matching_user_start_times['start_time'].min()
    actual_end_date = matching_user_start_times['start_time'].max()

    buckets = create_time_buckets(actual_start_date, actual_end_date, "hour")

    data = build_segments_progress_data(
        user_start_times=matching_user_start_times,
        buckets=buckets,
        strata_ids=strata_ids,
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

            logging.info(
                f"Generated {len(instructions)} instruction(s) for {study.general.name}"
            )

            # The FACEBOOK_ADOPT report is written by the job that produced it
            # (update_ads_for_campaign), not here, so that every caller of that
            # function records it and not just this one.
            made_ads = any(
                i.node == "ad" and i.action == "create" for i in instructions
            )

            run_instructions(instructions, state, db_conf)

            # Heal again if this run made ads. The heal at the top of
            # update_ads_for_campaign ran before them, so without this their
            # rows would wait for the next run -- two hours on the ads cron.
            # Nothing is lost by waiting (swoosh rebuilds a study's
            # inference_data from scratch each run, so a late row is applied
            # retroactively), but there is no reason to make a new ad spend for
            # two hours while the optimizer cannot see who it recruited.
            #
            # Conditional, so a steady-state run -- which creates nothing --
            # pays no extra Graph reads at all.
            if made_ads:
                heal_ad_attributions(study, fresh_state(study, env), db_conf)

        except BaseException as e:
            logging.error(f"Error updating campaign {s}. Error: {e}")


def update_audience() -> None:
    run_updates(update_audience_for_campaign)


def update_ads() -> None:
    run_updates(update_ads_for_campaign)


def update_recruitment_data() -> None:
    run_updates(update_recruitment_data_for_campaign)


def get_study_conf_for_reports(db_conf: DBConf, study_id: str) -> StudyConf:
    """
    Load study configuration for report generation only.

    Unlike get_study_conf(), this does not require valid Facebook credentials.
    It uses the study_id as the survey_user since get_inference_data()
    queries by study_id directly.

    Args:
        db_conf: Database configuration
        study_id: Study ID

    Returns:
        StudyConf with minimal user info (no FB token required)
    """
    from .campaign_queries import get_campaign_configs

    confs = get_campaign_configs(study_id, db_conf)
    cd = {v["conf_type"]: v["conf"] for v in confs}

    # For reports, we don't need actual Facebook credentials
    # Use study_id as survey_user since inference_data is queried by study_id
    user_info = {"token": "", "survey_user": str(study_id)}

    params = {"id": str(study_id), "user": user_info, **cd}
    return StudyConf(**params)


def heal_reports_for_study(db_conf: DBConf, study_id: str) -> tuple[bool, bool]:
    """
    Generate respondents_over_time and cost_over_time reports for a study.

    This function does NOT run optimization or require Facebook API access.
    It only reads from inference_data and recruitment_data_events tables.

    Args:
        db_conf: Database configuration
        study_id: Study ID to generate reports for

    Returns:
        Tuple of (respondents_success, cost_success) booleans
    """
    respondents_success = False
    cost_success = False

    try:
        study = get_study_conf_for_reports(db_conf, study_id)
    except Exception as e:
        logging.error(f"Failed to load study config for {study_id}: {e}")
        return respondents_success, cost_success

    # Get inference window from recruitment config
    now = datetime.utcnow()
    inf_start, inf_end = study.recruitment.get_inference_window(now)

    # Load inference data (no FB API needed)
    df = get_inference_data(
        study.user.survey_user, study.id, db_conf, inf_start, inf_end
    )

    # Generate respondents over time report
    try:
        from .campaign_queries import create_respondents_over_time_report
        respondents_report = calculate_respondents_over_time_report(
            df, study.strata, inf_start, inf_end
        )
        create_respondents_over_time_report(study.id, respondents_report, db_conf)
        logging.info(f"Healed respondents_over_time report for study {study_id}")
        respondents_success = True
    except Exception as e:
        logging.error(f"Error healing respondents_over_time report for {study_id}: {e}")

    # Generate cost over time report
    try:
        from .campaign_queries import create_cost_over_time_report
        cost_report = calculate_cost_over_time_report(
            df, study.strata, db_conf, study.id,
            study.recruitment.incentive_per_respondent
        )
        create_cost_over_time_report(study.id, cost_report, db_conf)
        logging.info(f"Healed cost_over_time report for study {study_id}")
        cost_success = True
    except Exception as e:
        logging.error(f"Error healing cost_over_time report for {study_id}: {e}")

    return respondents_success, cost_success


def run_report_healing(days_back: int = 14, now: Optional[datetime] = None) -> None:
    """
    Heal reports for all studies active in the past X days.

    This is the entry point for the healing CronJob. It:
    1. Gets all studies active within the lookback window
    2. Generates respondents_over_time and cost_over_time reports for each
    3. Does NOT run optimization or require Facebook API access

    Args:
        days_back: Number of days to look back for studies (default: 14)
        now: Current datetime (optional, defaults to utcnow for production)
    """
    from .recruitment_data import get_recent_studies

    env = Env()
    db_conf = get_db_conf(env)
    if now is None:
        now = datetime.utcnow()

    studies = list(get_recent_studies(db_conf, now, days_back))
    logging.info(f"Report healing: found {len(studies)} studies (lookback: {days_back} days)")

    success_count = 0
    failure_count = 0

    for study_id in studies:
        try:
            respondents_ok, cost_ok = heal_reports_for_study(db_conf, study_id)
            if respondents_ok and cost_ok:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logging.error(f"Failed to heal reports for study {study_id}: {e}")
            failure_count += 1

    logging.info(f"Report healing complete: {success_count} succeeded, {failure_count} failed")


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
    state: Optional[FacebookState], stratum: StratumConf
) -> FacebookTargeting:
    targeting = stratum.facebook_targeting

    # Merge static audiences from facebook_targeting with dynamic vlab-managed ones
    # from stratum.audiences/excluded_audiences, rather than replacing them.
    existing_custom = targeting.get(Targeting.Field.custom_audiences, [])
    dynamic_custom = [ca for s in stratum.audiences if (ca := _add_aud(state, s))]
    targeting[Targeting.Field.custom_audiences] = existing_custom + dynamic_custom

    existing_excluded = targeting.get(Targeting.Field.excluded_custom_audiences, [])
    dynamic_excluded = [eca for s in stratum.excluded_audiences if (eca := _add_aud(state, s))]
    targeting[Targeting.Field.excluded_custom_audiences] = existing_excluded + dynamic_excluded

    return targeting


def hydrate_strata(
    state: Optional[FacebookState],
    strata: List[StratumConf],
    creatives: List[CreativeConf],
    resolve_audiences: bool = True,
) -> List[Stratum]:
    """Turn stratum configs into strata, resolving vlab-managed audiences.

    `resolve_audiences=False` skips the only step that talks to the Graph API,
    and then `state` may be None. It exists for `adopt-probe --print-creative`,
    which builds creatives -- and a creative depends on the stratum's id,
    metadata and creative list, never on its targeting. Reusing this rather
    than building Stratum a second way is deliberate: a copy of these four
    lines is exactly the kind of divergence the probe exists to catch.

    The strata it returns carry only the *static* facebook_targeting in that
    mode, so they must not be used to build ad sets. Nothing that does takes
    the flag.
    """
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
            "facebook_targeting": (
                add_audience_targeting(state, s)
                if resolve_audiences
                else s.facebook_targeting
            ),
        }
        for s in strata
    ]

    return [Stratum(**s) for s in strata_params]
