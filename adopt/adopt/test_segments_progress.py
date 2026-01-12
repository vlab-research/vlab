"""
Comprehensive unit tests for segments_progress.py business logic functions.

These tests focus on the pure functions that calculate segment progress metrics,
including user start times, bucket counting, and progress data building.
"""
import pytest
import pandas as pd
from datetime import datetime
from adopt.segments_progress import (
    get_user_start_times,
    count_users_in_bucket,
    build_segments_progress_data,
)


class TestGetUserStartTimes:
    """Test suite for get_user_start_times function."""

    def test_basic_multiple_users_multiple_strata(self):
        """Test basic case with multiple users across multiple strata."""
        df = pd.DataFrame({
            'user_id': ['u1', 'u1', 'u2', 'u2'],
            'cluster': ['s1', 's1', 's2', 's2'],
            'timestamp': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 11, 0),
                datetime(2024, 1, 2, 10, 0),
                datetime(2024, 1, 2, 11, 0),
            ]
        })
        result = get_user_start_times(df)

        assert len(result) == 2
        assert set(result.columns) == {'user_id', 'stratum_id', 'start_time'}

        # Check u1 gets the earliest timestamp
        u1_row = result[result.user_id == 'u1'].iloc[0]
        assert u1_row.start_time == datetime(2024, 1, 1, 10, 0)
        assert u1_row.stratum_id == 's1'

        # Check u2 gets the earliest timestamp
        u2_row = result[result.user_id == 'u2'].iloc[0]
        assert u2_row.start_time == datetime(2024, 1, 2, 10, 0)
        assert u2_row.stratum_id == 's2'

    def test_user_appears_in_multiple_strata(self):
        """Test that users appearing in multiple strata get separate entries with min timestamp per stratum."""
        df = pd.DataFrame({
            'user_id': ['u1', 'u1', 'u1', 'u1'],
            'cluster': ['s1', 's1', 's2', 's2'],
            'timestamp': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 12, 0),
                datetime(2024, 1, 2, 14, 0),
                datetime(2024, 1, 2, 16, 0),
            ]
        })
        result = get_user_start_times(df)

        # Should have 2 rows - one for each stratum
        assert len(result) == 2

        # Check s1 entry
        s1_row = result[result.stratum_id == 's1'].iloc[0]
        assert s1_row.user_id == 'u1'
        assert s1_row.start_time == datetime(2024, 1, 1, 10, 0)

        # Check s2 entry
        s2_row = result[result.stratum_id == 's2'].iloc[0]
        assert s2_row.user_id == 'u1'
        assert s2_row.start_time == datetime(2024, 1, 2, 14, 0)

    def test_empty_dataframe(self):
        """Test that empty DataFrame returns empty result."""
        df = pd.DataFrame({
            'user_id': [],
            'cluster': [],
            'timestamp': []
        })
        result = get_user_start_times(df)

        assert len(result) == 0
        assert set(result.columns) == {'user_id', 'stratum_id', 'start_time'}

    def test_single_user_single_stratum(self):
        """Test with single user in single stratum."""
        df = pd.DataFrame({
            'user_id': ['u1'],
            'cluster': ['s1'],
            'timestamp': [datetime(2024, 1, 1, 10, 0)]
        })
        result = get_user_start_times(df)

        assert len(result) == 1
        assert result.iloc[0].user_id == 'u1'
        assert result.iloc[0].stratum_id == 's1'
        assert result.iloc[0].start_time == datetime(2024, 1, 1, 10, 0)

    def test_multiple_users_same_stratum(self):
        """Test multiple users in the same stratum get individual entries."""
        df = pd.DataFrame({
            'user_id': ['u1', 'u1', 'u2', 'u2', 'u3'],
            'cluster': ['s1', 's1', 's1', 's1', 's1'],
            'timestamp': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 12, 0),
                datetime(2024, 1, 2, 10, 0),
                datetime(2024, 1, 2, 12, 0),
                datetime(2024, 1, 3, 10, 0),
            ]
        })
        result = get_user_start_times(df)

        assert len(result) == 3
        assert set(result.user_id) == {'u1', 'u2', 'u3'}
        assert all(result.stratum_id == 's1')


class TestCountUsersInBucket:
    """Test suite for count_users_in_bucket function."""

    def test_users_within_bucket(self):
        """Test counting users whose start time falls within the bucket."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2', 'u3'],
            'stratum_id': ['s1', 's1', 's2'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 11, 0),
                datetime(2024, 1, 1, 12, 0),
            ]
        })
        bucket_start = datetime(2024, 1, 1, 0, 0)
        bucket_end = datetime(2024, 1, 2, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {'s1': 2, 's2': 1}

    def test_no_users_in_bucket(self):
        """Test that empty bucket returns empty dict."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2'],
            'stratum_id': ['s1', 's2'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 11, 0),
            ]
        })
        bucket_start = datetime(2024, 1, 5, 0, 0)
        bucket_end = datetime(2024, 1, 6, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {}

    def test_bucket_boundary_start_inclusive(self):
        """Test that bucket start is inclusive."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1'],
            'stratum_id': ['s1'],
            'start_time': [datetime(2024, 1, 1, 0, 0)]
        })
        bucket_start = datetime(2024, 1, 1, 0, 0)
        bucket_end = datetime(2024, 1, 2, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {'s1': 1}

    def test_bucket_boundary_end_exclusive(self):
        """Test that bucket end is exclusive."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1'],
            'stratum_id': ['s1'],
            'start_time': [datetime(2024, 1, 2, 0, 0)]
        })
        bucket_start = datetime(2024, 1, 1, 0, 0)
        bucket_end = datetime(2024, 1, 2, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {}

    def test_multiple_strata_with_different_counts(self):
        """Test multiple strata with varying user counts."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2', 'u3', 'u4', 'u5'],
            'stratum_id': ['s1', 's1', 's1', 's2', 's3'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 11, 0),
                datetime(2024, 1, 1, 12, 0),
                datetime(2024, 1, 1, 13, 0),
                datetime(2024, 1, 1, 14, 0),
            ]
        })
        bucket_start = datetime(2024, 1, 1, 0, 0)
        bucket_end = datetime(2024, 1, 2, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {'s1': 3, 's2': 1, 's3': 1}

    def test_empty_user_start_times(self):
        """Test with empty user_start_times DataFrame."""
        user_start_times = pd.DataFrame({
            'user_id': [],
            'stratum_id': [],
            'start_time': []
        })
        bucket_start = datetime(2024, 1, 1, 0, 0)
        bucket_end = datetime(2024, 1, 2, 0, 0)

        result = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        assert result == {}

class TestBuildSegmentsProgressData:
    """Test suite for build_segments_progress_data function."""

    @pytest.fixture
    def sample_strata(self):
        """Create sample strata IDs for testing."""
        return ["s1", "s2"]

    def test_full_integration_multiple_buckets_multiple_strata(self, sample_strata):
        """Test full integration with multiple buckets and strata."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2', 'u3', 'u4'],
            'stratum_id': ['s1', 's1', 's2', 's2'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 2, 10, 0),
                datetime(2024, 1, 1, 11, 0),
                datetime(2024, 1, 3, 11, 0),
            ]
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
            (datetime(2024, 1, 2, 0, 0), datetime(2024, 1, 3, 0, 0)),
            (datetime(2024, 1, 3, 0, 0), datetime(2024, 1, 4, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        # Should have 3 buckets
        assert len(result) == 3

        # First bucket: u1 (s1), u3 (s2)
        bucket1 = result[0]
        assert bucket1["datetime"] == int(datetime(2024, 1, 1, 0, 0).timestamp() * 1000)
        assert len(bucket1["segments"]) == 2
        s1_seg = next(s for s in bucket1["segments"] if s["id"] == "s1")
        s2_seg = next(s for s in bucket1["segments"] if s["id"] == "s2")
        assert s1_seg["participants"] == 1
        assert s2_seg["participants"] == 1
        assert bucket1["totalParticipants"] == 2

        # Second bucket: cumulative s1=2, s2=1
        bucket2 = result[1]
        s1_seg = next(s for s in bucket2["segments"] if s["id"] == "s1")
        s2_seg = next(s for s in bucket2["segments"] if s["id"] == "s2")
        assert s1_seg["participants"] == 2
        assert s2_seg["participants"] == 1
        assert bucket2["totalParticipants"] == 3

        # Third bucket: cumulative s1=2, s2=2
        bucket3 = result[2]
        s1_seg = next(s for s in bucket3["segments"] if s["id"] == "s1")
        s2_seg = next(s for s in bucket3["segments"] if s["id"] == "s2")
        assert s1_seg["participants"] == 2
        assert s2_seg["participants"] == 2
        assert bucket3["totalParticipants"] == 4

    def test_cumulative_counting_works_correctly(self, sample_strata):
        """Test that cumulative counting accumulates properly across buckets."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2', 'u3'],
            'stratum_id': ['s1', 's1', 's1'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 2, 10, 0),
                datetime(2024, 1, 3, 10, 0),
            ]
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
            (datetime(2024, 1, 2, 0, 0), datetime(2024, 1, 3, 0, 0)),
            (datetime(2024, 1, 3, 0, 0), datetime(2024, 1, 4, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        # Verify cumulative counts increase
        s1_counts = [
            next(s for s in bucket["segments"] if s["id"] == "s1")["participants"]
            for bucket in result
        ]
        assert s1_counts == [1, 2, 3]

    def test_empty_user_start_times_returns_zero_counts(self, sample_strata):
        """Test that empty user_start_times results in zero participant counts."""
        user_start_times = pd.DataFrame({
            'user_id': [],
            'stratum_id': [],
            'start_time': []
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        # Should still have bucket structure but with zero counts
        assert len(result) == 1
        assert len(result[0]["segments"]) == 2
        for segment in result[0]["segments"]:
            assert segment["participants"] == 0
        assert result[0]["totalParticipants"] == 0

    def test_single_bucket_single_stratum(self):
        """Test minimal case with one bucket and one stratum."""
        strata_ids = ["s1"]
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2'],
            'stratum_id': ['s1', 's1'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 11, 0),
            ]
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            strata_ids,
        )

        assert len(result) == 1
        assert len(result[0]["segments"]) == 1
        assert result[0]["segments"][0]["id"] == "s1"
        assert result[0]["segments"][0]["participants"] == 2
        assert result[0]["totalParticipants"] == 2

    def test_bucket_structure_includes_datetime_and_segments(self, sample_strata):
        """Test that each bucket has correct datetime and segments structure."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1'],
            'stratum_id': ['s1'],
            'start_time': [datetime(2024, 1, 1, 10, 0)]
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        assert len(result) == 1
        bucket = result[0]

        # Check required top-level keys
        assert "datetime" in bucket
        assert "totalParticipants" in bucket
        assert "segments" in bucket

        # Check datetime format (milliseconds timestamp)
        expected_ms = int(datetime(2024, 1, 1, 0, 0).timestamp() * 1000)
        assert bucket["datetime"] == expected_ms

        # Check segments structure
        for segment in bucket["segments"]:
            assert "id" in segment
            assert "participants" in segment
            assert isinstance(segment["id"], str)
            assert isinstance(segment["participants"], int)

    def test_segments_include_all_strata(self, sample_strata):
        """Test that all strata are represented in segment output even with zero participants."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1'],
            'stratum_id': ['s1'],  # Only s1 has participants
            'start_time': [datetime(2024, 1, 1, 10, 0)]
        })
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        # Both strata should be present
        segment_ids = {s["id"] for s in result[0]["segments"]}
        assert segment_ids == {"s1", "s2"}

        # s1 should have 1 participant, s2 should have 0
        s1_seg = next(s for s in result[0]["segments"] if s["id"] == "s1")
        s2_seg = next(s for s in result[0]["segments"] if s["id"] == "s2")
        assert s1_seg["participants"] == 1
        assert s2_seg["participants"] == 0

    def test_multiple_buckets_empty_buckets(self, sample_strata):
        """Test handling of empty buckets in the middle of the time series."""
        user_start_times = pd.DataFrame({
            'user_id': ['u1', 'u2'],
            'stratum_id': ['s1', 's1'],
            'start_time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 3, 10, 0),
            ]
        })
        # Middle bucket (day 2) has no users
        buckets = [
            (datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 2, 0, 0)),
            (datetime(2024, 1, 2, 0, 0), datetime(2024, 1, 3, 0, 0)),  # Empty bucket
            (datetime(2024, 1, 3, 0, 0), datetime(2024, 1, 4, 0, 0)),
        ]

        result = build_segments_progress_data(
            user_start_times,
            buckets,
            sample_strata,
        )

        # Verify cumulative counts remain same in empty bucket
        s1_counts = [
            next(s for s in bucket["segments"] if s["id"] == "s1")["participants"]
            for bucket in result
        ]
        # Should go 1, 1, 2 (empty bucket maintains cumulative, then adds new user)
        assert s1_counts == [1, 1, 2]
