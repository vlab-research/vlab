import logging
import re
from datetime import datetime, timedelta, timezone
from functools import cache, cached_property
from typing import List, Optional, Tuple

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
from facebook_business.session import FacebookSession

from .api import call
from .date_range import DateRange


class StateNameError(BaseException):
    pass


class StateInitializationError(BaseException):
    pass


#############################
# GET from Facebook API
#############################

# TODO: make fields dynamic based on given desired state...


def get_creatives(api: FacebookAdsApi, ids: List[str]) -> List[AdCreative]:
    if not ids:
        return []

    fields = [
        "url_tags",
        "actor_id",
        "instagram_actor_id",
        "object_story_spec",
        "link_deep_link_url",
    ]
    return call(AdCreative.get_by_ids, ids=ids, fields=fields, api=api)


def get_adsets(campaign: Campaign) -> List[AdSet]:
    return call(
        campaign.get_ad_sets,
        fields=[
            AdSet.Field.name,
            AdSet.Field.instagram_actor_id,
            AdSet.Field.status,
            AdSet.Field.targeting,
            AdSet.Field.optimization_goal,
            AdSet.Field.optimization_sub_event,
            AdSet.Field.destination_type,
            AdSet.Field.daily_budget,
            AdSet.Field.end_time,
            AdSet.Field.bid_strategy,
            AdSet.Field.promoted_object,
        ],
    )


def get_campaigns(account: AdAccount) -> List[Campaign]:
    return call(
        account.get_campaigns,
        fields=[
            Campaign.Field.name,
            Campaign.Field.objective,
            Campaign.Field.status,
            Campaign.Field.created_time,
        ],
    )


def get_ads(campaign: Campaign) -> List[Ad]:
    return call(
        campaign.get_ads,
        fields=[
            Ad.Field.creative,
            Ad.Field.adset_id,
            Ad.Field.status,
            Ad.Field.name,
            Ad.Field.effective_status,
        ],
    )


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


def _get_insights(adset, window) -> Optional[dict]:
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
        ai = call(adset.get_insights, params=params, fields=fields)[0]
        return ai.export_all_data()
    except IndexError:
        return None


# def get_daily_insights(
#     adsets: list[AdSet], start: date, end: date
# ) -> dict[date, dict[str, Any]]:

#     days = get_past_days(start, end)
#     return {day: get_insights(adsets, DateRange(day, day)) for day in days}


# TODO: remove from here, adopt should know how to get spend
# from stored RecruitmentData
# def get_spending(insights: Insights) -> Dict[str, float]:
#     spending = lambda i: 0 if i is None else i["spend"]
#     spend = {n: spending(i) for n, i in insights.items()}
#     spend = {n: float(v) * 100 for n, v in spend.items()}
#     return spend

# daily_insights
# create daily insights from campaign start to now.
# make "temp" true/false flag


def get_custom_audiences(account: AdAccount) -> List[CustomAudience]:
    fields = [
        CustomAudience.Field.name,
        CustomAudience.Field.description,
        CustomAudience.Field.subtype,
        CustomAudience.Field.time_created,
        CustomAudience.Field.time_updated,
        CustomAudience.Field.lookalike_spec,
    ]

    return call(account.get_custom_audiences, fields=fields)


def ads_for_adset(adset, ads):
    return [a for a in ads if a["adset_id"] == adset["id"]]


def get_api(env, token: str) -> FacebookAdsApi:
    session = FacebookSession(env("FACEBOOK_APP_ID"), env("FACEBOOK_APP_SECRET"), token)
    api = FacebookAdsApi(session)
    return api


class CampaignState:
    def __init__(
        self,
        facebook_state: "FacebookState",
        api: FacebookAdsApi,
        account: AdAccount,
        campaign_name: str,
    ):
        self.facebook_state = facebook_state
        self.campaign_name = campaign_name
        self.api = api
        self.account = account

    @cached_property
    def campaign(self) -> Campaign:
        name = self.campaign_name

        campaign_options = [c for c in get_campaigns(self.account) if c["name"] == name]

        if len(campaign_options) != 1:
            raise StateNameError(
                f"Phooey! No clear campaign to get for campaign: {self.campaign_name}."
            )

        campaign = campaign_options[0]
        return campaign

    @property
    def campaign_start(self) -> datetime:
        return datetime.strptime(
            self.campaign["created_time"], "%Y-%m-%dT%H:%M:%S%z"
        ).astimezone(timezone.utc)

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

    # TODO: change stupid name and nail down type.
    @cached_property
    def campaign_state(self) -> List[Tuple[AdSet, List[Ad]]]:
        return [(adset, ads_for_adset(adset, self.ads)) for adset in self.adsets]

    @cached_property
    def total_spend(self) -> float:
        # total time window
        window = DateRange(datetime.utcnow() - timedelta(days=365), datetime.utcnow())
        params = {"time_range": {"since": window.start, "until": window.until}}
        res = call(self.campaign.get_insights, params=params, fields=["spend"])
        if not res:
            return 0
        return float(res[0]["spend"])

    def get_insights(self, start: datetime, end: datetime) -> dict[str, Optional[dict]]:
        window = DateRange(start, end)
        insights = {a["name"]: _get_insights(a, window) for a in self.adsets}
        return insights


class FacebookState:
    def __init__(
        self, api: FacebookAdsApi, ad_account_id: str, managed_campaigns: list[str]
    ):
        self.api = api

        if re.search(r"^act_", ad_account_id):
            raise Exception(
                "initial CampaignState with ad account id without act_ prefix"
            )

        self.account: AdAccount = AdAccount(f"act_{ad_account_id}", api=self.api)

        self.managed_campaigns = managed_campaigns

    @cache
    def campaign_state(self, campaign_name: str) -> CampaignState:
        return CampaignState(self, self.api, self.account, campaign_name)

    @cached_property
    def campaigns(self) -> List[Campaign]:
        all_campaigns = get_campaigns(self.account)
        return [c for c in all_campaigns if c["name"] in self.managed_campaigns]

    @cached_property
    def adsets(self) -> List[AdSet]:
        states = [self.campaign_state(campaign["name"]) for campaign in self.campaigns]
        return [a for c in states for a in c.adsets]

    @cached_property
    def ads(self) -> List[Ad]:
        states = [self.campaign_state(campaign["name"]) for campaign in self.campaigns]
        return [a for c in states for a in c.ads]

    @cached_property
    def custom_audiences(self) -> List[CustomAudience]:
        return get_custom_audiences(self.account)

    def get_audience(self, name: str) -> CustomAudience:
        aud = next((a for a in self.custom_audiences if a["name"] == name), None)
        if not aud:
            raise StateNameError(f"Audience not found with name: {name}")
        return aud
