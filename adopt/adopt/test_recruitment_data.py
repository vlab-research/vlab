import uuid
from datetime import date, datetime, timedelta
from test.dbfix import cnf, _reset_db
from unittest.mock import MagicMock, patch
import json

from .campaign_queries import create_campaign_confs

from .db import _connect, execute, manyify, query
from .facebook.date_range import DateRange
from .recruitment_data import (
    CollectionPeriod,
    RecruitmentData,
    Study,
    TimePeriod,
    _get_days,
    _load_recruitment_data,
    day_end,
    day_start,
    get_active_studies,
    get_collection_days,
    get_recruitment_data,
    insert_recruitment_data_events,
    today,
    calculate_stat_sql,
    RecruitmentStats,
    AdPlatformRecruitmentStats,
)


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


def create_study(name, user_id="foo@email"):
    q = """
    INSERT INTO users(id) VALUES (%s) RETURNING id
    """

    execute(cnf, q, [user_id])

    q = """
    INSERT INTO credentials(user_id, entity, key, details)
    VALUES (%s, %s, %s, '{}')
    """

    execute(cnf, q, [user_id, "entity", "key"])

    q = """
    INSERT INTO studies(user_id, name, slug, credentials_key, credentials_entity)
    VALUES (%s, %s, %s, %s, %s) RETURNING id
    """

    res = query(
        cnf,
        q,
        [user_id, name, name, "key", "entity"],
    )

    study_id = list(res)[0][0]

    return user_id, study_id


def insert_general_conf(study_id, start_date, end_date):
    config = {
        "start_date": start_date,
        "end_date": end_date,
    }

    create_campaign_confs(study_id, "recruitment", config, cnf)


@patch("adopt.recruitment_data.get_insights")
def test_load_recruitment_data_loads_same_data_multiple_times_without_throwing(mock):
    _reset_db()

    insights = {
        "campaign1": {
            "stratum1": {
                "spend": "100.0",
                "reach": "1000",
                "unique_clicks": "50",
                "impressions": "2000",
                "date_start": "2025-05-11",
                "date_stop": "2025-05-11",
            }
        }
    }
    mock.return_value = insights

    now = datetime.utcnow()
    start = now
    end = now + timedelta(days=2)

    _, study_id = create_study("foo")

    _load_recruitment_data(cnf, study_id, ["campaign1"], start, end, None, now)

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
    assert res[0].data == {"campaign1": insights}

    _load_recruitment_data(cnf, study_id, ["campaign1"], start, end, None, now)
    events = query(cnf, "select * from recruitment_data_events", as_dict=True)
    assert len(list(events)) == 1


@patch("adopt.recruitment_data.get_insights")
def test_load_recruitment_data_adds_additional_events(mock):
    _reset_db()

    insights = {
        "campaign1": {
            "stratum1": {
                "spend": "100.0",
                "reach": "1000",
                "unique_clicks": "50",
                "impressions": "2000",
                "date_start": "2025-05-11",
                "date_stop": "2025-05-11",
            }
        }
    }
    mock.return_value = insights

    now = datetime.utcnow()
    start = day_start(now)
    end = now + timedelta(days=2)

    _, study_id = create_study("foo")
    _load_recruitment_data(cnf, study_id, ["campaign1"], start, end, None, now)

    events = query(cnf, "select * from recruitment_data_events", as_dict=True)
    assert len(list(events)) == 1

    # one day later, temp becomes permanent, now loads two events
    now = now + timedelta(days=1)
    _load_recruitment_data(cnf, study_id, ["campaign1"], start, end, None, now)

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
    _, study_id = create_study("foo")
    data = get_recruitment_data(cnf, study_id)
    assert data == []


def insert_data(dats):
    insert_recruitment_data_events(cnf, dats)


def test_get_active_studies_gets_based_on_latest_conf():
    _reset_db()

    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("foo")

    insert_general_conf(study_id, start, start)
    insert_general_conf(study_id, start, end)

    studies = get_active_studies(cnf, now)

    assert len(studies) == 1
    assert studies[0] == study_id


def test_get_active_studies_gets_only_active_studies():
    _reset_db()

    now = _dt(2, 12)
    start = _dt(1, 10)
    end = _dt(3, 23)

    user_id, study_id = create_study("foo")
    user_id_b, study_id_b = create_study("bar", "bar@email")
    user_id_c, study_id_c = create_study("baz", "baz@email")

    insert_general_conf(study_id, start, end)
    insert_general_conf(study_id_b, start - timedelta(days=1), start)
    insert_general_conf(study_id_c, end, end + timedelta(days=1))

    studies = get_active_studies(cnf, now)

    assert len(studies) == 1
    assert studies[0] == study_id


def test_get_recruitment_data_returns_only_latest_temp_data():
    _reset_db()

    now = _dt(2, 12)
    start = _dt(1, 10)

    _, study_id = create_study("foo")

    to_insert = [
        (
            study_id,
            "facebook",
            start,
            start + timedelta(hours=2),
            True,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "100.0",
                            "reach": "1000",
                            "unique_clicks": "50",
                            "impressions": "2000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    }
                }
            ),
        ),
        (
            study_id,
            "facebook",
            start,
            start + timedelta(hours=4),
            True,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "200.0",
                            "reach": "2000",
                            "unique_clicks": "100",
                            "impressions": "4000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    }
                }
            ),
        ),
        (
            study_id,
            "facebook",
            start,
            day_end(start),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "300.0",
                            "reach": "3000",
                            "unique_clicks": "150",
                            "impressions": "6000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    }
                }
            ),
        ),
        (
            study_id,
            "facebook",
            day_start(now),
            now - timedelta(hours=2),
            True,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "400.0",
                            "reach": "4000",
                            "unique_clicks": "200",
                            "impressions": "8000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    }
                }
            ),
        ),
        (
            study_id,
            "facebook",
            day_start(now),
            now,
            True,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "500.0",
                            "reach": "5000",
                            "unique_clicks": "250",
                            "impressions": "10000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    }
                }
            ),
        ),
    ]

    insert_data(to_insert)

    data = get_recruitment_data(cnf, study_id)
    assert len(data) == 2
    assert data[0].time_period.end == day_end(start)
    assert data[0].temp is False
    assert data[1].time_period.end == now
    assert data[1].temp is True
    assert data[1].data["campaign1"]["stratum1"]["spend"] == "500.0"


def _rd(start, end, temp, data):
    return RecruitmentData(TimePeriod(start, end), temp, data)


def test_calculate_stat_sql_returns_empty_dict_for_no_data():
    _reset_db()
    _, study_id = create_study("foo")
    window = DateRange(_dt(1, 0), _dt(2, 0))
    res = calculate_stat_sql(cnf, window, study_id)
    assert res == {}


def test_calculate_stat_sql_calculates_metrics_correctly():
    _reset_db()
    _, study_id = create_study("foo")

    # Insert test data
    to_insert = [
        (
            study_id,
            "facebook",
            _dt(1, 0),
            _dt(1, 12),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "100.0",
                            "reach": "1000",
                            "unique_clicks": "50",
                            "impressions": "2000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                        "stratum2": {
                            "spend": "200.0",
                            "reach": "2000",
                            "unique_clicks": "100",
                            "impressions": "4000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "150.0",
                            "reach": "1500",
                            "unique_clicks": "75",
                            "impressions": "3000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
        (
            study_id,
            "facebook",
            _dt(1, 12),
            _dt(2, 0),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "150.0",
                            "reach": "1500",
                            "unique_clicks": "75",
                            "impressions": "3000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                        "stratum2": {
                            "spend": "250.0",
                            "reach": "2500",
                            "unique_clicks": "125",
                            "impressions": "5000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "250.0",
                            "reach": "2500",
                            "unique_clicks": "125",
                            "impressions": "5000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
    ]

    insert_data(to_insert)

    window = DateRange(_dt(1, 0), _dt(2, 0))
    res = calculate_stat_sql(cnf, window, study_id)

    # Verify results
    assert "stratum1" in res
    assert "stratum2" in res

    # Check stratum1 metrics (summed across campaigns)
    stratum1 = res["stratum1"]
    assert isinstance(stratum1, AdPlatformRecruitmentStats)
    assert stratum1.spend == 650.0  # 100 + 150 + 150 + 250
    assert stratum1.reach == 6500  # 1000 + 1500 + 1500 + 2500
    assert stratum1.unique_clicks == 325  # 50 + 75 + 75 + 125
    assert stratum1.impressions == 13000
    assert stratum1.cpm == 20.0  # 13000 impressions / 650 spend
    assert stratum1.frequency == 2.0  # 13000 impressions / 6500 reach
    assert stratum1.unique_ctr == 0.05  # 325 clicks / 6500 reach

    # Check stratum2 metrics
    stratum2 = res["stratum2"]
    assert isinstance(stratum2, AdPlatformRecruitmentStats)
    assert stratum2.spend == 450.0  # 200 + 250
    assert stratum2.reach == 4500  # 2000 + 2500
    assert stratum2.unique_clicks == 225  # 100 + 125
    assert stratum2.impressions == 9000  # 4000 + 5000
    assert stratum2.cpm == 20.0  # 9000 impressions / 450 spend
    assert stratum2.frequency == 2.0  # 9000 impressions / 4500 reach
    assert stratum2.unique_ctr == 0.05  # 225 clicks / 4500 reach


def test_calculate_stat_sql_handles_missing_data():
    _reset_db()
    _, study_id = create_study("foo")

    # Insert test data with some missing values
    to_insert = [
        (
            study_id,
            "facebook",
            _dt(1, 0),
            _dt(1, 12),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "100.0",
                            "reach": "1000",
                            "unique_clicks": "50",
                            "impressions": "2000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                        "stratum2": {
                            "spend": "200.0",
                            "reach": "2000",
                            "unique_clicks": None,
                            "impressions": "4000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "150.0",
                            "reach": "1500",
                            "unique_clicks": "75",
                            "impressions": "3000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        )
    ]

    insert_data(to_insert)

    window = DateRange(_dt(1, 0), _dt(2, 0))
    res = calculate_stat_sql(cnf, window, study_id)

    # Verify results
    assert "stratum1" in res
    assert "stratum2" in res

    # Check stratum1 metrics (summed across campaigns)
    stratum1 = res["stratum1"]
    assert isinstance(stratum1, AdPlatformRecruitmentStats)
    assert stratum1.spend == 250.0  # 100 + 150
    assert stratum1.reach == 2500
    assert stratum1.unique_clicks == 125  # 50 + 75
    assert stratum1.impressions == 5000  # 2000 + 3000

    # Check stratum2 metrics (should handle missing unique_clicks)
    stratum2 = res["stratum2"]
    assert isinstance(stratum2, AdPlatformRecruitmentStats)
    assert stratum2.spend == 200.0
    assert stratum2.reach == 2000
    assert stratum2.unique_clicks == 0  # Should default to 0 for missing data
    assert stratum2.impressions == 4000


def test_calculate_stat_sql_respects_date_window():
    _reset_db()
    _, study_id = create_study("foo")

    # Insert test data across different days
    to_insert = [
        (
            study_id,
            "facebook",
            _dt(1, 0),
            _dt(1, 12),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "100.0",
                            "reach": "1000",
                            "unique_clicks": "50",
                            "impressions": "2000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "150.0",
                            "reach": "1500",
                            "unique_clicks": "75",
                            "impressions": "3000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
        (
            study_id,
            "facebook",
            _dt(2, 0),
            _dt(2, 12),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "200.0",
                            "reach": "2000",
                            "unique_clicks": "100",
                            "impressions": "4000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "250.0",
                            "reach": "2500",
                            "unique_clicks": "125",
                            "impressions": "5000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
    ]

    insert_data(to_insert)

    # Test window that only includes first day
    window = DateRange(_dt(1, 0), _dt(1, 23))
    res = calculate_stat_sql(cnf, window, study_id)

    assert "stratum1" in res
    stratum1 = res["stratum1"]
    assert isinstance(stratum1, AdPlatformRecruitmentStats)
    assert stratum1.spend == 250.0  # 100 + 150
    assert stratum1.reach == 2500  # 1000 + 1500
    assert stratum1.unique_clicks == 125  # 50 + 75
    assert stratum1.impressions == 5000  # 2000 + 3000

    # Test window that includes both days
    window = DateRange(_dt(1, 0), _dt(2, 23))
    res = calculate_stat_sql(cnf, window, study_id)

    assert "stratum1" in res
    stratum1 = res["stratum1"]
    assert isinstance(stratum1, AdPlatformRecruitmentStats)
    assert stratum1.spend == 700.0  # 100 + 150 + 200 + 250
    assert stratum1.reach == 7000  # 1000 + 1500 + 2000 + 2500
    assert stratum1.unique_clicks == 350  # 50 + 75 + 100 + 125
    assert stratum1.impressions == 14000  # 2000 + 3000 + 4000 + 5000


def test_calculate_stat_sql_handles_mixed_null_values():
    _reset_db()
    _, study_id = create_study("foo")

    # Insert test data with mixed null and non-null values
    to_insert = [
        (
            study_id,
            "facebook",
            _dt(1, 0),
            _dt(1, 12),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": {
                            "spend": "100.0",
                            "reach": "1000",
                            "unique_clicks": "50",
                            "impressions": "2000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                        "stratum2": {
                            "spend": "200.0",
                            "reach": "2000",
                            "unique_clicks": "100",
                            "impressions": "4000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "150.0",
                            "reach": "1500",
                            "unique_clicks": "75",
                            "impressions": "3000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
        (
            study_id,
            "facebook",
            _dt(1, 12),
            _dt(2, 0),
            False,
            json.dumps(
                {
                    "campaign1": {
                        "stratum1": None,  # This stratum has null data
                        "stratum2": {
                            "spend": "300.0",
                            "reach": "3000",
                            "unique_clicks": "150",
                            "impressions": "6000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        },
                    },
                    "campaign2": {
                        "stratum1": {
                            "spend": "250.0",
                            "reach": "2500",
                            "unique_clicks": "125",
                            "impressions": "5000",
                            "date_start": "2025-05-11",
                            "date_stop": "2025-05-11",
                        }
                    },
                }
            ),
        ),
    ]

    insert_data(to_insert)

    window = DateRange(_dt(1, 0), _dt(2, 0))
    res = calculate_stat_sql(cnf, window, study_id)

    # Verify results - should sum the non-null values and ignore nulls
    assert "stratum1" in res
    assert "stratum2" in res

    # stratum1 should sum values from both campaigns
    stratum1 = res["stratum1"]
    assert isinstance(stratum1, AdPlatformRecruitmentStats)
    assert stratum1.spend == 500.0  # 100 + 150 + 250
    assert stratum1.reach == 5000  # 1000 + 1500 + 2500
    assert stratum1.unique_clicks == 250  # 50 + 75 + 125
    assert stratum1.impressions == 10000  # 2000 + 3000 + 5000

    # stratum2 should sum values from both periods
    stratum2 = res["stratum2"]
    assert isinstance(stratum2, AdPlatformRecruitmentStats)
    assert stratum2.spend == 500.0  # 200 + 300
    assert stratum2.reach == 5000  # 2000 + 3000
    assert stratum2.unique_clicks == 250  # 100 + 150
    assert stratum2.impressions == 10000

    # Verify derived metrics are calculated correctly
    assert stratum1.cpm == 20.0  # 10000 impressions / 500 spend
    assert stratum1.frequency == 2.0  # 10000 impressions / 5000 reach
    assert stratum1.unique_ctr == 0.05  # 250 clicks / 5000 reach

    assert stratum2.cpm == 20.0  # 10000 impressions / 500 spend
    assert stratum2.frequency == 2.0  # 10000 impressions / 5000 reach
    assert stratum2.unique_ctr == 0.05  # 250 clicks / 5000 reach
