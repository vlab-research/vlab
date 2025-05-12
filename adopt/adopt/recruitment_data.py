import json
from datetime import date, datetime, timedelta
from typing import Any, NamedTuple, Optional

from facebook_business.adobjects.adsinsights import AdsInsights

from .db import execute, manyify, query
from .facebook.date_range import DateRange
from .facebook.state import FacebookState
from .study_conf import GeneralConf, StudyConf, UserInfo

Stratum = str  # stratum id of some sort
Campaign = str  # campaign name


class CollectionPeriod(NamedTuple):
    start_time: datetime
    end_time: datetime
    temp: bool


class TimePeriod(NamedTuple):
    start: datetime
    end: datetime


class RecruitmentData(NamedTuple):
    time_period: TimePeriod
    temp: bool
    data: dict[Campaign, dict[Stratum, Optional[dict]]]


class Study(NamedTuple):
    id: str
    user_id: str
    name: str
    start_time: datetime
    end_time: datetime


def today():
    return datetime.utcnow().date()


def _get_days(start: date, until: date):
    days = [start]
    while days[-1] < until:
        days.append(days[-1] + timedelta(days=1))
    return days


def day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


def day_end(d: datetime) -> datetime:
    return datetime(
        d.year, d.month, d.day, hour=23, minute=59, second=59, microsecond=999999
    )


def get_collection_days(
    start: datetime, until: datetime, now: datetime
) -> list[CollectionPeriod]:
    if start > until:
        raise Exception(f"nonsensical time range: {start} to {until}")

    # if start is today, just get today as temp data
    if start.date() == now.date():
        return [CollectionPeriod(start, now, True)]

    # in all other cases, the first day is final
    first = [CollectionPeriod(start, day_end(start), False)]
    start = day_start(start) + timedelta(days=1)

    if start > until:
        return first

    return first + get_collection_days(start, until, now)


# Wrapper for mocking
def get_insights(
    state: FacebookState, campaign: str, start_time: datetime, end_time: datetime
):
    return state.campaign_state(campaign).get_insights(start_time, end_time)


def facebook_recruitment_data(
    state: FacebookState,
    campaigns: list[str],
    start_time: datetime,
    end_time: datetime,
    now: datetime,
) -> list[RecruitmentData]:
    days = get_collection_days(start_time, end_time, now)

    insights = [
        RecruitmentData(
            TimePeriod(s, e),
            t,
            {c: get_insights(state, c, s, e) for c in campaigns},
        )
        for s, e, t in days
    ]

    return insights


# TODO: create a function that finds gaps in recruitment_data
# for all studies and fills the gaps, instead of
# current model of using active studies


def insert_recruitment_data_events(db_conf, records):
    q = """
    INSERT INTO recruitment_data_events
    (study_id, source_name, period_start, period_end, temp, data)
    """
    q, records = manyify(q, records)

    q += """
    ON CONFLICT (study_id, source_name, temp, period_start, period_end)
    DO UPDATE SET data = excluded.data
    """

    return execute(db_conf, q, records)


def _load_recruitment_data(
    db_conf,
    study_id: str,
    campaigns: list[str],
    start_time: datetime,
    end_time: datetime,
    state: FacebookState,
    now: datetime,
):
    data = facebook_recruitment_data(state, campaigns, start_time, end_time, now)

    records = [
        (
            study_id,
            "facebook",
            d.time_period.start,
            d.time_period.end,
            d.temp,
            json.dumps(d.data),
        )
        for d in data
    ]

    return insert_recruitment_data_events(db_conf, records)


def load_recruitment_data(
    db_conf,
    study: StudyConf,
    state: FacebookState,
    now: datetime,
):
    return _load_recruitment_data(
        db_conf,
        study.id,
        study.campaign_names,
        study.recruitment.start_date,
        study.recruitment.end_date,
        state,
        now,
    )


def get_recruitment_data(db_conf, study_id: str) -> list[RecruitmentData]:
    q = """
    SELECT period_start, period_end, temp, DATA
    FROM recruitment_data_events
    WHERE study_id = %s
    AND temp = FALSE

    UNION

    (SELECT period_start, period_end, temp, DATA
    FROM recruitment_data_events
    WHERE study_id = %s
    AND temp = TRUE
    ORDER BY period_end DESC
    LIMIT 1)
    """

    vals = (study_id, study_id)
    res = query(db_conf, q, vals, as_dict=True)

    # ORM
    data = [
        RecruitmentData(
            TimePeriod(e["period_start"], e["period_end"]),
            e["temp"],
            e["data"],
        )
        for e in res
    ]

    return data


def calculate_stat(
    data: list[RecruitmentData], stat, window: DateRange = None
) -> dict[str, float]:
    # Note: sums over campaigns. This good?

    if window:
        data = [
            d
            for d in data
            if d.time_period.start >= window.start_date
            and d.time_period.end <= window.until_date
        ]

    # Initialize sums for all strata with 0.0
    stratum_sums: dict[str, float] = {}
    for d in data:
        for campaign, insights in d.data.items():
            for stratum_id in insights.keys():
                if stratum_id not in stratum_sums:
                    stratum_sums[stratum_id] = 0.0

    # Sum incrementally
    for d in data:
        for campaign, insights in d.data.items():
            for stratum_id, metrics in insights.items():
                if metrics is None:
                    continue
                value = float(metrics.get(stat, 0.0))
                stratum_sums[stratum_id] += value

    return stratum_sums


def get_active_studies(db_conf, now: datetime) -> list[str]:
    q = """
    select id from studies
    join study_state using(id)
    where study_state.start_date < %s
    and study_state.end_date > %s
    """

    res = query(db_conf, q, [now, now])
    return [t[0] for t in res]
