from datetime import datetime, timedelta
from typing import List, Optional, Union

import pandas as pd

from .clustering import only_target_users
from .study_conf import (Audience, AudienceConf, LookalikeAudience,
                         Partitioning, StudyConf)


def get_users(df) -> List[str]:
    if df is None:
        return []
    return df.user_id.unique().tolist()


def partitioning_view(
    df: pd.DataFrame, part: Partitioning, now: datetime
) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = (
        df.sort_values("timestamp")
        .drop_duplicates("user_id", keep="first")
        .reset_index(drop=True)
    )

    from_time = d.timestamp.iloc[0]
    now_delta = now - from_time
    d["delta"] = d.timestamp - from_time
    d["users"] = d.index.values + 1

    empty = df[df.timestamp < from_time]  # empty
    min_users = d.shape[0] >= part.min_users

    def msk(m):
        return df[df.user_id.isin(d[m].user_id)].reset_index(drop=True)

    if part.scenario == {"min_users"}:
        cutoff = d.users > part.min_users
        if not min_users:
            return empty, df

        return msk(~cutoff), msk(cutoff)

    if part.min_days and part.min_users:
        include = (d.delta <= timedelta(days=part.min_days)) | (
            d.users <= part.min_users
        )

        min_days = now_delta >= timedelta(days=part.min_days)

        if not min_users or not min_days:
            return empty, df

        return msk(include), msk(~include)

    if part.max_days and part.max_users:
        days_mask = d.delta <= timedelta(part.max_days)

        if days_mask.all():
            days_mask = now_delta >= timedelta(days=part.max_days)

        include = days_mask & (d.users <= part.max_users)

        if not min_users:
            return empty, df

        return msk(include), msk(~include)

    raise Exception(f"Impossible partitioning: {part}")


def partition_users(
    df: Optional[pd.DataFrame], aud: AudienceConf, now: datetime
) -> list[pd.DataFrame]:
    partitions: list[pd.DataFrame] = []

    if df is None:
        return partitions

    if not aud.partitioning:
        raise Exception(
            f"Trying to partition users on a non-partitioned Audience: {aud}"
        )

    while True:
        if df.empty:
            return partitions

        a, df = partitioning_view(df, aud.partitioning, now)
        if a.empty:
            return partitions

        partitions.append(a)


def partition_name(aud, i):
    return aud.name + f"-cohort-{i+1}"


# TODO: add context obj for country_code / page_id...
# actually that's kind what Marketing is... !
def hydrate_audience(
    page_ids: list[str], df: pd.DataFrame, aud: AudienceConf, now: datetime
) -> list[Union[Audience, LookalikeAudience]]:
    df = only_target_users(df, aud)

    audiences: list[Union[Audience, LookalikeAudience]] = []
    if aud.subtype == "LOOKALIKE" and aud.lookalike:
        users = get_users(df)
        origin = Audience(name=aud.name + "-origin", page_ids=page_ids, users=users)
        audiences += [origin]

        if len(users) >= aud.lookalike.target:
            audiences += [
                LookalikeAudience(
                    name=aud.name, spec=aud.lookalike.spec, origin_audience=origin
                )
            ]

        return audiences

    if aud.subtype == "CUSTOM":
        users = get_users(df)
        return [Audience(name=aud.name, page_ids=page_ids, users=users)]

    if aud.subtype == "PARTITIONED":
        partitions = partition_users(df, aud, now)

        return [
            Audience(name=partition_name(aud, i), page_ids=page_ids, users=get_users(d))
            for i, d in enumerate(partitions)
        ]

    raise Exception(f"Unsupported audience type: {aud.subtype}")


def hydrate_audiences(
    study: StudyConf, df: pd.DataFrame, auds: List[AudienceConf]
) -> List[Union[Audience, LookalikeAudience]]:
    now = datetime.utcnow()

    # can get pageid from the audience directly... If it needs it?
    # Or should all ads be from the same page by construction?
    page_ids = [
        c.template["actor_id"] for c in study.creatives if c.template is not None
    ]

    return [i for aud in auds for i in hydrate_audience(page_ids, df, aud, now)]
