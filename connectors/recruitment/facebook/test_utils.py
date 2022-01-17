from datetime import date, datetime, timedelta

from utils import _get_study_days, get_study_days, today


def test__get_study_days():
    days = _get_study_days(date(2021, 1, 1), date(2021, 1, 1))
    assert days == [date(2021, 1, 1)]

    days = _get_study_days(date(2021, 1, 1), date(2021, 1, 2))
    assert days == [date(2021, 1, 1), date(2021, 1, 2)]

    days = _get_study_days(date(2021, 1, 1), date(2021, 1, 5))
    assert days == [date(2021, 1, x) for x in [1, 2, 3, 4, 5]]

    days = _get_study_days(date(2021, 1, 31), date(2021, 2, 2))
    assert days == [date(2021, 1, 31), date(2021, 2, 1), date(2021, 2, 2)]


def test_get_study_days_gets_():
    # pass
    start = today() - timedelta(days=2)
    days = get_study_days(start, today())
    assert days == [start, today() - timedelta(days=1)]
    # assert days == [date(2021, 1, 1)]
