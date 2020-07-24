import pandas as pd
import logging

def res_col(ref, df):
    try:
        response = df[df.question_ref == ref].response.iloc[0]
    except IndexError:
        raise Exception(f'Could not find question with ref {ref}')

    return response

def _res_col(ref, col_name, df):
    try:
        df[col_name] = res_col(ref, df)
        return df
    except:
        logging.warning(f'User without district: {df.userid.unique()[0]}')
        return None

def add_res_col(ref, col_name, groupby, df):
    df = df \
        .groupby(groupby) \
        .apply(lambda df: _res_col(ref, col_name, df))

    return df


def users_fulfilling(treqs, cluster_ref, df):
    df = add_res_col(cluster_ref, 'cluster', 'userid', df)

    for ref, pred in treqs:
        try:
            d = df[df.question_ref == ref]
            d = d[d.response.map(pred)]
            users = d.userid.unique()
            df = df[df.userid.isin(users)]
        except AttributeError:
            return None

    return df

def make_pred(q):
    fns = {
        'equal': lambda a, b: a == b,
        'greater_than': lambda a, b: a > b,
        'less_than': lambda a, b: a < b
    }

    try:
        fn = fns[q['op']]
    except KeyError:
        raise TypeError(f'op function: {q["op"]} is not supported!')

    return lambda x: fn(x, q['value'])

def make_reqs(target_questions):
    return [(q['ref'], make_pred(q))
            for q in target_questions]

def only_target_users(df, surveys):
    reqs = [(s['shortcode'], s['cluster_question']['ref'], make_reqs(s['target_questions']))
            for s in surveys]

    users = [users_fulfilling(tqs, cq, df[df.shortcode == sc])
             for sc, cq, tqs in reqs]

    users = [u for u in users if u is not None]

    if len(users) == 0:
        return None

    return pd.concat(users)

def get_saturated_clusters(df, stratum):
    surveys = stratum['surveys']
    is_saturated = lambda df: df.userid.unique().shape[0] >= stratum['per_cluster_pop']

    df = only_target_users(df, surveys)

    if df is None:
        return []

    clusters = df \
                 .groupby('cluster') \
                 .filter(is_saturated) \
                 ['cluster'] \
                 .unique() \
                 .tolist()

    return clusters
