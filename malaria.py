import json
import pandas as pd
from environs import Env
from cyksuid import ksuid
from clustering import is_saturated, get_unsaturated_clusters, all_users_fulfilling, res_col
from responses import last_responses, format_synthetic, get_surveyids
from marketing import Marketing, MarketingNameError


def make_district(pincode):
    pincode = str(pincode).strip()
    return pincode[:3]

def _make_event(q_district, df):
    district = res_col(q_district, df)
    row = df.iloc[0]
    row['response'] = make_district(district)
    return row


def synthetic_district(ref, shortcode, df):
    d = df[df.shortcode == shortcode] \
        .groupby('userid') \
        .apply(lambda df: _make_event(ref, df)) \
        .reset_index(drop=True)

    dat = d.to_dict(orient='records')
    return format_synthetic(dat, 'synth-district', 'district')


def synthetic_districts(cnfs, df):
    return [r for ref, s in cnfs
            for r in synthetic_district(ref, s, df)]

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
        raise Exception('No responses were found in the database!')

    # add synthetic district responses
    synth_cnf = [(t['cluster_question']['ref'], t['shortcode'])
                 for t in surveys]

    synth = synthetic_districts(synth_cnf, df)
    synth = pd.DataFrame(synth)

    # could remove original district questions...
    df = pd.concat([synth, df]).reset_index(drop=True)

    return df

def geo_lookup(districts, lookup_loc):
    lookup = pd.read_csv(lookup_loc)
    lookup['pincode'] = lookup.pincode.astype(str)

    matches = pd.Series(districts).isin(lookup.pincode)
    if matches.sum() != len(matches):
        raise Exception(f'District(s) not found!! {districts}')

    lookup = lookup[lookup.pincode.isin(districts)]
    return lookup.drop(columns=['pincode']).to_dict(orient='records')

def unsaturated(df, cnf):
    fil = is_saturated(cnf)
    res = get_unsaturated_clusters(df, 'synth-district', fil)
    clusters = geo_lookup(res, cnf['lookup_loc'])
    return clusters

def lookalike(df, cnf):
    users = all_users_fulfilling(cnf['stratum']['surveys'], df)
    return users

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
            'password': env('CHATBASE_PASSWORD'),
        }
    }

    c['surveyids'] = get_surveyids(c['survey_shortcode'],
                                   c['survey_user'],
                                   c['chatbase'])

    with open('strata.json') as f:
        s = f.read()
        c['stratum'] = json.loads(s)['strata'][0]

    return c


def load_creatives(group):
    with open('creatives.json') as f:
        s = f.read()

    d = json.loads(s)
    return d[group]

def load_cities():
    cities = pd.read_csv('output/cities.csv')
    cities = cities[cities.rad >= 1.0]
    return cities

def new_ads(m, clusters, budget, status, lookalike_aud):
    cities = load_cities()

    # TODO: clusters tells me which ones are NOT saturated
    # but only from those found in or database,
    # doesn't tell us which codes have 0 values!!!!!!!

    # cities

    creatives = load_creatives('hindi')
    locs = [(r.lat, r.lng, r.rad) for _, r
            in cities.iterrows()]

    # for cg, d in df.groupby('creative_group'):
    #     locs = [(r.lat, r.lng, r.rad) for _, r
    #             in d.iterrows()]
    #     creatives = load_creatives(cg)

    m.launch_adsets(creatives, locs, budget, status, lookalike_aud)


def get_aud(m, cnf, create):
    name = cnf['audience_name']
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

    m.add_users(aud['id'], users)


def update_ads():
    env = Env()
    cnf = get_conf(env)
    m = Marketing(env)

    df = get_df(cnf)
    clusters = unsaturated(df, cnf)

    aud = get_aud(m, cnf, False)
    if aud:
        uid = ksuid.ksuid().encoded.decode('utf-8')
        aud = m.create_lookalike(f'vlab-{uid}', cnf['country'], aud)

    new_ads(m, clusters, cnf['budget'], 'PAUSED', aud)
