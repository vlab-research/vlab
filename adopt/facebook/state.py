import logging
import re
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Any, Dict, List, Tuple

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
from facebook_business.session import FacebookSession

from .api import call


class StateNameError(BaseException):
    pass


class StateInitializationError(BaseException):
    pass


#############################
# GET from Facebook API
#############################

epoch = datetime.utcfromtimestamp(0)


def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0


@dataclass
class BudgetWindow:
    start_date: datetime
    until_date: datetime

    @property
    def start(self):
        return self.start_date.strftime("%Y-%m-%d")

    @property
    def until(self):
        return self.until_date.strftime("%Y-%m-%d")

    @property
    def start_unix(self):
        return unix_time_millis(self.start_date)

    @property
    def until_unix(self):
        return unix_time_millis(self.until_date)


#############################
# GET from Facebook API
#############################

# TODO: make fields dynamic based on given desired state...


def get_creatives(api: FacebookAdsApi, ids: List[str]) -> List[AdCreative]:
    if not ids:
        return []

    fields = ["url_tags", "actor_id", "object_story_spec"]
    return call(AdCreative.get_by_ids, ids=ids, fields=fields, api=api)


def get_adsets(campaign: Campaign) -> List[AdSet]:
    return call(
        campaign.get_ad_sets,
        fields=[
            AdSet.Field.name,
            AdSet.Field.status,
            AdSet.Field.targeting,
            AdSet.Field.optimization_goal,
            AdSet.Field.optimization_sub_event,
            AdSet.Field.destination_type,
            AdSet.Field.daily_budget,
            AdSet.Field.end_time,
            AdSet.Field.bid_strategy,
        ],
    )


def get_campaigns(account: AdAccount) -> List[Campaign]:
    return call(account.get_campaigns, fields=["name"])


def get_ads(campaign: Campaign) -> List[Ad]:
    return call(campaign.get_ads, fields=["creative", "adset_id", "status", "name"])


def split(li, N):
    while li:
        head, li = li[:N], li[N:]
        yield head


def get_all_ads(api: FacebookAdsApi, c: Campaign) -> List[Ad]:
    ads = [a for a in get_ads(c)]
    creative_ids = [ad["creative"]["id"] for ad in ads]

    creatives = {
        c["id"]: c for cids in split(creative_ids, 50) for c in get_creatives(api, cids)
    }
    for cid, ad in zip(creative_ids, ads):
        ad["creative"] = creatives[cid]
    return ads


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
    ]

    try:
        return call(adset.get_insights, params=params, fields=fields)[0]
    except IndexError:
        return None


Insights = Dict[str, Any]


def get_insights(adsets, window: BudgetWindow) -> Insights:
    insights = {a["name"]: _get_insights(a, window) for a in adsets}
    return insights


def get_spending(insights: Insights) -> Dict[str, float]:
    spending = lambda i: 0 if i is None else i["spend"]
    spend = {n: spending(i) for n, i in insights.items()}
    spend = {n: float(v) * 100 for n, v in spend.items()}
    return spend


def get_custom_audiences(account: AdAccount) -> List[CustomAudience]:
    fields = [
        CustomAudience.Field.name,
        CustomAudience.Field.description,
        CustomAudience.Field.subtype,
        CustomAudience.Field.time_created,
        CustomAudience.Field.approximate_count,
        CustomAudience.Field.source,
        CustomAudience.Field.lookalike_spec,
        CustomAudience.Field.expectedsize,
    ]

    return call(account.get_custom_audiences, fields=fields)


def ads_for_adset(adset, ads):
    return [a for a in ads if a["adset_id"] == adset["id"]]


def get_api(env, token: str) -> FacebookAdsApi:
    session = FacebookSession(env("FACEBOOK_APP_ID"), env("FACEBOOK_APP_SECRET"), token)
    api = FacebookAdsApi(session)
    return api


class CampaignState:
    def __init__(self, token, api, ad_account_id, campaign_id=None, window=None):
        self.token: str = token
        self.api: FacebookAdsApi = api
        self.campaign_id = campaign_id
        self.window: BudgetWindow = window

        if re.search(r"^act_", ad_account_id):
            raise Exception(
                "initial CampaignState with ad account id without act_ prefix"
            )

        self.account: AdAccount = AdAccount(f"act_{ad_account_id}", api=self.api)

    @cached_property
    def campaigns(self) -> List[Campaign]:
        return get_campaigns(self.account)

    @cached_property
    def campaign(self) -> Campaign:
        name = self.campaign_id
        if name is None:
            raise StateNameError(
                "You must initialize CampaignState with campaign_id "
                "to access Campaign data"
            )
        campaign = next((c for c in self.campaigns if c["name"] == name), None)

        if campaign is None:
            raise StateNameError(f"Could not find a campaign with name: {name}")
        return campaign

    @cached_property
    def adsets(self) -> List[AdSet]:
        adsets = get_adsets(self.campaign)
        logging.info(
            f'Loaded {len(adsets)} adsets from campaign {self.campaign["name"]}'
        )
        return adsets

    @cached_property
    def ads(self) -> List[Ad]:
        ads = get_all_ads(self.api, self.campaign)
        logging.info(f'Loaded {len(ads)} ads from campaign {self.campaign["name"]}')
        return ads

    @cached_property
    def campaign_state(self) -> List[Tuple[AdSet, List[Ad]]]:
        return [(adset, ads_for_adset(adset, self.ads)) for adset in self.adsets]

    @cached_property
    def insights(self) -> Insights:
        if not self.window:
            raise StateInitializationError("Cannot get insights without a window")
        return get_insights(self.adsets, self.window)

    @cached_property
    def spend(self) -> Dict[str, float]:
        return get_spending(self.insights)

    @cached_property
    def total_spend(self) -> float:
        res = call(self.campaign.get_insights, fields=["spend"])
        if not res:
            return 0
        return float(res[0]["spend"])

    @cached_property
    def custom_audiences(self) -> List[CustomAudience]:
        return get_custom_audiences(self.account)

    def get_audience(self, name: str) -> CustomAudience:
        aud = next((a for a in self.custom_audiences if a["name"] == name), None)
        if not aud:

            raise StateNameError(f"Audience not found with name: {name}")
        return aud
