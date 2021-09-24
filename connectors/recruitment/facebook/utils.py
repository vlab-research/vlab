from datetime import date, datetime, timedelta


def today():
    return datetime.utcnow().date()


def _get_study_days(start: date, until: date):
    days = [start]
    while days[-1] < until:
        days.append(days[-1] + timedelta(days=1))
    return days


def get_study_days(start: date, until: date):
    # if until is in the future or today, get from yesterday
    if until <= today():
        end = today() - timedelta(days=1)
        return _get_study_days(start, end)

    # otherwise get until study end
    return _get_study_days(start, until)
