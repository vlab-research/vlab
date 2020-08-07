import logging
from typing import Dict, List, Tuple
from marketing import Marketing
import pandas as pd


def res_col(ref, df, t):
    try:
        response = df[ref].iloc[0]
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

def _make_reqs(target_questions):
    return [(q['ref'], make_pred(q))
            for q in target_questions]

def make_reqs(target_key, surveys):
    return [(s['shortcode'], s['cluster_question']['ref'], _make_reqs(s[target_key]))
            for s in surveys]

def add_cluster(surveys, df):
    reqs = [(s['shortcode'], s['cluster_question']['ref']) for s in surveys]
    reqs = dict(reqs)

    return df \
        .groupby('shortcode') \
        .apply(lambda df: add_res_cols([('cluster', reqs[df.shortcode.iloc[0]], lambda x: x)],
                                       'userid',
                                       df)) \
        .reset_index(drop=True)

def shape_df(df):
    df = df \
        .groupby(['surveyid', 'shortcode']) \
        .apply(lambda df: df.pivot('userid', 'question_ref', 'response')) \
        .reset_index()

    # Clean anyone who answered multiple surveys in this group of shortcodes
    # in theory should only be testers.
    # Keep the lastest survey they took.
    return df \
        .sort_values('md:startTime') \
        .drop_duplicates(['userid'], keep='last')


def users_fulfilling(treqs, df):
    for ref, pred in treqs:
        try:
            d = df[df[ref].map(pred)]
            users = d.userid.unique()
            df = df[df.userid.isin(users)]
        except KeyError:
            return None

    return df

def users_answering(treqs, df):
    for ref, _ in treqs:
        try:
            d = df[~df[ref].isna()]
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




def only_target_users(df, surveys, target_key, fn=users_fulfilling):
    reqs = make_reqs(target_key, surveys)

    users = [fn(tqs, df[df.shortcode == sc])
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
    df = add_cluster(surveys, df)
    targets = only_target_users(df, surveys, 'target_questions')
    return _saturated_clusters(stratum, targets)


def get_weight_lookup(df, stratum, all_clusters) -> Dict[str, float]:
    surveys = stratum['surveys']

    # reqs = make_reqs('target_questions', surveys)
    df = add_cluster(surveys, df)

    targets = only_target_users(df, surveys, 'target_questions')
    target_users = targets.userid.unique()
    df['target'] = df.userid.isin(target_users)

    saturated = _saturated_clusters(stratum, targets)
    df = df[~df.cluster.isin(saturated)].reset_index(drop=True)
    df = only_target_users(df, surveys, 'target_questions', users_answering)
    df = df.drop_duplicates('userid')

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


from dataclasses import dataclass
from datetime import datetime

@dataclass
class BudgetWindow:
    start: str
    until: str

    @property
    def start_date(self):
        return datetime.strptime(self.start, '%Y-%m-%d')

    @property
    def until_date(self):
        return datetime.strptime(self.until, '%Y-%m-%d')


def get_budget_lookup(df, stratum, max_budget, days_left, window: BudgetWindow, spend: Dict[str, float]):
    surveys = stratum['surveys']

    # Get only target users and add cluster
    df = add_cluster(surveys, df)
    df = only_target_users(df, surveys, 'target_questions')

    # filter by time
    windowed = df[(df['md:startTime'] >= window.start_date) & (df['md:startTime'] <= window.until_date)]


    # see how many remaining in each cluster (don't add one)
    tot = df.groupby('cluster').userid.count().to_dict()
    tot = {**{k:0 for k in spend.keys()}, **tot}
    goal = stratum['per_cluster_pop']
    remain = {k: goal - v for k, v in tot.items()}

    # pretend to have found one in each cluster
    counts = windowed.groupby('cluster').userid.count().to_dict()
    counts = {**{k:1 for k in spend.keys()}, **counts}
    price = {k: spend[k] / v for k, v in counts.items()}
    budget = {k: v*remain[k] / days_left for k, v in price.items()}
    tot_price = sum(budget.values())

    if tot_price > max_budget:
        weighted = {k:v/tot_price for k, v in budget.items()}
        weighted = {k:v*max_budget for k, v in budget.items()}
        return weighted

    return budget



def cluster_value(perc, tot):
    tot = tot + 1
    m = tot.mean()
    w = (m / tot)

    pm = perc.mean()
    if pm > 0:
        p = perc / pm
    else:
        p = 0.

    weights = w + p

    return weights
