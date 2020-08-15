import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Any
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from .api import call


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
        return self.start_date.strftime('%Y-%m-%d')

    @property
    def until(self):
        return self.until_date.strftime('%Y-%m-%d')

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
    campaigns = call(account.get_campaigns, {}, ['name'])
    c = next((c for c in campaigns if c['name'] == name), None)
    return c

def get_creatives(account: AdAccount, ad_label_id: str) -> List[AdCreative]:
    # loads ALL creatives for account...
    # how many API requests does that count as???
    fields = ['name', 'url_tags', 'actor_id', 'object_story_spec']
    params = {'ad_label_ids': [ad_label_id]}

    return call(account.get_ad_creatives_by_labels, params, fields)

def get_adsets(campaign: Campaign) -> List[AdSet]:
    return call(campaign.get_ad_sets, {}, ['name', 'status', 'targeting'])

def get_ads(adset: AdSet) -> List[Ad]:
    return call(adset.get_ads, {}, ['creative', 'adset_id', 'status'])

def get_all_ads(adsets: List[AdSet]) -> List[Ad]:
    return [a for s in adsets for a in get_ads(s)]

def get_label(account: AdAccount, name: str):
    return call(account.create_ad_label, {'name': name}, [])

def _get_insights(adset, window):
    params = {
        'time_range': {
            'since': window.start,
            'until': window.until
        }
    }
    fields = ['unique_link_clicks_ctr', 'unique_ctr', 'ctr',
              'cpp', 'cpm', 'cpc', 'unique_clicks', 'reach',
              'spend', 'actions']

    try:
        return call(adset.get_insights, params=params, fields=fields)[0]
    except IndexError:
        return None

def get_insights(adsets, window: BudgetWindow) -> Tuple[Dict[str, float], Dict[str, Any]]:
    insights = {a['name']: _get_insights(a, window)
                for a in adsets}

    spending = lambda i: 0 if i is None else i['spend']
    spend = {n: spending(i) for n, i in insights.items()}
    spend = {n: float(v)*100 for n, v in spend.items()}
    return spend, insights

def get_account(env):
    cnf = {
        'APP_ID': env('FACEBOOK_APP_ID'),
        'APP_SECRET': env('FACEBOOK_APP_SECRET'),
        'USER_TOKEN': env('FACEBOOK_USER_TOKEN'),
        'AD_ACCOUNT': f'act_{env("FACEBOOK_AD_ACCOUNT")}',
    }

    FacebookAdsApi.init(cnf['APP_ID'], cnf['APP_SECRET'], cnf['USER_TOKEN'])
    return AdAccount(cnf['AD_ACCOUNT'])

def get_custom_audiences(account):
    fields = [CustomAudience.Field.name,
              CustomAudience.Field.description,
              CustomAudience.Field.subtype,
              CustomAudience.Field.time_created]

    return call(account.get_custom_audiences, {}, fields)


class CampaignState():
    def __init__(self, env, window=None):
        cnf = {
            'PAGE_ID': env('FACEBOOK_PAGE_ID'),
            'INSTA_ID': env('FACEBOOK_INSTA_ID'),
            'CAMPAIGN': env("FACEBOOK_AD_CAMPAIGN"),
            'AD_LABEL': env('FACEBOOK_AD_LABEL'),
            'USER_TOKEN': env('FACEBOOK_USER_TOKEN'),
            'ADSET_HOURS': env.int('FACEBOOK_ADSET_HOURS'),
            'LOOKALIKE_STARTING_RATIO': env.float('FACEBOOK_LOOKALIKE_STARTING_RATIO'),
            'LOOKALIKE_RATIO': env.float('FACEBOOK_LOOKALIKE_RATIO'),
        }

        self.cnf = cnf
        self.window = window
        self.account = get_account(env)
        self.campaign = get_campaign(self.account, cnf['CAMPAIGN'])
        self.label = get_label(self.account, cnf['AD_LABEL'])

        # TODO: this is a nest for bugs, it's not explicit that the data was
        # loaded or not.
        self.creatives = []
        self.adsets = []
        self.ads = []
        self.spend = []
        self.insights = []
        self.custom_audiences = []

    def load_ad_state(self):
        if not self.window:
            raise Exception('Cannot load_ad_state without a window')

        self.creatives = get_creatives(self.account, self.label['id'])
        if self.campaign:
            self.adsets = get_adsets(self.campaign)
            self.ads = get_all_ads(self.adsets)
            self.spend, self.insights = get_insights(self.adsets, self.window)
            logging.info(f'Campaign {self.campaign["name"]} has {len(self.creatives)} creatives, '
                         f'and {len(self.adsets)} running ads')

        else:
            raise Exception('No campaign! Must create first...')

    def load_audience_state(self):
        self.custom_audiences = get_custom_audiences(self.account) # add label???

    def get_audience(self, name):
        if not self.custom_audiences:
            raise Exception('Must load_audience_state before getting an audience')

        aud = next((a for a in self.custom_audiences
                    if a['name'] == name), None)
        if not aud:
            raise Exception(f'Audience not found with name: {name}')
        return aud
