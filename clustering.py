import logging
from typing import Dict
import pandas as pd

def res_col(ref, df, t):
    try:
        response = df[df.question_ref == ref].response.iloc[0]
    except IndexError:
        raise Exception(f'Could not find question with ref {ref}')

    return t(response)

def _res_col(ref, col_name, df, t):
    try:
        df[col_name] = res_col(ref, df, t)
        return df
    except:
        logging.warning(f'User without {col_name}: {df.userid.unique()[0]}')
        return None

def _res_cols(new_cols, df):
    for col, ref, t in new_cols:
        df = _res_col(ref, col, df, t)
    return df


def add_res_cols(new_cols, groupby, df):
    df = df \
        .groupby(groupby) \
        .apply(lambda df: _res_cols(new_cols, df))

    return df

def add_cluster(reqs, df):
    dfs = [add_res_cols([('cluster', cq, lambda x: x)],
                        'userid',
                        df[df.shortcode == sc])
           for sc, cq, _ in reqs]

    return pd.concat(dfs)


def users_fulfilling(treqs, df):
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

def _make_reqs(target_questions):
    return [(q['ref'], make_pred(q))
            for q in target_questions]

def make_reqs(target_key, surveys):
    return [(s['shortcode'], s['cluster_question']['ref'], _make_reqs(s[target_key]))
            for s in surveys]

def only_target_users(df, surveys, target_key):
    reqs = make_reqs(target_key, surveys)

    df = add_cluster(reqs, df)

    users = [users_fulfilling(tqs, df[df.shortcode == sc])
             for sc, cq, tqs in reqs]

    users = [u for u in users if u is not None]

    if len(users) == 0:
        return None

    return pd.concat(users)

def _saturated_clusters(stratum, targets):
    is_saturated = lambda df: df.userid.unique().shape[0] >= stratum['per_cluster_pop']

    if targets is None:
        return []

    clusters = targets \
                 .groupby('cluster') \
                 .filter(is_saturated) \
                 ['cluster'] \
                 .unique() \
                 .tolist()

    return clusters


def get_saturated_clusters(df, stratum):
    surveys = stratum['surveys']
    targets = only_target_users(df, surveys, 'target_questions')
    return _saturated_clusters(stratum, targets)


def get_weight_lookup(df, stratum, all_clusters) -> Dict[str, float]:
    surveys = stratum['surveys']

    reqs = make_reqs('target_questions', surveys)
    df = add_cluster(reqs, df)

    targets = only_target_users(df, surveys, 'target_questions')
    target_users = targets.userid.unique()
    df['target'] = df.userid.isin(target_users)

    saturated = _saturated_clusters(stratum, targets)
    df = df[~df.cluster.isin(saturated)].reset_index(drop=True)

    recorded_clusters = df.cluster.unique()
    extra_df = pd.DataFrame([{'cluster': c, 'perc': 0.0, 'tot': 0}
                             for c in all_clusters
                             if c not in recorded_clusters])

    lookup = df \
        .groupby('cluster') \
        .apply(lambda df: pd.Series([df.target.mean(), df.shape[0]], index=['perc', 'tot'])) \
        .reset_index() \
        .pipe(lambda df: pd.concat([df, extra_df])) \
        .pipe(lambda df: df.assign(weight=cluster_value(df.perc, df.tot))) \
        .set_index('cluster') \
        .to_dict(orient='index')

    lookup = {k: v['weight'] for k, v in lookup.items()}
    N = len(all_clusters)
    lookup = {**lookup, **{k:1/N for k in all_clusters if k not in lookup}}
    tot = sum(lookup.values())
    lookup = {k: v/tot for k, v in lookup.items()}

    return lookup

def cluster_value(perc, tot):
    tot += 1
    m = tot.mean()
    w = (m / tot)

    pm = perc.mean()
    if pm > 0:
        p = perc / pm
    else:
        p = 0.

    weights = w + p

    return weights
