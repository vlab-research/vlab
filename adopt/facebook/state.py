import logging
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Any, Dict, List, Optional

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adlabel import AdLabel
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi

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
def get_campaign(account: AdAccount, name: str) -> Optional[Campaign]:
    campaigns = call(account.get_campaigns, {}, ["name"])
    c = next((c for c in campaigns if c["name"] == name), None)
    return c


def get_creatives(account: AdAccount, ad_label_id: str) -> List[AdCreative]:
    # loads ALL creatives for account...
    # how many API requests does that count as???
    fields = ["name", "url_tags", "actor_id", "object_story_spec"]
    params = {"ad_label_ids": [ad_label_id]}

    return call(account.get_ad_creatives_by_labels, params, fields)


def get_adsets(campaign: Campaign) -> List[AdSet]:
    return call(
        campaign.get_ad_sets,
        {},
        [
            "name",
            "status",
            "targeting",
            "optimization_goal",
            "optimization_sub_event",
            "destination_type",
        ],
    )


def get_ads(adset: AdSet) -> List[Ad]:
    return call(adset.get_ads, {}, ["creative", "adset_id", "status"])


def get_all_ads(adsets: List[AdSet]) -> List[Ad]:
    return [a for s in adsets for a in get_ads(s)]


def get_label(account: AdAccount, name: str):
    return call(account.create_ad_label, {"name": name}, [])


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


def get_account(env, token):
    cnf = {
        "APP_ID": env("FACEBOOK_APP_ID"),
        "APP_SECRET": env("FACEBOOK_APP_SECRET"),
        "USER_TOKEN": token,
        "AD_ACCOUNT": f'act_{env("FACEBOOK_AD_ACCOUNT")}',
    }

    FacebookAdsApi.init(cnf["APP_ID"], cnf["APP_SECRET"], cnf["USER_TOKEN"])
    return AdAccount(cnf["AD_ACCOUNT"])


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

    return call(account.get_custom_audiences, {}, fields)


class CampaignState:
    def __init__(self, env, token, window=None):
        cnf = {
            "PAGE_ID": env("FACEBOOK_PAGE_ID"),
            "INSTA_ID": env("FACEBOOK_INSTA_ID"),
            "CAMPAIGN": env("FACEBOOK_AD_CAMPAIGN"),
            "AD_LABEL": env("FACEBOOK_AD_LABEL"),
        }

        self.cnf = cnf
        self.window: BudgetWindow = window
        self.account: AdAccount = get_account(env, token)

    @cached_property
    def label(self) -> AdLabel:
        return get_label(self.account, self.cnf["AD_LABEL"])

    @cached_property
    def campaign(self) -> Campaign:
        name = self.cnf["CAMPAIGN"]
        campaign = get_campaign(self.account, name)

        if campaign is None:
            raise StateNameError(f"Could not find a campaign with name: {name}")
        return campaign

    @cached_property
    def creatives(self) -> List[AdCreative]:
        creatives = get_creatives(self.account, self.label["id"])
        logging.info(f'Loaded {len(creatives)} creatives with label {self.label["id"]}')
        return creatives

    @cached_property
    def adsets(self) -> List[AdSet]:
        adsets = get_adsets(self.campaign)
        logging.info(
            f'Loaded {len(adsets)} adsets from campaign {self.campaign["name"]}'
        )
        return adsets

    @cached_property
    def ads(self) -> List[Ad]:
        return get_all_ads(self.adsets)

    @cached_property
    def insights(self) -> Insights:
        if not self.window:
            raise StateInitializationError("Cannot get insights without a window")
        return get_insights(self.adsets, self.window)

    @cached_property
    def spend(self) -> Dict[str, float]:
        return get_spending(self.insights)

    @cached_property
    def custom_audiences(self) -> List[CustomAudience]:
        return get_custom_audiences(self.account)

    def get_audience(self, name: str) -> CustomAudience:
        aud = next((a for a in self.custom_audiences if a["name"] == name), None)
        if not aud:

            raise StateNameError(f"Audience not found with name: {name}")
        return aud
