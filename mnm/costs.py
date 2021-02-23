from datetime import datetime, timezone
import pandas as pd
import re
# from adopt.malaria import get_cluster_from_adset


def get_cluster_from_adset(adset_name: str) -> str:
    pat = r"(?<=vlab-)\w+"
    matches = re.search(pat, adset_name)
    if not matches:
        raise Exception(f"Cannot extract cluster id from adset: {adset_name}")

    return matches[0]

def prep_facebook_data(path, dd, final_clusters):
    capture_count = dd[(dd.timestamp > datetime(2020,7,23,tzinfo=timezone.utc)) &
                       (dd.timestamp < datetime(2020,7,24,tzinfo=timezone.utc))] \
        .groupby('disthash') \
        .userid.count() \
        .reset_index() \
        .rename(columns={'userid': 'completed_survey'})

    df = pd.read_csv(path)
    df['disthash'] = df['Ad Set Name'].map(get_cluster_from_adset)
    df = df.merge(capture_count, how='left')

    df = df[df.disthash.isin(final_clusters)].reset_index(drop=True)

    spend = 'Amount Spent (INR)'

    df['cost_per_completion'] = df.apply(lambda r: r[spend] / r.completed_survey, 1)
    df = df.rename(columns = {'CTR (All)': 'CTR',
                              'Cost per Results': 'cost_per_message',
                              'CPM (Cost per 1,000 Impressions) (INR)': 'CPM'})

    return df[['disthash', 'cost_per_completion', 'cost_per_message', 'CTR', 'CPM']]



# avg_mal = rdf[(rdf.wave == 0) & (rdf.variable == 'malaria2weeks')].groupby('clusterid').apply(lambda df: (df.translated_response == 'Yes').mean()).reset_index(name='avg_malaria2weeks')


# baselines = dd[dd.wave == 0] \
    #     .groupby('clusterid') \
    #     .agg({'under_net': 'mean', 'long_sleeves': 'mean'}) \
    #     .reset_index() \
    #     .rename(columns = {'under_net': 'avg_under_net', 'long_sleeves': 'avg_long_sleeves'})


# get dataframe for prep_facebook_data...
# just needs to be reponse df for july...
# def make_dist_info(df, dd, rdf, dist_stats):
#     costs = prep_facebook_data('outs/fb-export-vlab-1.csv', df.assign(disthash = df.clusterid), treatment_assignment.disthash)
#     costs = costs.rename(columns={'disthash': 'clusterid'})

#     costs['high_CPM'] = costs['CPM'] >= costs.CPM.quantile(0.5)
#     costs['low_CPM'] = costs['CPM'] <= costs.CPM.quantile(0.5)

#     dist_info = costs.merge(dist_stats.rename(columns={'disthash': 'clusterid'}))

#     return dist_info

# dist_info = make_dist_info(df, dd, rdf, dist_stats)
# dd = dd.merge(dist_info, on='clusterid')
# dist_info.to_csv('outs/dist_info.csv', index=False)
