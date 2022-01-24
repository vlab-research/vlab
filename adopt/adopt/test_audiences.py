from datetime import datetime

import pandas as pd
import pytest

from .audiences import hydrate_audience, partition_users, partitioning_view
from .marketing import AudienceConf, Lookalike, LookalikeSpec, Partitioning

# integration test
# works with empty list


def _responses(data):
    cols = ["variable", "value", "user_id", "timestamp"]
    return pd.DataFrame(data, columns=cols)


def _resp(ref, response, userid, day, hour=None):
    now = datetime.utcnow()

    if hour is None:
        hour = now.hour

    ts = pd.Timestamp(
        datetime(2021, 1, day, hour, now.minute, now.second, now.microsecond)
    )
    return (
        ref,
        response,
        userid,
        ts,
    )


def test_partitioning_view_min_users_when_not_past():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
        ]
    )
    now = datetime(2021, 1, 4)

    part = Partitioning(min_users=4)
    a, b = partitioning_view(df, part, now)
    assert a.empty
    assert b.equals(df)


def test_partitioning_view_min_users_when_past():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
        ]
    )
    now = datetime(2021, 1, 4)

    part = Partitioning(min_users=3)
    a, b = partitioning_view(df, part, now)
    assert a.equals(df)
    assert b.empty

    part = Partitioning(min_users=2)
    a, b = partitioning_view(df, part, now)
    assert a.shape[0] == 3  # first two users
    assert set(a.user_id.tolist()) == {"foo", "bar"}
    assert b.shape[0] == 1  # last user
    assert set(b.user_id.tolist()) == {"baz"}


def test_partitioning_view_min_users_min_days_when_not_past_now():
    now = datetime(2021, 1, 4)

    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 3, 23),
        ]
    )

    part = Partitioning(min_users=2, min_days=3)
    a, b = partitioning_view(df, part, now)
    assert a.empty
    assert b.equals(df)


def test_partitioning_view_min_users_min_days_when_past_now_but_not_enough_users():
    now = datetime(2021, 1, 4)

    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
        ]
    )

    part = Partitioning(min_users=3, min_days=2)
    a, b = partitioning_view(df, part, now)
    assert a.empty
    assert b.equals(df)


def test_partitioning_view_min_users_min_days_when_past_users_but_many_days():
    now = datetime(2021, 1, 6)

    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 4),
            _resp("one", "yes", "baz", 5),
            _resp("one", "yes", "qux", 5),
            _resp("one", "yes", "quxx", 5),
        ]
    )

    part = Partitioning(min_users=4, min_days=2)
    a, b = partitioning_view(df, part, now)
    assert a.shape[0] == 5
    assert set(a.user_id.tolist()) == {"foo", "bar", "baz", "qux"}
    assert b.shape[0] == 1
    assert set(b.user_id.tolist()) == {"quxx"}


def test_partitioning_view_min_users_min_days_when_past():
    now = datetime(2021, 1, 6)

    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 4),
            _resp("one", "yes", "baz", 5),
        ]
    )

    part = Partitioning(min_users=2, min_days=2)
    a, b = partitioning_view(df, part, now)
    assert a.shape[0] == 3
    assert set(a.user_id.tolist()) == {"foo", "bar"}
    assert b.shape[0] == 1
    assert set(b.user_id.tolist()) == {"baz"}


def test_partitioning_view_min_users_max_days_max_users_when_past_days_now():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
        ]
    )

    now = datetime(2021, 1, 4)

    part = Partitioning(min_users=1, max_days=2, max_users=10)
    a, b = partitioning_view(df, part, now)
    assert a.shape[0] == 2
    assert set(a.user_id.tolist()) == {"foo"}
    assert b.shape[0] == 0


def test_partitioning_view_min_users_max_days_max_users_when_not_min_users():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
        ]
    )

    now = datetime(2021, 1, 4)
    part = Partitioning(min_users=2, max_days=2, max_users=10)
    a, b = partitioning_view(df, part, now)
    assert a.empty
    assert b.equals(df)


def test_partitioning_view_min_users_max_days_max_users_when_past_days():

    df = _responses(
        [
            _resp("one", "yes", "foo", 1, 0),
            _resp("two", "yes", "bar", 2, 23),
            _resp("two", "yes", "baz", 3, 1),  # slightly more than 2 days.
        ]
    )

    now = datetime(2021, 1, 4)

    part = Partitioning(min_users=2, max_days=2, max_users=10)
    a, b = partitioning_view(df, part, now)
    assert a.shape[0] == 2
    assert set(a.user_id.tolist()) == {"foo", "bar"}
    assert b.shape[0] == 1
    assert set(b.user_id.tolist()) == {"baz"}


def test_partition_users_partitions_by_user_ignores_extra():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
            _resp("one", "yes", "qux", 5),
            _resp("one", "yes", "quxx", 6),
        ]
    )
    now = datetime(2021, 1, 10)

    part = Partitioning(min_users=2)
    conf = AudienceConf("foo", "PARTITIONED", partitioning=part)
    dfs = partition_users(df, conf, now)
    assert len(dfs) == 2
    assert dfs[0].equals(df.iloc[:3])
    assert dfs[1].equals(df.iloc[3:5].reset_index(drop=True))


def test_partition_users_partitions_by_user_when_they_perfectly_fit():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
            _resp("one", "yes", "qux", 5),
        ]
    )
    now = datetime(2021, 1, 4)

    part = Partitioning(min_users=2)
    conf = AudienceConf("foo", "PARTITIONED", partitioning=part)
    dfs = partition_users(df, conf, now)
    assert len(dfs) == 2
    assert dfs[0].equals(df.iloc[:3])
    assert dfs[1].equals(df.iloc[3:].reset_index(drop=True))


# if not target reached, don't create lookalike audience
def test_hydrate_audience_creates_partitioned_audiences():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
            _resp("one", "yes", "qux", 5),
        ]
    )
    now = datetime(2021, 1, 4)
    part = Partitioning(min_users=2)

    conf = AudienceConf("foo", "PARTITIONED", partitioning=part)
    audiences = hydrate_audience("page", df, conf, now)

    assert len(audiences) == 2
    assert audiences[0].name == "foo-cohort-1"
    assert audiences[1].name == "foo-cohort-2"


def test_hydrate_users_works_when_no_users_for_any_type():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
        ]
    )

    now = datetime(2021, 1, 4)
    part = Partitioning(min_users=2)
    conf = AudienceConf("foo", "PARTITIONED", partitioning=part)
    audiences = hydrate_audience("page", df, conf, now)
    assert len(audiences) == 0

    lookalike = Lookalike(4, LookalikeSpec("IN", 0.1, 0.0))
    conf = AudienceConf(
        name="foo-lookalike",
        subtype="LOOKALIKE",
        lookalike=lookalike,
    )

    audiences = hydrate_audience("page", df, conf, now)
    assert len(audiences) == 1

    conf = AudienceConf(name="foo", subtype="CUSTOM")
    audiences = hydrate_audience("page", df, conf, now)
    assert len(audiences) == 1


def test_hydrate_audience_creates_audience_and_lookalike_if_enough_users():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
            _resp("one", "yes", "qux", 5),
        ]
    )
    now = datetime(2021, 1, 4)

    lookalike = Lookalike(4, LookalikeSpec("IN", 0.1, 0.0))
    conf = AudienceConf(
        name="foo-lookalike",
        subtype="LOOKALIKE",
        lookalike=lookalike,
    )

    audiences = hydrate_audience("page", df, conf, now)

    assert len(audiences) == 2
    assert audiences[0].name == "foo-lookalike-origin"
    assert audiences[1].name == "foo-lookalike"


def test_hydrate_audience_creates_no_lookalike_if_not_enough_users():
    df = _responses(
        [
            _resp("one", "yes", "foo", 1),
            _resp("two", "yes", "foo", 1),
            _resp("one", "yes", "bar", 3),
            _resp("one", "yes", "baz", 4),
        ]
    )
    now = datetime(2021, 1, 4)

    lookalike = Lookalike(4, LookalikeSpec("IN", 0.1, 0.0))
    conf = AudienceConf(
        name="foo-lookalike",
        subtype="LOOKALIKE",
        lookalike=lookalike,
    )

    audiences = hydrate_audience("page", df, conf, now)

    assert len(audiences) == 1
    assert audiences[0].name == "foo-lookalike-origin"
