from toolz import curry

def res_col(ref, df):
    try:
        response = df[df.question_ref == ref].response.iloc[0]
    except IndexError:
        raise Exception(f'Could not find question with ref {ref}')

    return response

def _res_col(ref, col_name, df):
    df[col_name] = res_col(ref, df)
    return df

def get_unsaturated_clusters(df, cluster_ref, is_saturated):
    clusters = df \
        .groupby('userid') \
        .apply(lambda df: _res_col(cluster_ref, 'cluster', df)) \
        .groupby('cluster') \
        .filter(lambda df: not is_saturated(df)) \
        ['cluster'] \
        .unique()

    return clusters

def users_fulfilling(reqs, df):
    for ref, pred in reqs:
        try:
            d = df[df.question_ref == ref]
            d = d[d.response.map(pred)]
            users = d.userid.unique()
            df = df[df.userid.isin(users)]
        except AttributeError:
            return []
    return users.tolist()

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

def all_users_fulfilling(surveys, df):
    return [u for s in surveys
            for u in users_fulfilling(make_reqs(s['target_questions']),
                                      df[df.shortcode == s['shortcode']])]

@curry
def is_saturated(cnf, df):
    s = cnf['stratum']
    users = all_users_fulfilling(s['surveys'], df)
    return len(users) >= s['per_cluster_pop']
