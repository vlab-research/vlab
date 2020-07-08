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

@curry
def is_saturated(reqs, lim, df):
    users = users_fulfilling(reqs, df)
    return len(users) >= lim


# IDEATION: distribution target
# get histogram of responses to Y.
# compare to target
# create lookalike that makes up difference (only response which is most underrepresented)
