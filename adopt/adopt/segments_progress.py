"""
Business logic for segments progress calculations.

This module contains pure functions for tracking participant counts over time
per segment/stratum. All functions are pure (no side effects, no I/O) for
testability and reusability.
"""

from datetime import datetime

import pandas as pd

def get_user_start_times(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get the first timestamp per user grouped by stratum.

    This determines when each user "joined" a particular stratum by finding
    their earliest interaction timestamp in that stratum.

    Args:
        filtered_df: DataFrame with columns user_id, cluster, timestamp
                    (output of prep_df_for_budget)

    Returns:
        DataFrame with columns: user_id, stratum_id, start_time
        Each row represents a user's first interaction in a specific stratum.
    """
    return (
        filtered_df.groupby(['user_id', 'cluster'])
        .agg({'timestamp': 'min'})
        .reset_index()
        .rename(columns={'timestamp': 'start_time', 'cluster': 'stratum_id'})
    )


def count_users_in_bucket(
    user_start_times: pd.DataFrame,
    bucket_start: datetime,
    bucket_end: datetime
) -> dict[str, int]:
    """
    Count new users per stratum within a time bucket.

    Identifies users whose first interaction in each stratum occurred
    within the specified time range.

    Args:
        user_start_times: DataFrame with columns user_id, stratum_id, start_time
        bucket_start: Start of the time bucket (inclusive)
        bucket_end: End of the time bucket (exclusive)

    Returns:
        Dictionary mapping stratum_id -> count of new users in this bucket
    """
    bucket_data = user_start_times[
        (user_start_times.start_time >= bucket_start) &
        (user_start_times.start_time < bucket_end)
    ]
    return bucket_data.groupby('stratum_id').user_id.nunique().to_dict()


def build_segments_progress_data(
    user_start_times: pd.DataFrame,
    buckets: list[tuple[datetime, datetime]],
    strata_ids: list[str],
) -> list[dict]:
    """
    Build respondents over time data.

    This function:
    1. Iterates through time buckets
    2. Calculates cumulative participant counts per segment
    3. Returns time-series data with participant counts

    Args:
        user_start_times: DataFrame with user_id, stratum_id, start_time
                         (output of get_user_start_times)
        buckets: List of (start, end) datetime tuples for time buckets
        strata_ids: List of stratum IDs to track

    Returns:
        List of dictionaries with structure:
        [
            {
                "datetime": int (milliseconds timestamp),
                "totalParticipants": int (sum across all segments),
                "segments": [
                    {"id": str, "participants": int},
                    ...
                ]
            },
            ...
        ]
    """
    # Initialize cumulative counts for each stratum
    cumulative_counts = {sid: 0 for sid in strata_ids}
    result = []

    for bucket_start, bucket_end in buckets:
        # Count new users in this bucket
        new_counts = count_users_in_bucket(user_start_times, bucket_start, bucket_end)

        # Update cumulative counts
        for stratum_id, count in new_counts.items():
            if stratum_id in cumulative_counts:
                cumulative_counts[stratum_id] += count

        # Build segment data
        segments = [
            {"id": sid, "participants": cumulative_counts[sid]}
            for sid in strata_ids
        ]

        total = sum(seg["participants"] for seg in segments)

        result.append({
            "datetime": int(bucket_start.timestamp() * 1000),
            "totalParticipants": total,
            "segments": segments,
        })

    return result
