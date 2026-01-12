from datetime import datetime, timedelta
import pytest
from .responses import create_time_buckets

# from datetime import datetime, timezone
# import pytest
# from test.dbfix import db, cnf as chatbase
# from .responses import *

# @pytest.fixture()
# def dat(db):
#     conn, cur = db

#     q = """
#     INSERT INTO responses(surveyid, userid, question_ref, response, metadata, timestamp)
#     VALUES (%s, %s, %s, %s, %s, %s)
#     """

#     rows = [
#         ('1', '1', '1', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('1', '1', '1', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('1', '1', '2', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('1', '1', '2', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('1', '1', '3', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),

#         ('2', '2', '1', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('2', '2', '1', 'bar', '{"mykey": "baz"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('2', '2', '2', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 1, tzinfo=timezone.utc))
#     ]

#     for r in rows:
#         cur.execute(q, r)

#     conn.commit()

#     yield True

#     cur.execute('DELETE FROM responses;')
#     conn.commit()


# def test_last_responses_gets_only_last_answer(db, dat):
#     res = list(last_responses('1', ['1'], chatbase))
#     assert len(res) == 1
#     assert res[0]['response'] == 'bar'


# def test_last_responses_gets_only_last_answer_multiple_surveys(db, dat):
#     res = list(last_responses(['1', '2'], ['1'], chatbase))
#     assert len(res) == 2
#     assert res[0]['response'] == 'bar'
#     assert res[1]['response'] == 'bar'


# def test_last_responses_works_with_multiple_questions(db, dat):
#     res = list(last_responses('1', ['1', '2', '3'], chatbase))
#     assert len(res) == 3
#     assert res[0]['question_ref'] == '1'
#     assert res[0]['response'] == 'bar'
#     assert res[1]['question_ref'] == '2'
#     assert res[1]['response'] == 'bar'
#     assert res[2]['question_ref'] == '3'
#     assert res[2]['response'] == 'foo'


# def test_last_responses_works_with_multiple_questions_and_surveys(db, dat):
#     res = list(last_responses(['1', '2'], ['1', '2'], chatbase))
#     assert len(res) == 4

#     assert {r['question_ref'] for r in res} == set(['1', '2'])
#     assert {r['response'] for r in res} == set(['bar'])

# def test_get_metadata_creates_question(db, dat):
#     res = list(get_metadata(['2'], chatbase))
#     assert res[0]['question_ref'] == 'md:mykey'
#     assert res[0]['response'] == 'baz'

# def test_get_metadata_creates_question_many_surveys(db, dat):
#     res = list(get_metadata(['1', '2'], chatbase))
#     assert res[0]['question_ref'] == 'md:mykey'
#     assert res[0]['response'] == 'bar'
#     assert res[1]['question_ref'] == 'md:mykey'
#     assert res[1]['response'] == 'baz'
#     assert len(res) == 2


# Tests for create_time_buckets() function

class TestCreateTimeBucketsDaily:
    """Test suite for daily time buckets."""

    def test_daily_buckets_basic(self):
        """Test basic daily bucketing with mid-day start and end times."""
        start = datetime(2024, 1, 1, 10, 30)
        end = datetime(2024, 1, 5, 15, 0)

        buckets = create_time_buckets(start, end, "day")

        # Should have 5 buckets (Jan 1-5)
        assert len(buckets) == 5
        # First bucket should start at midnight Jan 1
        assert buckets[0][0] == datetime(2024, 1, 1, 0, 0)
        # First bucket should end at midnight Jan 2
        assert buckets[0][1] == datetime(2024, 1, 2, 0, 0)
        # Each subsequent bucket should be 1 day apart
        for i in range(5):
            assert buckets[i][1] - buckets[i][0] == timedelta(days=1)

    def test_daily_buckets_aligned_to_midnight(self):
        """Verify daily buckets are aligned to midnight boundaries."""
        start = datetime(2024, 6, 15, 22, 45)
        end = datetime(2024, 6, 18, 3, 30)

        buckets = create_time_buckets(start, end, "day")

        # All buckets should start and end at hour 0 (midnight)
        for bucket_start, bucket_end in buckets:
            assert bucket_start.hour == 0
            assert bucket_start.minute == 0
            assert bucket_start.second == 0
            assert bucket_end.hour == 0
            assert bucket_end.minute == 0
            assert bucket_end.second == 0

    def test_daily_buckets_spanning_month_boundary(self):
        """Test daily buckets that span across month boundaries."""
        start = datetime(2024, 1, 30, 12, 0)
        end = datetime(2024, 2, 2, 12, 0)

        buckets = create_time_buckets(start, end, "day")

        # Should have 4 buckets
        assert len(buckets) == 4
        # Verify correct month transitions
        assert buckets[0][0] == datetime(2024, 1, 30, 0, 0)
        assert buckets[1][0] == datetime(2024, 1, 31, 0, 0)
        assert buckets[2][0] == datetime(2024, 2, 1, 0, 0)
        assert buckets[3][0] == datetime(2024, 2, 2, 0, 0)

    def test_daily_buckets_spanning_year_boundary(self):
        """Test daily buckets that span across year boundaries."""
        start = datetime(2023, 12, 31, 15, 0)
        end = datetime(2024, 1, 2, 15, 0)

        buckets = create_time_buckets(start, end, "day")

        # Should have 3 buckets
        assert len(buckets) == 3
        assert buckets[0][0] == datetime(2023, 12, 31, 0, 0)
        assert buckets[1][0] == datetime(2024, 1, 1, 0, 0)
        assert buckets[2][0] == datetime(2024, 1, 2, 0, 0)

    def test_daily_buckets_single_day(self):
        """Test daily buckets when start and end are on the same day."""
        start = datetime(2024, 5, 15, 8, 30)
        end = datetime(2024, 5, 15, 18, 45)

        buckets = create_time_buckets(start, end, "day")

        # Should have 1 bucket for the single day
        assert len(buckets) == 1
        assert buckets[0][0] == datetime(2024, 5, 15, 0, 0)
        assert buckets[0][1] == datetime(2024, 5, 16, 0, 0)


class TestCreateTimeBucketsHourly:
    """Test suite for hourly time buckets."""

    def test_hourly_buckets_basic(self):
        """Test basic hourly bucketing."""
        start = datetime(2024, 1, 1, 10, 30)
        end = datetime(2024, 1, 1, 14, 15)

        buckets = create_time_buckets(start, end, "hour")

        # Should have 5 buckets (10:00, 11:00, 12:00, 13:00, 14:00)
        # because current < end includes 14:00 as start < 14:15
        assert len(buckets) == 5
        # First bucket should start at 10:00 (minutes stripped)
        assert buckets[0][0] == datetime(2024, 1, 1, 10, 0)
        # First bucket should end at 11:00
        assert buckets[0][1] == datetime(2024, 1, 1, 11, 0)

    def test_hourly_buckets_aligned_to_hour(self):
        """Verify hourly buckets are aligned to hour boundaries."""
        start = datetime(2024, 1, 1, 5, 45, 30)
        end = datetime(2024, 1, 1, 9, 30, 15)

        buckets = create_time_buckets(start, end, "hour")

        # All buckets should have minutes and seconds set to 0
        for bucket_start, bucket_end in buckets:
            assert bucket_start.minute == 0
            assert bucket_start.second == 0
            assert bucket_start.microsecond == 0
            assert bucket_end.minute == 0
            assert bucket_end.second == 0
            assert bucket_end.microsecond == 0

    def test_hourly_buckets_spanning_midnight(self):
        """Test hourly buckets that span across midnight boundary."""
        start = datetime(2024, 1, 1, 22, 30)
        end = datetime(2024, 1, 2, 2, 15)

        buckets = create_time_buckets(start, end, "hour")

        # Should have 5 buckets (22:00, 23:00, 00:00, 01:00, 02:00)
        # because 2:00 < 2:15
        assert len(buckets) == 5
        assert buckets[0][0] == datetime(2024, 1, 1, 22, 0)
        assert buckets[1][0] == datetime(2024, 1, 1, 23, 0)
        assert buckets[2][0] == datetime(2024, 1, 2, 0, 0)
        assert buckets[3][0] == datetime(2024, 1, 2, 1, 0)
        assert buckets[4][0] == datetime(2024, 1, 2, 2, 0)

    def test_hourly_buckets_single_hour(self):
        """Test hourly buckets when start and end are within the same hour."""
        start = datetime(2024, 1, 1, 12, 15)
        end = datetime(2024, 1, 1, 12, 45)

        buckets = create_time_buckets(start, end, "hour")

        # Should have 1 bucket
        assert len(buckets) == 1
        assert buckets[0][0] == datetime(2024, 1, 1, 12, 0)
        assert buckets[0][1] == datetime(2024, 1, 1, 13, 0)

    def test_hourly_buckets_spanning_multiple_days(self):
        """Test hourly buckets that span multiple days."""
        start = datetime(2024, 1, 1, 20, 30)
        end = datetime(2024, 1, 3, 4, 15)

        buckets = create_time_buckets(start, end, "hour")

        # Each bucket should be exactly 1 hour
        for bucket_start, bucket_end in buckets:
            assert bucket_end - bucket_start == timedelta(hours=1)


class TestCreateTimeBucketsWeekly:
    """Test suite for weekly time buckets."""

    def test_weekly_buckets_basic(self):
        """Test basic weekly bucketing."""
        # Start on a Wednesday, end on the following Tuesday
        start = datetime(2024, 1, 3, 10, 30)  # Wednesday
        end = datetime(2024, 1, 16, 15, 0)    # Tuesday (2 weeks later)

        buckets = create_time_buckets(start, end, "week")

        # Should have 3 buckets (Jan 1-8, Jan 8-15, Jan 15-22)
        # because Jan 15 < Jan 16:15
        assert len(buckets) == 3
        # First bucket should start at the Monday of that week
        assert buckets[0][0] == datetime(2024, 1, 1, 0, 0)  # Monday
        # First bucket should end at the Monday of the next week
        assert buckets[0][1] == datetime(2024, 1, 8, 0, 0)

    def test_weekly_buckets_start_on_monday(self):
        """Verify weekly buckets always start on Monday."""
        # Start on a Friday
        start = datetime(2024, 1, 5, 14, 30)
        end = datetime(2024, 1, 22, 10, 0)

        buckets = create_time_buckets(start, end, "week")

        # All buckets should start on a Monday
        for bucket_start, bucket_end in buckets:
            # Monday is weekday() == 0
            assert bucket_start.weekday() == 0
            # Each bucket should start at midnight
            assert bucket_start.hour == 0
            assert bucket_start.minute == 0
            assert bucket_start.second == 0
            # And end on the next Monday at midnight
            assert bucket_end.weekday() == 0

    def test_weekly_buckets_aligned_to_midnight(self):
        """Verify weekly buckets are aligned to midnight."""
        start = datetime(2024, 1, 10, 23, 59, 59)
        end = datetime(2024, 1, 31, 12, 0, 0)

        buckets = create_time_buckets(start, end, "week")

        for bucket_start, bucket_end in buckets:
            assert bucket_start.hour == 0
            assert bucket_start.minute == 0
            assert bucket_start.second == 0
            assert bucket_end.hour == 0
            assert bucket_end.minute == 0
            assert bucket_end.second == 0

    def test_weekly_buckets_spanning_month_boundary(self):
        """Test weekly buckets that span across month boundaries."""
        start = datetime(2024, 1, 29, 10, 0)  # Monday of last week in Jan
        end = datetime(2024, 2, 12, 10, 0)    # Into February

        buckets = create_time_buckets(start, end, "week")

        # Each bucket should be exactly 1 week
        for bucket_start, bucket_end in buckets:
            assert bucket_end - bucket_start == timedelta(weeks=1)

    def test_weekly_buckets_single_week(self):
        """Test weekly buckets when start and end are within the same week."""
        start = datetime(2024, 1, 3, 12, 0)   # Wednesday
        end = datetime(2024, 1, 5, 15, 0)     # Friday of same week

        buckets = create_time_buckets(start, end, "week")

        # Should have 1 bucket
        assert len(buckets) == 1
        # Should start at the Monday of that week
        assert buckets[0][0] == datetime(2024, 1, 1, 0, 0)
        # Should end at the Monday of the next week
        assert buckets[0][1] == datetime(2024, 1, 8, 0, 0)

    def test_weekly_buckets_start_exactly_on_monday(self):
        """Test weekly buckets when start is exactly on a Monday."""
        start = datetime(2024, 1, 8, 0, 0)   # Monday
        end = datetime(2024, 1, 29, 0, 0)    # Monday 3 weeks later

        buckets = create_time_buckets(start, end, "week")

        # Should have 3 buckets
        assert len(buckets) == 3
        assert buckets[0][0] == datetime(2024, 1, 8, 0, 0)
        assert buckets[1][0] == datetime(2024, 1, 15, 0, 0)
        assert buckets[2][0] == datetime(2024, 1, 22, 0, 0)


class TestCreateTimeBucketsEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_start_equals_end_daily_at_midnight(self):
        """Test that start equals end at midnight returns empty list (edge case)."""
        # When start and end are the same and at a boundary, aligned start >= end
        dt = datetime(2024, 1, 15, 0, 0)

        buckets = create_time_buckets(dt, dt, "day")

        # No bucket because aligned start (midnight) is not < end
        assert buckets == []

    def test_start_equals_end_daily_mid_day(self):
        """Test that start equals end mid-day returns one bucket (aligned to midnight)."""
        # When start and end are the same but mid-day, aligned start < end
        dt = datetime(2024, 1, 15, 12, 30)

        buckets = create_time_buckets(dt, dt, "day")

        # One bucket because aligned start (midnight) < end (12:30)
        assert len(buckets) == 1
        assert buckets[0][0] == datetime(2024, 1, 15, 0, 0)
        assert buckets[0][1] == datetime(2024, 1, 16, 0, 0)

    def test_start_equals_end_hourly_at_hour_boundary(self):
        """Test hourly buckets when start equals end at hour boundary."""
        dt = datetime(2024, 1, 15, 12, 0)

        buckets = create_time_buckets(dt, dt, "hour")

        # No bucket because aligned start equals end
        assert buckets == []

    def test_start_equals_end_hourly_mid_hour(self):
        """Test hourly buckets when start equals end mid-hour."""
        dt = datetime(2024, 1, 15, 12, 30)

        buckets = create_time_buckets(dt, dt, "hour")

        # One bucket because aligned start (12:00) < end (12:30)
        assert len(buckets) == 1
        assert buckets[0][0] == datetime(2024, 1, 15, 12, 0)
        assert buckets[0][1] == datetime(2024, 1, 15, 13, 0)

    def test_start_equals_end_weekly_at_monday_midnight(self):
        """Test weekly buckets when start equals end at Monday midnight."""
        dt = datetime(2024, 1, 15, 0, 0)  # Monday midnight

        buckets = create_time_buckets(dt, dt, "week")

        # No bucket because aligned start equals end
        assert buckets == []

    def test_start_equals_end_weekly_mid_week(self):
        """Test weekly buckets when start equals end mid-week."""
        # Monday is Jan 15, 2024
        dt = datetime(2024, 1, 15, 12, 30)

        buckets = create_time_buckets(dt, dt, "week")

        # One bucket because aligned start (Monday midnight) < end (12:30)
        assert len(buckets) == 1
        assert buckets[0][0] == datetime(2024, 1, 15, 0, 0)
        assert buckets[0][1] == datetime(2024, 1, 22, 0, 0)

    def test_invalid_bucket_size_raises_error(self):
        """Test that invalid bucket_size raises ValueError."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 5, 0, 0)

        with pytest.raises(ValueError) as exc_info:
            create_time_buckets(start, end, "invalid")

        assert "Invalid bucket_size" in str(exc_info.value)

    def test_invalid_bucket_size_month_raises_error(self):
        """Test that 'month' bucket size raises ValueError."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 3, 1, 0, 0)

        with pytest.raises(ValueError):
            create_time_buckets(start, end, "month")

    def test_invalid_bucket_size_year_raises_error(self):
        """Test that 'year' bucket size raises ValueError."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2025, 1, 1, 0, 0)

        with pytest.raises(ValueError):
            create_time_buckets(start, end, "year")

    def test_start_after_end_returns_empty_list(self):
        """Test that start > end returns an empty list."""
        start = datetime(2024, 1, 15, 0, 0)
        end = datetime(2024, 1, 1, 0, 0)

        buckets = create_time_buckets(start, end, "day")

        assert buckets == []

    def test_bucket_size_case_sensitive(self):
        """Test that bucket_size parameter is case-sensitive."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 5, 0, 0)

        # Should fail because 'Day' is not 'day'
        with pytest.raises(ValueError):
            create_time_buckets(start, end, "Day")

    def test_microseconds_stripped_from_daily_buckets(self):
        """Test that microseconds are stripped from daily bucket boundaries."""
        start = datetime(2024, 1, 1, 10, 30, 45, 123456)
        end = datetime(2024, 1, 3, 15, 20, 30, 654321)

        buckets = create_time_buckets(start, end, "day")

        for bucket_start, bucket_end in buckets:
            assert bucket_start.microsecond == 0
            assert bucket_end.microsecond == 0
            assert bucket_start.second == 0
            assert bucket_end.second == 0

    def test_microseconds_stripped_from_hourly_buckets(self):
        """Test that microseconds are stripped from hourly bucket boundaries."""
        start = datetime(2024, 1, 1, 10, 30, 45, 123456)
        end = datetime(2024, 1, 1, 14, 20, 30, 654321)

        buckets = create_time_buckets(start, end, "hour")

        for bucket_start, bucket_end in buckets:
            assert bucket_start.microsecond == 0
            assert bucket_end.microsecond == 0
            assert bucket_start.second == 0
            assert bucket_end.second == 0


class TestCreateTimeBucketsBoundaryAlignment:
    """Test suite for verifying boundary alignment across bucket types."""

    def test_daily_bucket_end_is_next_day_start(self):
        """Verify that one bucket's end time is the next bucket's start time."""
        start = datetime(2024, 1, 1, 12, 0)
        end = datetime(2024, 1, 7, 12, 0)

        buckets = create_time_buckets(start, end, "day")

        for i in range(len(buckets) - 1):
            assert buckets[i][1] == buckets[i + 1][0]

    def test_hourly_bucket_end_is_next_hour_start(self):
        """Verify continuous hourly bucket boundaries."""
        start = datetime(2024, 1, 1, 8, 30)
        end = datetime(2024, 1, 1, 16, 15)

        buckets = create_time_buckets(start, end, "hour")

        for i in range(len(buckets) - 1):
            assert buckets[i][1] == buckets[i + 1][0]

    def test_weekly_bucket_end_is_next_week_start(self):
        """Verify continuous weekly bucket boundaries."""
        start = datetime(2024, 1, 5, 14, 0)
        end = datetime(2024, 2, 5, 10, 0)

        buckets = create_time_buckets(start, end, "week")

        for i in range(len(buckets) - 1):
            assert buckets[i][1] == buckets[i + 1][0]

    def test_no_gaps_in_daily_buckets(self):
        """Verify there are no gaps in daily bucket coverage."""
        start = datetime(2024, 3, 15, 10, 30)
        end = datetime(2024, 3, 25, 20, 45)

        buckets = create_time_buckets(start, end, "day")

        # Build a continuous timeline and verify coverage
        current = buckets[0][0]
        for bucket_start, bucket_end in buckets:
            assert current == bucket_start
            current = bucket_end

    def test_bucket_size_consistency(self):
        """Verify that all buckets have consistent size (except possibly the last)."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 10, 12, 0)

        # Test each bucket size
        for size in ["hour", "day", "week"]:
            buckets = create_time_buckets(start, end, size)
            if len(buckets) > 1:
                expected_delta = buckets[0][1] - buckets[0][0]
                for bucket_start, bucket_end in buckets:
                    assert bucket_end - bucket_start == expected_delta
