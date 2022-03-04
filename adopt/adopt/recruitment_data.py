import json
from datetime import date, datetime, timedelta
from typing import Any, NamedTuple, Optional

from facebook_business.adobjects.adsinsights import AdsInsights

from .db import execute, manyify, query
from .facebook.date_range import DateRange
from .facebook.state import CampaignState, get_insights

Stratum = str  # stratum id of some sort


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
    data: dict[Stratum, Optional[dict]]


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


# eventually this should be told the source too
# (not just facebook, multiple per study)
def facebook_recruitment_data(
    state: CampaignState, start_time: datetime, end_time: datetime, now: datetime
) -> list[RecruitmentData]:

    days = get_collection_days(start_time, end_time, now)

    insights = [
        RecruitmentData(TimePeriod(s, e), t, get_insights(state, s, e))
        for s, e, t in days
    ]

    return insights


def load_recruitment_data(
    db_conf,
    study_id: str,
    start_time: datetime,
    end_time: datetime,
    state: CampaignState,
    now: datetime,
):
    data = facebook_recruitment_data(state, start_time, end_time, now)

    # ORM
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

    q = """
    INSERT INTO recruitment_data_events
    (study_id, source_name, period_start, period_end, temp, data)
    """
    q, records = manyify(q, records)
    q += "ON CONFLICT DO NOTHING"

    execute(db_conf, q, records)


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


def calculate_stat(data: list[RecruitmentData], stat, window=None) -> dict[str, float]:
    if window:
        data = [
            d
            for d in data
            if d.time_period.start >= window.start_date
            and d.time_period.end <= window.until_date
        ]

    daily_stats: dict[str, Any] = {}
    for d in data:
        for k, v in d.data.items():
            if k in daily_stats:
                daily_stats[k].append(v)
            else:
                daily_stats[k] = [v]

    stat = {
        k: sum([float(x.get(stat, 0.0) if x else 0.0) for x in v])
        for k, v in daily_stats.items()
    }
    return stat


# TODO: remove "Study" type, change to just id??
def get_active_studies(db_conf, now: datetime) -> list[Study]:
    q = """
    WITH t AS (
    SELECT s.id,
           s.user_id,
           s.NAME,
           (conf->0->>'start_date')::TIMESTAMP AS start_date,
           (conf->0->>'end_date')::TIMESTAMP AS end_date,
           row_number() over (PARTITION BY sc.study_id ORDER BY sc.created DESC) AS n
    FROM studies s
    JOIN study_confs sc ON sc.study_id = s.id
    WHERE conf_type = 'opt'
    ORDER BY sc.created DESC)
    SELECT id, user_id, name, start_date, end_date
    FROM t
    WHERE n = 1
    AND start_date <= %s
    AND end_date >= %s
    """

    res = query(db_conf, q, [now, now])
    return [Study(*t) for t in res]
