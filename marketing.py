import json
import logging
import re
from urllib.parse import quote
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, NamedTuple, Tuple, Optional, Union, Any, Dict
import requests
import backoff
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.targeting import Targeting
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.exceptions import FacebookRequestError
from facebook_business.adobjects.targetinggeolocationcustomlocation \
    import TargetingGeoLocationCustomLocation
from facebook_business.adobjects.targetinggeolocation import TargetingGeoLocation
from toolz import get_in
import xxhash


# 5 minute constant backoff
BACKOFF = 5*60

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


class Cluster(NamedTuple):
    id: str
    name: str


class CreativeConfig(NamedTuple):
    name: str
    image_hash: str
    image: str
    body: str
    welcome_message: str
    link_text: str
    button_text: str
    form: str

class CreativeGroup(NamedTuple):
    name: str
    creatives: List[CreativeConfig]

class Location(NamedTuple):
    lat: float
    lng: float
    rad: float


class AdsetConf(NamedTuple):
    campaign: Campaign
    cluster: Cluster
    locs: List[Location]
    creatives: List[AdCreative]
    budget: float
    status: str
    instagram_id: str
    hours: int
    targeting: Optional[Dict[str, Any]]
    audience: Optional[CustomAudience]
    excluded_audience: Optional[CustomAudience]


class MarketingNameError(BaseException):
    pass

# Setup backoff logging
logging.getLogger('backoff').addHandler(logging.StreamHandler())

def check_code(e):
    # only continue on code 80004
    code = e.api_error_code()
    logging.info(f'Facebook error code: {code}')
    return False
    # return code not in [80004]

def split(li, N):
    while li:
        head, li = li[:N], li[N:]
        yield head

@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def get_campaign(account, name):
    campaigns = account.get_campaigns(fields=['name'])
    c = next((c for c in campaigns if c['name'] == name), None)
    if not c:
        raise MarketingNameError(f'Could not find campaign: {name}')
    return c

@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def create_campaign(account, name):
    params = {
        Campaign.Field.name: name,
        Campaign.Field.status: Campaign.Status.active,
        Campaign.Field.objective: Campaign.Objective.messages,
        Campaign.Field.special_ad_categories: []
    }

    return account.create_campaign(params=params, fields=['name'])

def get_or_create_campaign(account, name):
    try:
        campaign = get_campaign(account, name)
    except MarketingNameError:
        campaign = create_campaign(account, name)
    return campaign

def create_location(lat, lng, rad):
    return {
        TargetingGeoLocationCustomLocation.Field.latitude: lat,
        TargetingGeoLocationCustomLocation.Field.longitude: lng,
        TargetingGeoLocationCustomLocation.Field.radius: rad,
        TargetingGeoLocationCustomLocation.Field.distance_unit: 'kilometer',
    }



def get_all_audiences(account):
    fields = [CustomAudience.Field.name,
              CustomAudience.Field.description,
              CustomAudience.Field.subtype,
              CustomAudience.Field.time_created]


    audiences = account.get_custom_audiences(fields=fields)

    audiences = [aud for aud in audiences
                 if aud['subtype'] == CustomAudience.Subtype.custom]

    audiences = sorted(audiences, key=lambda x: -x['time_created'])
    return audiences


def validate_targeting(targeting):
    valid_targets = set(dir(Targeting.Field))
    for k, _ in targeting.items():
        if k not in valid_targets:
            raise Exception(f'Targeting config invalid, key: {k} does not exist!')

def create_targeting(c: AdsetConf) -> Dict[str, Union[Any, List[Any]]]:
    custom_locs = [create_location(lat, lng, rad)
                   for lat, lng, rad in c.locs]

    T = Dict[str, Union[Any, List[Any]]]

    targeting: T = {
        Targeting.Field.geo_locations: {
            TargetingGeoLocation.Field.location_types: ['home'],
            TargetingGeoLocation.Field.custom_locations: custom_locs
        }
    }

    if c.targeting:
        for k, v in c.targeting.items():
            targeting[k] = v

    return targeting


@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def update_adset(adset: AdSet, c: AdsetConf) -> AdSet:
    targeting = create_targeting(c)

    if c.audience:
        targeting[Targeting.Field.custom_audiences] = [{'id': c.audience['id']}]

    if c.excluded_audience:
        targeting[Targeting.Field.excluded_custom_audiences] = \
            [{'id': c.excluded_audience['id']}]

    params = {
        AdSet.Field.daily_budget: c.budget,
        AdSet.Field.end_time: datetime.utcnow() + timedelta(hours=c.hours),
        AdSet.Field.targeting: targeting,
        AdSet.Field.status: c.status
    }

    adset = adset.api_update(params=params)
    return adset


@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def create_adset(account, name, c: AdsetConf):
    targeting = create_targeting(c)

    if c.audience:
        targeting[Targeting.Field.custom_audiences] = [{'id': c.audience['id']}]

    if c.excluded_audience:
        targeting[Targeting.Field.excluded_custom_audiences] = \
            [{'id': c.excluded_audience['id']}]

    params = {
        AdSet.Field.name: name,
        AdSet.Field.instagram_actor_id: c.instagram_id,
        AdSet.Field.daily_budget: c.budget,
        AdSet.Field.start_time: datetime.utcnow() + timedelta(minutes=5),
        AdSet.Field.end_time: datetime.utcnow() + timedelta(hours=c.hours),
        AdSet.Field.campaign_id: c.campaign['id'],
        AdSet.Field.optimization_goal: AdSet.OptimizationGoal.replies,
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.bid_strategy: AdSet.BidStrategy.lowest_cost_without_cap,
        AdSet.Field.targeting: targeting,
        AdSet.Field.status: c.status
    }

    adset = account.create_ad_set(params=params)

    return adset

@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def create_ad(account, adset, creative, name, status) -> Ad:
    return account.create_ad(params={
        'name': name,
        'status': status,
        'adset_id': adset['id'],
        'creative': {'creative_id': creative['id']}
    })

def create_ads(account, adset, creatives, status):
    ads = [create_ad(account, adset, c, c['name'], status)
           for c in creatives]

    return ads

def hash_creative(creative):
    keys = [['actor_id'],
            ['url_tags'],
            ['object_story_spec', 'instagram_actor_id'],
            ['object_story_spec', 'link_data', 'image_hash'],
            ['object_story_spec', 'link_data', 'message'],
            ['object_story_spec', 'link_data', 'name'],
            ['object_story_spec', 'link_data', 'page_welcome_message']]

    vals = [get_in(k, creative) for k in keys]
    vals = [v for v in vals if v]
    s = ' '.join(vals)
    return xxhash.xxh64(s).hexdigest()

@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def get_creatives(account: AdAccount, ad_label_id: str):
    # loads ALL creatives for account...
    # how many API requests does that count as???
    fields = ['name', 'url_tags', 'actor_id', 'object_story_spec']
    params = {'ad_label_ids': [ad_label_id]}

    creatives = account.get_ad_creatives_by_labels(fields=fields,
                                                   params=params)
    return {hash_creative(c): c for c in creatives}


@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def get_running_ads(campaign):
    sets = campaign.get_ad_sets(fields=['name'])
    return {s['name']:s for s in sets}


@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def get_running_ad(name, sets, creatives):
    if name in sets:
        adset = sets[name]
        ads = adset.get_ads()
        if len(ads) == len(creatives):
            return adset

        # else this adset is corrupted
        adset.api_delete()

    return None

@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def get_label(account, name):
    label = account.create_ad_label(params={'name': name})
    return label


def launch_adset(name: str, account: AdAccount, c: AdsetConf) -> Tuple[AdSet, List[Ad]]:

    adset = create_adset(account, name, c)
    ads = create_ads(account, adset, c.creatives, c.status)
    return adset, ads



def get_images(account):
    return account.get_ad_images(fields=[AdImage.Field.hash,
                                         AdImage.Field.name,
                                         AdImage.Field.created_time,
                                         AdImage.Field.filename])


def get_image_hash(account, name):
    images = get_images(account)
    img = next((img for img in images if img['name'] == name), None)
    if not img:
        raise Exception(f'Could not find image with name: {name}')

    return img['hash']

def make_welcome_message(text, button_text, ref):
    payload = json.dumps({'referral': {'ref': ref}})

    message = {
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": button_text,
                            "payload": payload
                        }
                    ]
                }
            }
        }
    }

    return json.dumps(message, sort_keys=True)

def make_ref(form, id_, name) -> str:
    name = quote(name)
    id_ = quote(id_)
    return f'form.{form}.clusterid.{id_}.clustername.{name}'


def get_cluster_from_adset(adset_name: str) -> str:
    pat = r'(?<=vlab-)\w+'
    matches = re.search(pat, adset_name)
    if not matches:
        raise Exception('Cannot extract cluster id from adset: ${adset_name}')

    return matches[0]


@backoff.on_exception(backoff.constant, FacebookRequestError, giveup=check_code, interval=BACKOFF)
def _get_spend(adset, window):
    params = {
        'time_range': {
            'since': window.start,
            'until': window.until
        }
    }

    return adset.get_insights(params=params)[0]


class Marketing():
    def __init__(self, env, load_ads=True):
        cnf = {
            'APP_ID': env('FACEBOOK_APP_ID'),
            'APP_SECRET': env('FACEBOOK_APP_SECRET'),
            'PAGE_ID': env('FACEBOOK_PAGE_ID'),
            'INSTA_ID': env('FACEBOOK_INSTA_ID'),
            'USER_TOKEN': env('FACEBOOK_USER_TOKEN'),
            'AD_ACCOUNT': f'act_{env("FACEBOOK_AD_ACCOUNT")}',
            'CAMPAIGN': env("FACEBOOK_AD_CAMPAIGN"),
            'AD_LABEL': env('FACEBOOK_AD_LABEL'),
            'ADSET_HOURS': env.int('FACEBOOK_ADSET_HOURS'),
            'LOOKALIKE_STARTING_RATIO': env.float('FACEBOOK_LOOKALIKE_STARTING_RATIO'),
            'LOOKALIKE_RATIO': env.float('FACEBOOK_LOOKALIKE_RATIO'),
        }

        FacebookAdsApi.init(cnf['APP_ID'], cnf['APP_SECRET'], cnf['USER_TOKEN'])
        self.account = AdAccount(cnf['AD_ACCOUNT'])
        self.campaign = get_or_create_campaign(self.account, cnf['CAMPAIGN'])

        self.label = get_label(self.account, cnf['AD_LABEL'])

        if load_ads:
            self.running_ads = get_running_ads(self.campaign)
            self.creatives = get_creatives(self.account, self.label['id'])

            logging.info(f'Intiailized Marketing with {len(self.creatives)} creatives, '
                         f'{len(self.running_ads)} running ads and '
                         f'campaign {self.campaign["name"]}')

        self.cnf = cnf


    def get_spend(self, window: BudgetWindow) -> Dict[str, float]:

        spend = {a['name']: _get_spend(a, window)
                 for a in self.running_ads.values()}
        spend = {get_cluster_from_adset(n): i['spend']
                 for n, i in spend.items()}
        spend = {k: float(v)*100 for k, v in spend.items()}
        return spend


    def create_custom_audience(self, name, desc, users) -> CustomAudience:
        params = {
            'name': name,
            'subtype': 'CUSTOM',
            'description': desc,
            'customer_file_source': 'USER_PROVIDED_ONLY',
        }

        aud = self.account.create_custom_audience(fields=['name'], params=params)
        self.add_users(aud.get_id(), users)
        return aud

    def add_users(self, aud_id, users):
        pageid = self.cnf['PAGE_ID']
        token = self.cnf['USER_TOKEN']
        url = f'https://graph.facebook.com/v8.0/{aud_id}/users?access_token={token}'

        body = {
            'payload': {
                'schema': ['PAGEUID'],
                'is_raw': True,
                'page_ids': [pageid]
            }
        }

        results = []

        for chunk in split(users, 1000):
            body['payload']['data'] = [[u] for u in chunk]
            res = requests.post(url, json=body)
            results.append(res.json())

        return results

    def get_audience(self, name):
        fields = [CustomAudience.Field.name,
                  CustomAudience.Field.description,
                  CustomAudience.Field.subtype,
                  CustomAudience.Field.time_created]

        audiences = self.account.get_custom_audiences(fields=fields)
        aud = next((a for a in audiences if a['name'] == name), None)

        if not aud:
            raise MarketingNameError(f'Audience not found with name: {name}')

        return aud


    def launch_adsets(self,
                      cluster: Cluster,
                      cg: CreativeGroup,
                      locs: List[Location],
                      budget: float,
                      targeting: Dict[str, Any],
                      status: str,
                      audience: Optional[CustomAudience],
                      anti_audience: Optional[CustomAudience]) -> None:


        creatives = [self.create_creative(cluster, c) for c in cg.creatives]

        for i, ls in enumerate(split(locs, 200)):

            adset_conf = AdsetConf(self.campaign,
                                   cluster,
                                   ls,
                                   creatives,
                                   budget,
                                   status,
                                   self.cnf['INSTA_ID'],
                                   self.cnf['ADSET_HOURS'],
                                   targeting,
                                   audience,
                                   anti_audience)

            name = f'vlab-{cluster.id}-{cg.name}-{i}'

            adset = get_running_ad(name, self.running_ads, creatives)

            if adset:
                logging.info(f'Updating already running Ad: {name}')
                update_adset(adset, adset_conf)
            else:
                logging.info(f'Launching new Ad: {name}')
                launch_adset(name, self.account, adset_conf)


    def get_lookalike(self,
                      custom_audience: CustomAudience,
                      country: str) -> CustomAudience:

        slr, lr = self.cnf['LOOKALIKE_STARTING_RATIO'], self.cnf['LOOKALIKE_RATIO']

        spec = {
            'starting_ratio': slr,
            'ratio': lr,
            'country': country
        }

        name = f'vlab-lookalike-{custom_audience["name"]}-{slr}-{lr}'

        # Get lookalike if already exists
        try:
            return self.get_audience(name)
        except MarketingNameError:
            pass

        params = {
            CustomAudience.Field.name: name,
            CustomAudience.Field.subtype: CustomAudience.Subtype.lookalike,
            CustomAudience.Field.origin_audience_id: custom_audience.get_id(),
            CustomAudience.Field.lookalike_spec:json.dumps(spec),
        }

        return self.account.create_custom_audience(params=params, fields=['name'])

    @backoff.on_exception(backoff.constant,
                          FacebookRequestError,
                          giveup=check_code,
                          interval=BACKOFF)
    def create_creative(self, cluster: Cluster, config: CreativeConfig) -> AdCreative:
        ref = make_ref(config.form, cluster.id, cluster.name)
        msg = make_welcome_message(config.welcome_message, config.button_text, ref)

        oss = {
            "instagram_actor_id": self.cnf['INSTA_ID'],
            "link_data": {
                "call_to_action": {
                    "type": "MESSAGE_PAGE",
                    "value": {
                        "app_destination": "MESSENGER"
                    }
                },
                "image_hash": config.image_hash,
                "message": config.body,
                "name": config.link_text,
                "page_welcome_message": msg
            },
            "page_id": self.cnf['PAGE_ID'],
        }

        params = {
            "name": config.name,
            "url_tags": f"ref={ref}",
            "actor_id": self.cnf['PAGE_ID'],
            "object_story_spec": oss,
            "adlabels": [self.label],
        }

        fingerprint = hash_creative(params)

        try:
            creative = self.creatives[fingerprint]
            logging.debug(f'Found creative with fingerprint: {fingerprint}')
            return creative
        except KeyError:
            fields = ['name', 'object_story_spec']
            return self.account.create_ad_creative(fields=fields, params=params)
