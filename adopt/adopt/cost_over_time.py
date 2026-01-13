"""Cost over time calculations for recruitment analytics."""

from datetime import datetime, date
from typing import Optional
import pandas as pd


def count_new_respondents_by_day(
    user_start_times: pd.DataFrame,
) -> dict[date, int]:
    """
    Count new respondents per day from user start times.

    Args:
        user_start_times: DataFrame with columns [user_id, stratum_id, start_time]

    Returns:
        Dict mapping date -> count of new respondents that day
    """
    if user_start_times.empty:
        return {}

    df = user_start_times.copy()
    df['date'] = df['start_time'].dt.date

    # Count unique users per day (user can only be "new" once)
    daily_counts = df.groupby('date')['user_id'].nunique()
    return daily_counts.to_dict()


def calculate_cost_over_time(
    spend_by_day: list[dict],
    new_respondents_by_day: dict[date, int],
    incentive_per_respondent: float,
) -> list[dict]:
    """
    Calculate cumulative spend and marginal cost per respondent for each day.

    IMPORTANT: cumulativeSpend includes BOTH ad spend AND incentives, per Director's recommendation.

    Args:
        spend_by_day: List of {"date": date, "spend": float} dicts from recruitment data
        new_respondents_by_day: Dict mapping date -> count of new respondents
        incentive_per_respondent: Cost of incentive per respondent

    Returns:
        List of:
        {
            "datetime": int (ms timestamp),
            "cumulativeSpend": float,  # Includes both ad spend AND incentives
            "cumulativeRespondents": int,
            "marginalCost": float | None,  # None if no new respondents that day
            "newRespondents": int,
            "dailySpend": float,
        }
    """
    # Get all dates from both sources
    spend_dates = {d["date"] for d in spend_by_day}
    respondent_dates = set(new_respondents_by_day.keys())
    all_dates = sorted(spend_dates | respondent_dates)

    if not all_dates:
        return []

    # Build lookup for spend
    spend_lookup = {d["date"]: d["spend"] for d in spend_by_day}

    result = []
    cumulative_spend = 0.0
    cumulative_respondents = 0

    for day in all_dates:
        daily_spend = spend_lookup.get(day, 0.0)
        new_respondents = new_respondents_by_day.get(day, 0)

        # Calculate daily incentive cost
        daily_incentive = new_respondents * incentive_per_respondent
        daily_total = daily_spend + daily_incentive

        # Update cumulative values (include BOTH ad spend AND incentives)
        cumulative_spend += daily_total
        cumulative_respondents += new_respondents

        # Marginal cost (None if no new respondents to avoid division by zero)
        marginal_cost = None
        if new_respondents > 0:
            marginal_cost = daily_total / new_respondents

        # Convert date to millisecond timestamp
        dt = datetime.combine(day, datetime.min.time())
        timestamp_ms = int(dt.timestamp() * 1000)

        result.append({
            "datetime": timestamp_ms,
            "cumulativeSpend": cumulative_spend,
            "cumulativeRespondents": cumulative_respondents,
            "marginalCost": marginal_cost,
            "newRespondents": new_respondents,
            "dailySpend": daily_spend,
        })

    return result
