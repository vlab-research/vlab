import uuid
from datetime import date, datetime, timedelta
from test.dbfix import cnf
from unittest.mock import MagicMock, patch

from .db import _connect, execute, manyify, query
from .facebook.date_range import DateRange
from .recruitment_data import (CollectionPeriod, RecruitmentData, Study,
                               TimePeriod, _get_days, calculate_stat, day_end,
                               day_start, get_collection_days,
                               get_recruitment_data, load_recruitment_data,
                               today)


def _now():
    return datetime.utcnow()


def _cp(start_time, end_time, temp):
    return CollectionPeriod(start_time, end_time, temp)


def test__get_days():
    days = _get_days(date(2021, 1, 1), date(2021, 1, 1))
    assert days == [date(2021, 1, 1)]

    days = _get_days(date(2021, 1, 1), date(2021, 1, 2))
    assert days == [date(2021, 1, 1), date(2021, 1, 2)]

    days = _get_days(date(2021, 1, 1), date(2021, 1, 5))
    assert days == [date(2021, 1, x) for x in [1, 2, 3, 4, 5]]

    days = _get_days(date(2021, 1, 31), date(2021, 2, 2))
    assert days == [date(2021, 1, 31), date(2021, 2, 1), date(2021, 2, 2)]


def _dt(day=1, hour=0, month=1, year=2022):
    return datetime(year, month, day, hour)


def test_get_collection_days_gets_only_today_for_studies_starting_today():
    now = _dt(1, 5)
    start = _dt(1, 0)
    end = _dt(3, 0)

    res = get_collection_days(start, end, now)

    assert res == [
        _cp(start, now, True),
    ]


def test_get_collection_days_gets_up_to_today_studies_ending_today():
    now = _dt(3, 5)
    start = _dt(1, 0)
    end = _dt(3, 23)

    res = get_collection_days(start, end, now)

    assert res == [
        _cp(start, day_end(start), False),
        _cp(
            day_start(start + timedelta(days=1)),
            day_end(start + timedelta(days=1)),
            False,
        ),
        _cp(day_start(now), now, True),
    ]


def test_get_collection_days_gets_up_to_end_for_studies_in_past():
    now = _dt(3, 5)
    start = _dt(1, 3)
    end = _dt(2, 23)

    res = get_collection_days(start, end, now)

    assert res == [
        _cp(start, day_end(start), False),
        _cp(
            _dt(2, 0),
            day_end(_dt(2, 0)),
            False,
        ),
    ]


def test_get_collection_days_gets_up_to_end_for_ongoing_studies():
    now = _dt(3, 5)
    start = _dt(1, 3)
    end = _dt(5, 23)

    res = get_collection_days(start, end, now)

    assert res == [
        _cp(start, day_end(start), False),
        _cp(
            day_start(start + timedelta(days=1)),
            day_end(start + timedelta(days=1)),
            False,
        ),
        _cp(day_start(now), now, True),
    ]


def test_get_collection_days_gets_up_to_now_for_ongoing_study_from_yesterday():
    now = datetime.utcnow()
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)

    res = get_collection_days(start, end, now)

    assert len(res) == 2
    assert res == [
        _cp(start, day_end(start), False),
        _cp(day_start(now), now, True),
    ]


user = str(uuid.uuid4())


def _reset_db():
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            tables = ["study_confs", "recruitment_data_events", "studies", "users"]
            for t in tables:
                cur.execute(f"delete from {t} cascade")
            conn.commit()


def create_study(name, user_email="foo@email"):
    q = """
    INSERT INTO users(email) VALUES (%s) RETURNING id
    """

    res = query(cnf, q, [user_email])
    user_id = list(res)[0][0]

    q = """
    INSERT INTO studies(user_id, name, credentials_key, credentials_entity)
    VALUES (%s, %s, %s, %s) RETURNING id
    """

    res = query(
        cnf,
        q,
        [user_id, name, "key", "entity"],
    )

    return list(res)[0][0]


# def _load_recruitment_data(db, dat):
#     _execute(
#         db,
#         "INSERT INTO receruitment_data(user_id, name, start_time, end_time)"
#         " values(%s, %s, %s, %s)",
#         [user_id, name, start_time, end_time],
#     )


# patch


@patch("adopt.recruitment_data.get_insights")
def test_load_recruitment_data_loads_same_data_multiple_times_without_throwing(mock):
    _reset_db()

    insights = [{"strata1": {"cpm": 1.0}}]
    mock.return_value = insights

    now = datetime.utcnow()
    start = now
    end = now + timedelta(days=2)

    study_id = create_study("foo")

    load_recruitment_data(cnf, study_id, start, end, None, now)

    events = query(cnf, "select * from recruitment_data_events", as_dict=True)

    # ORM
    res = [
        RecruitmentData(
            TimePeriod(e["period_start"], e["period_end"]), e["temp"], e["data"]
        )
        for e in events
    ]

    assert len(res) == 1
    assert res[0].time_period.start.day == now.day
    assert res[0].time_period.end.day == now.day
    assert res[0].data == insights

    load_recruitment_data(cnf, study_id, start, end, None, now)
    events = query(cnf, "select * from recruitment_data_events", as_dict=True)
    assert len(list(events)) == 1


@patch("adopt.recruitment_data.get_insights")
def test_load_recruitment_data_adds_additional_events(mock):
    _reset_db()

    insights = [{"strata1": {"cpm": 1.0}}]
    mock.return_value = insights

    now = datetime.utcnow()
    start = day_start(now)
    end = now + timedelta(days=2)

    study_id = create_study("foo")
    load_recruitment_data(cnf, study_id, start, end, None, now)

    events = query(cnf, "select * from recruitment_data_events", as_dict=True)
    assert len(list(events)) == 1

    # one day later, temp becomes permanent, now loads two events
    now = now + timedelta(days=1)
    load_recruitment_data(cnf, study_id, start, end, None, now)

    events = query(cnf, "select * from recruitment_data_events", as_dict=True)

    # ORM
    res = [
        RecruitmentData(
            TimePeriod(e["period_start"], e["period_end"]), e["temp"], e["data"]
        )
        for e in events
    ]

    assert len(res) == 3
    assert res[0].temp is True
    assert res[1].temp is False
    assert res[0].time_period.start == res[1].time_period.start
    assert res[0].time_period.end != res[1].time_period.end


def test_get_recruitment_data_returns_empty_array_if_no_data():
    _reset_db()
    study_id = create_study("foo")
    data = get_recruitment_data(cnf, study_id)
    assert data == []


def insert_data(dats):
    query = """
    insert into recruitment_data_events
    (study_id, source_name, period_start, period_end, temp, data)
    """

    q, records = manyify(query, dats)

    execute(cnf, q, records)


def test_get_recruitment_data_returns_only_latest_temp_data():
    _reset_db()

    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    study_id = create_study("foo")

    to_insert = [
        (
            study_id,
            "facebook",
            start,
            start + timedelta(hours=2),
            True,
            '{"foo":"bar"}',
        ),
        (
            study_id,
            "facebook",
            start,
            start + timedelta(hours=4),
            True,
            '{"foo":"bar"}',
        ),
        (
            study_id,
            "facebook",
            start,
            day_end(start),
            False,
            '{"foo":"bar"}',
        ),
        (
            study_id,
            "facebook",
            day_start(now),
            now - timedelta(hours=2),
            True,
            '{"foo":"bar"}',
        ),
        (
            study_id,
            "facebook",
            day_start(now),
            now,
            True,
            '{"foo":"baz"}',
        ),
    ]

    insert_data(to_insert)

    data = get_recruitment_data(cnf, study_id)
    assert len(data) == 2
    assert data[0].time_period.end == day_end(start)
    assert data[0].temp is False
    assert data[1].time_period.end == now
    assert data[1].temp is True
    assert data[1].data == {"foo": "baz"}


def _rd(start, end, temp, data):
    return RecruitmentData(TimePeriod(start, end), temp, data)


def test_calculate_spend_calculates_all_spend():
    data = [
        _rd(
            _dt(1, 12),
            day_end(_dt(1, 12)),
            False,
            {"a": {"spend": "1.1"}, "b": {"spend": "0.2"}},
        ),
        _rd(
            _dt(2, 0),
            day_end(_dt(2, 0)),
            False,
            {"a": {"spend": "2.5"}, "b": {"spend": "0.6"}},
        ),
    ]

    res = calculate_stat(data, "spend")
    assert res["a"] == 3.6
    assert res["b"] == 0.8


def test_calculate_spend_calculates_all_spend_within_window():
    data = [
        _rd(
            _dt(1, 12),
            day_end(_dt(1, 12)),
            False,
            {"a": {"spend": "1.1"}, "b": {"spend": "0.2"}},
        ),
        _rd(
            _dt(2, 0),
            day_end(_dt(2, 0)),
            False,
            {"a": {"spend": "2.5"}, "b": {"spend": "0.6"}},
        ),
    ]

    window = DateRange(_dt(2, 0), _dt(3, 0))
    res = calculate_stat(data, "spend", window)

    assert res["a"] == 2.5
    assert res["b"] == 0.6
