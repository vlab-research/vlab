import json
import logging
from typing import Dict, Optional, List
import pandas as pd
import typing_json
from environs import Env
from cyksuid import ksuid
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.exceptions import FacebookRequestError
from clustering import get_saturated_clusters, only_target_users
from responses import last_responses, get_surveyids, get_metadata
from marketing import Marketing, MarketingNameError, CreativeGroup, \
    Location, Cluster, validate_targeting



def get_df(cnf):
    surveys = cnf['stratum']['surveys']

    questions = [q['ref']
                 for s in surveys
                 for q in s['target_questions']]

    questions += [s['cluster_question']['ref'] for s in surveys]

    uid = cnf['survey_user']
    shortcodes = [s['shortcode'] for s in surveys]

    surveyids = get_surveyids(shortcodes, uid, cnf['chatbase'])

    responses = last_responses(surveyids,
                               questions,
                               cnf['chatbase'])

    df = pd.DataFrame(list(responses))

    if df.shape[0] == 0:
        print(f'Warning: no responses were found in the database \
        for shortcodes: {shortcodes} and questions: {questions}')
        return None


    # add synthetic district responses
    md = get_metadata(surveyids, cnf['chatbase'])
    md = pd.DataFrame(md)

    # could remove original district questions...
    df = pd.concat([md, df]).reset_index(drop=True)

    return df


def lookup_clusters(saturated, lookup_loc):
    lookup = pd.read_csv(lookup_loc)
    return [d for d in lookup.disthash.unique()
            if d not in saturated]

def unsaturated(df, cnf):
    if df is None:
        return lookup_clusters([], cnf['lookup_loc'])

    stratum = cnf['stratum']
    saturated = get_saturated_clusters(df, stratum)
    return lookup_clusters(saturated, cnf['lookup_loc'])

def lookalike(df, cnf):
    if df is None:
        return []
    df = only_target_users(df, cnf['stratum']['surveys'])
    return df.userid.unique().tolist()

def opt(cnf):
    df = get_df(cnf)
    clusters = unsaturated(df, cnf)
    users = lookalike(df, cnf)
    return clusters, users

def get_conf(env):
    c = {
        'country': env('MALARIA_COUNTRY'),
        'budget': env('MALARIA_BUDGET'),
        'survey_user': env('MALARIA_SURVEY_USER'),
        'lookup_loc': env('MALARIA_DISTRICT_LOOKUP'),
        'chatbase': {
            'db': env('CHATBASE_DATABASE'),
            'user': env('CHATBASE_USER'),
            'host': env('CHATBASE_HOST'),
            'port': env('CHATBASE_PORT'),
            'password': env('CHATBASE_PASSWORD', None),
        }
    }

    with open('config/strata.json') as f:
        s = f.read()
        c['stratum'] = json.loads(s)['strata'][0]

    return c


def load_creatives(path: str, group: str) -> CreativeGroup:
    with open(path) as f:
        s = f.read()

    d = typing_json.loads(s, Dict[str, CreativeGroup])
    return d[group]

def load_cities(path):
    cities = pd.read_csv(path)
    cities = cities[cities.rad >= 1.0]
    return cities


def uniqueness(clusters: List[Cluster]):
    ids = [cl.id for cl in clusters]
    if len(set(ids)) != len(ids):
        raise Exception('Cluster IDs combinations are not unique')

def new_ads(m: Marketing,
            cnf,
            status: str,
            clusters: List[str],
            lookalike_aud: Optional[CustomAudience]) -> None:

    # TODO: get this dynamically somehow
    cluster_vars = ['disthash', 'distname']
    creative_config = 'config/creatives.json'
    creative_group = 'hindi'
    targeting = cnf['stratum'].get('targeting')

    # different creative group per cluster?
    cg = load_creatives(creative_config, creative_group)

    # groupby cluster
    cities = load_cities(cnf['lookup_loc'])
    locs = [(Cluster(i, n), [Location(r.lat, r.lng, r.rad) for _, r in df.iterrows()])
            for (i, n), df in cities.groupby(cluster_vars)]

    # filter for only clusters of interest
    locs = [(cl, ls) for cl, ls in locs if cl.id in clusters]

    # check uniqueness of clusterids
    uniqueness([cl for cl, _ in locs])

    # validate targeting keys
    if targeting:
        validate_targeting(targeting)


    for cl, ls in locs:
        m.launch_adsets(cl, cg, ls, cnf['budget'], targeting, status, lookalike_aud)


def get_aud(m: Marketing, cnf, create: bool) -> Optional[CustomAudience]:
    name = cnf['stratum']['name']
    try:
        aud = m.get_audience(name)
    except MarketingNameError:
        if create:
            aud = m.create_custom_audience(name, 'Virtual Lab auto-generated audience', [])
        else:
            aud = None
    return aud


def update_audience():
    env = Env()
    cnf = get_conf(env)
    m = Marketing(env)

    df = get_df(cnf)
    users = lookalike(df, cnf)
    aud = get_aud(m, cnf, True)

    logging.info(f'Adding {len(users)} users to audience {aud.get("name")}.')

    m.add_users(aud['id'], users)


def update_ads():
    env = Env()
    cnf = get_conf(env)
    m = Marketing(env)

    df = get_df(cnf)
    clusters = unsaturated(df, cnf)

    aud = get_aud(m, cnf, False)
    if aud:

        # TODO: handle case when too few users in the aud
        # which should throw a facebook error...
        uid = ksuid.ksuid().encoded.decode('utf-8')
        aud = m.create_lookalike(f'vlab-{uid}', cnf['country'], aud)

    new_ads(m, cnf, 'ACTIVE', clusters, aud)
