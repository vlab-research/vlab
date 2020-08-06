import json
import logging
from typing import Dict, Optional, List, Any, Tuple
import pandas as pd
import typing_json
from environs import Env
from facebook_business.adobjects.customaudience import CustomAudience
from clustering import get_saturated_clusters, only_target_users, get_weight_lookup
from responses import get_response_df
from marketing import Marketing, MarketingNameError, CreativeGroup, \
    Location, Cluster, validate_targeting

logging.basicConfig(level=logging.INFO)


def get_df(cnf):
    surveys = [survey for stratum in cnf['strata']
               for survey in stratum['surveys']]

    questions = {q['ref']
                 for s in surveys
                 for q in s['target_questions']}

    questions |= {s['cluster_question']['ref'] for s in surveys}

    survey_user = cnf['survey_user']
    shortcodes = {s['shortcode'] for s in surveys}

    return get_response_df(survey_user, shortcodes, questions, cnf['chatbase'])



def lookup_clusters(saturated, lookup_loc):
    lookup = pd.read_csv(lookup_loc)
    return [d for d in lookup.disthash.unique()
            if d not in saturated]

def unsaturated(df, cnf, stratum):
    if df is None:
        return lookup_clusters([], cnf['lookup_loc'])

    saturated = get_saturated_clusters(df, stratum)
    return lookup_clusters(saturated, cnf['lookup_loc'])

def lookalike(df, stratum):
    if df is None:
        return [], []

    target = only_target_users(df, stratum['surveys'], 'target_questions')
    target_users = target.userid.unique()

    anti = only_target_users(df, stratum['surveys'], 'exclude_questions')
    anti_users = anti.userid.unique()

    return target_users.tolist(), anti_users.tolist()

def opt(cnf, anti=False):
    # opt is used in tests and nothing else
    # pick first stratum
    stratum = cnf['strata'][0]

    df = get_df(cnf)
    clusters = unsaturated(df, cnf, stratum)
    users, antis = lookalike(df, stratum)
    if anti:
        return clusters, users, antis
    return clusters, users


def get_conf(env):
    c = {
        'country': env('MALARIA_COUNTRY'),
        'budget': env.float('MALARIA_BUDGET'),
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
        c['strata'] = json.loads(s)['strata']

    return c


def load_creatives(path: str) -> Dict[str, CreativeGroup]:
    with open(path) as f:
        s = f.read()

    d = typing_json.loads(s, Dict[str, CreativeGroup])
    return d

def load_cities(path):
    cities = pd.read_csv(path)
    cities = cities[cities.rad >= 1.0]
    return cities


def uniqueness(clusters: List[Cluster]):
    ids = [cl.id for cl in clusters]
    if len(set(ids)) != len(ids):
        raise Exception('Cluster IDs combinations are not unique')

def new_ads(m: Marketing,
            cnf: Dict[str, Any],
            df: pd.DataFrame,
            stratum: Dict[str, Any],
            status: str,
            saturated_clusters: List[str],
            aud: Optional[CustomAudience],
            anti_aud: Optional[CustomAudience]) -> None:

    # TODO: get this dynamically somehow
    # aud
    cluster_vars = ['disthash', 'distname', 'creative_group', 'include_audience']
    creative_config = 'config/creatives.json'

    cg_lookup = load_creatives(creative_config)
    cities = load_cities(cnf['lookup_loc'])

    all_clusters = cities[cluster_vars[0]].unique()
    weight_lookup = get_weight_lookup(df, stratum, all_clusters)
    total_budget = cnf['budget']
    budget_lookup = {k:int(w*total_budget) for k, w in weight_lookup.items()}


    # In principle all the groupby vars should be the same,
    # so grouping by clusterid, clustername, and creative group
    # should return the same groups!! Important data assumption!
    LocsType = List[Tuple[Cluster, CreativeGroup, List[Location], int, bool]]
    locs: LocsType = [(Cluster(i, n),
                       cg_lookup[cg],
                       [Location(r.lat, r.lng, r.rad) for _, r in df.iterrows()],
                       budget_lookup[i],
                       bool(au))
                      for (i, n, cg, au), df in cities.groupby(cluster_vars)
                      if i not in saturated_clusters]

    # check uniqueness of clusterids
    uniqueness([cl for cl, _, _, _, _ in locs])

    # validate targeting keys
    targeting = stratum.get('targeting')
    if targeting:
        validate_targeting(targeting)


    for cl, cg, ls, bu, au in locs:
        if au:
            m.launch_adsets(cl, cg, ls, bu, targeting, status, aud, anti_aud)
        else:
            m.launch_adsets(cl, cg, ls, bu, targeting, status, None, None)


def get_aud(m: Marketing, name, create: bool) -> Optional[CustomAudience]:
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
    m = Marketing(env, load_ads=False)
    df = get_df(cnf)

    for stratum in cnf['strata']:
        users, anti_users = lookalike(df, stratum)
        name = stratum['name']
        for u, n in [(users, name), (anti_users, f'anti-{name}')]:
            aud = get_aud(m, n, True)
            logging.info(f'Adding {len(u)} users to audience {aud.get("name")}.')
            res = m.add_users(aud['id'], u)
            for r in res:
                logging.info(r)


def update_ads():
    env = Env()
    cnf = get_conf(env)
    m = Marketing(env)

    df = get_df(cnf)

    # TODO: make a separate campaign per strata
    # this will requre dif instances of Marketing.
    # change label for creatives, make it linked to
    # campaign somehow?
    # or just cache get_creatives...
    stratum = cnf['strata'][0]

    saturated = get_saturated_clusters(df, stratum)

    aud, anti_aud = get_aud(m, stratum['name'], False), \
        get_aud(m, f'anti-{stratum["name"]}', False)

    if aud:
        aud = m.get_lookalike(aud, cnf['country'])

    if anti_aud:
        anti_aud = m.get_lookalike(anti_aud, cnf['country'])

    new_ads(m, cnf, df, stratum, 'ACTIVE', saturated, aud, anti_aud)
