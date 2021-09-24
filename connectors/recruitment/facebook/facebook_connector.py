# TODO: extract "call" to be reused across libs/apps
from datetime import datetime
from typing import Any, Dict, NamedTuple, Sequence

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign

from date_range import DateRange

# TODO: move to "types" and keep in sync
# with Go versions.
Insights = Dict[str, Any]
Stratum = str  # stratum id of some sort


class TimePeriod(NamedTuple):
    start: datetime
    end: datetime


class RecruitmentDataEvent(NamedTuple):
    study_id: str
    source: str
    integrity: int
    time_period: TimePeriod
    data: Dict[Stratum, Insights]


def _get_insights(adset, window):
    params = {"time_range": {"since": window.start, "until": window.until}}
    fields = [
        "unique_link_clicks_ctr",
        "unique_ctr",
        "ctr",
        "cpp",
        "cpm",
        "cpc",
        "unique_clicks",
        "reach",
        "spend",
        "actions",
        "frequency",
    ]

    try:
        return call(adset.get_insights, params=params, fields=fields)[0]
    except IndexError:
        return None


# TODO: remove from here, move to Facebook RecruitmentData connector
def get_insights(adsets: Sequence[AdSet], window: DateRange) -> Insights:
    insights = {a["name"]: _get_insights(a, window) for a in adsets}
    return insights


def get_adsets(account: AdAccount, study_mapping) -> Sequence[AdSet]:
    # adopt needs to either persist this study_mapping or expose it
    # as a shared library or via API...
    # It's a map of stratumids and their corresponding campaign + adset name
    # use the same idea of getting campaign/adset by name and throw
    # if there are multiple (eventually this should be a uesr-specific error)

    # maybe worth depending on facebook_ad_state for some of this...
    pass


account = AdAccount(f"act_{ad_account_id}", api=api)
#
# get window from config

# get stratum ids from config
# map stratumids to adsets -- how?? For each stratum id created,
# I need to know the campaign and adset the corresponds.
# previously I just used name of adset and there was only one campaign,
# but no longer.

# get_insights(adsets, window)
# format insights as RecruitmentDataEvent

# publish
