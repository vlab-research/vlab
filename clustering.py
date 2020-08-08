import logging
from math import floor
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from marketing import Marketing, BudgetWindow
from forms import BadResponseError
import pandas as pd


class MissingResponseError(BaseException):
    pass

def res_col(ref, row, t):
    response = row[ref]

    if pd.isna(response):
        raise MissingResponseError(f'user missing response')

    return t(response)

def _res_col(ref, col_name, t, row):
    try:
        row[col_name] = res_col(ref, row, t)
    except MissingResponseError:
        logging.warning(f'User without {col_name}: {row.userid}')
        row[col_name] = None
    except BadResponseError:
        row[col_name] = None

    return row


def add_res_cols(new_cols, df):
    for col, ref, t in new_cols:
        df = df.apply(lambda r: _res_col(ref, col, t, r), axis=1)
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
        .apply(lambda df: add_res_cols([('cluster',
                                         reqs[df.shortcode.iloc[0]],
                                         lambda x: x)],
                                       df)) \
        .reset_index(drop=True)

def shape_df(df):
    df = df \
        .groupby(['surveyid', 'shortcode']) \
        .apply(lambda df: df.pivot('userid', 'question_ref', 'response')) \
        .reset_index()

    df['timestamp'] = df['md:startTime'].map(lambda x: datetime.fromtimestamp(x/1000, tz=timezone.utc))

    # Clean anyone who answered multiple surveys in this group of shortcodes
    # in theory should only be testers.
    # Keep the lastest survey they took.
    return df \
        .sort_values('timestamp') \
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


def get_budget_lookup(df, stratum, max_budget, days_left, window: BudgetWindow, spend: Dict[str, float]):
    surveys = stratum['surveys']

    # Get only target users and add cluster
    df = add_cluster(surveys, df)
    df = only_target_users(df, surveys, 'target_questions')

    # filter by time
    windowed = df[(df['md:startTime'] >= window.start_unix) & (df['md:startTime'] <= window.until_unix)]

    # see how many remaining in each cluster (all time)
    tot = df.groupby('cluster').userid.count().to_dict()
    tot = {**{k:0 for k in spend.keys()}, **tot}
    goal = stratum['per_cluster_pop']
    remain = {k: goal - v for k, v in tot.items()}

    # pretend to have found one in each cluster
    counts = windowed.groupby('cluster').userid.count().to_dict()
    counts = {**{k:1 for k in spend.keys()}, **counts}

    # filter out anything that hasn't been spent in the last day
    # TODO: Make this constraint explicit or get rid of it.
    # it means you can never increase the number of clusters
    price = {k: spend[k] / v for k, v in counts.items() if k in spend}
    budget = {k: v*remain[k] / days_left for k, v in price.items()}

    tot_price = sum(budget.values())
    if tot_price > max_budget:
        budget = {k:v/tot_price for k, v in budget.items()}
        budget = {k:v*max_budget for k, v in budget.items()}

    budget = {k: floor(v) for k, v in budget.items()}
    return budget
