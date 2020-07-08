import pandas as pd
from environs import Env
from clustering import is_saturated, get_unsaturated_clusters, users_fulfilling, res_col
from responses import last_responses, format_synthetic

env = Env()

def make_district(pincode):
    pincode = str(pincode).strip()
    return pincode[:3]

def _make_event(q_district, df):
    district = res_col(q_district, df)
    row = df.iloc[0]
    row['response'] = make_district(district)
    return row

def synthetic_district(q_district, df):
    d = df \
        .groupby('userid') \
        .apply(lambda df: _make_event(q_district, df)) \
        .reset_index(drop=True)

    dat = d.to_dict(orient='records')
    return format_synthetic(dat, 'synth-district', 'district')

def get_df(cnf):
    questions = [cnf['q_district'], cnf['q_target']]
    responses = last_responses(cnf['surveyid'], questions, cnf['dbname'], cnf['dbuser'])
    df = pd.DataFrame(list(responses))

    # add synthetic district responses
    synth = synthetic_district(cnf['q_district'], df)
    synth = pd.DataFrame(list(synth))

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
    qa, lim = cnf['q_target'], cnf['cluster_size']

    # whatever is necessary to make target
    reqs = [(qa, lambda x: x.strip() == cnf['target_value'])]

    fil = is_saturated(reqs, lim)
    res = get_unsaturated_clusters(df, 'synth-district', fil)

    clusters = geo_lookup(res, cnf['lookup_loc'])
    return clusters

def lookalike(df, cnf):
    reqs = [(cnf['q_target'], lambda x: x.strip() == cnf['target_value'])]
    users = users_fulfilling(reqs, df)
    return users

def opt(cnf):
    df = get_df(cnf)
    clusters = unsaturated(df, cnf)
    users = lookalike(df, cnf)
    return clusters, users


def main():
    cnf = {
        'q_district': env('MALARIA_DISTRICT_QUESTION'),
        'q_target': env('MALARIA_TARGET_QUESTION'),
        'target_value': env('MARLARIA_TARGET_VALUE'),
        'surveyid': env('MALARIA_SURVEY_ID'),
        'cluster_size': env('MALARIA_CLUSTER_SIZE'),
        'dbname': env('CHATBASE_DATABASE'),
        'dbuser': env('CHATBASE_USER'),
        'lookup_loc': env('MALARIA_DISTRICT_LOOKUP')
    }

    clusters, users = opt(cnf)

    # store or send or use API or something
    print(clusters)
    print(users)
