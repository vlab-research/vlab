import logging

import geopandas as gpd
import pandas as pd

from adopt.responses import all_responses, get_all_forms

from .translation import translate_responses


def get_dist_info(path):
    """ Gets tot_p, total population per district """
    geod = gpd.read_file(path)
    district_info = (
        geod.groupby("disthash")
        .apply(lambda df: df.iloc[0][["disthash", "tot_p"]])
        .reset_index(drop=True)
    )
    return district_info


def add_form_metadata(forms, keys, df):
    form_lookup = {f["id"]: f for f in forms}
    for key in keys:
        df[key] = df.surveyid.map(lambda sid: form_lookup[sid]["metadata"].get(key))

    return df


def add_response_metadata(keys, df):
    for key in keys:
        df[key] = df.metadata.map(lambda x: x.get(key))
    return df


def pivot_response_df(df, metadata_keys, form_keys, extra_keys=[]):
    keys = ["userid"] + metadata_keys + form_keys + extra_keys

    # NOTE: we are dropping all duplicated users, these could
    # be testers or they could be sneaky devils that take
    # advantage of changes in form names, etc.
    duplicated_users = df[df.duplicated(subset=keys + ["question_ref"])].userid.unique()
    logging.warn(f"Removing {len(duplicated_users)} users for duplication")

    dd = (
        df[~df.userid.isin(duplicated_users)]
        .pivot(keys, "question_ref", "translated_response")
        .reset_index()
        .sort_values(["userid"])
    )
    return dd


def get_form_data(survey_names, db_conf):
    forms = list(get_all_forms(survey_names, db_conf))
    form_keys = {k for f in forms for k in f["metadata"].keys()}
    return forms, list(form_keys)


def get_response_data(forms, db_conf):
    responses = all_responses({f["shortcode"] for f in forms}, db_conf)
    return pd.DataFrame(list(responses))


def wrap_empty(fn):
    def _wrapper(df):
        if df.shape[0] == 0:
            return None
        return fn(df)

    return _wrapper


def _add_time_indicators(rdf):
    rdf = (
        rdf.set_index("timestamp")
        .resample("1m")
        .apply(wrap_empty(lambda df: df.assign(month=df.index[0].month)))
        .reset_index(level=1)
        .reset_index(drop=True)
    )
    rdf = (
        rdf.set_index("timestamp")
        .resample("1w")
        .apply(wrap_empty(lambda df: df.assign(week=df.index[0].week)))
        .reset_index(level=1)
        .reset_index(drop=True)
    )

    return rdf


def format_response_df(rdf, forms, form_keys, metadata_keys, tester_key):
    rdf = add_form_metadata(forms, form_keys, rdf)

    # Add metadata from responses themselves
    rdf = add_response_metadata(metadata_keys, rdf)

    # Remove testers
    testers = rdf[rdf[tester_key].isna()].userid.unique()
    rdf = rdf[~rdf.userid.isin(testers)].reset_index(drop=True)
    logging.warn(f"Removing {len(testers)} possible test users")

    if rdf.shape[0] == 0:
        return rdf

    rdf = _add_time_indicators(rdf)
    return rdf


def get_response_df(survey_names, db_conf, metadata_keys, tester_key):
    forms, form_keys = get_form_data(survey_names, db_conf)
    rdf = get_response_data(forms, db_conf)
    rdf = format_response_df(rdf, forms, form_keys, metadata_keys, tester_key)
    return pivot_response_df(rdf, metadata_keys, form_keys, ["week", "month"])


def cast_number(mn, mx, n):
    try:
        f = int(n)
        if f < mn or f > mx:
            return None
        return f
    except ValueError:
        return None


def _add_bednet_share(df):
    members = df.iloc[0].familymembers

    if members:
        df["bednet_share"] = df.membersbednet / members

        # give some people a break if they are
        # sometimes a bit over?
        # _ = (df.bednet_share > 1.0).sum()

    return df


def add_bednet_share(df):
    return (
        df.assign(
            membersbednet=df.membersbednet.map(lambda x: cast_number(0, 30, x)).astype(
                float
            )
        )
        .assign(
            familymembers=df.familymembers.map(lambda x: cast_number(0, 30, x)).astype(
                float
            )
        )
        .sort_values("week")
        .groupby("userid")
        .apply(_add_bednet_share)
    )


def get_response_df_round_a(survey_name, formcentral_url, db_conf):
    forms, form_keys = get_form_data(survey_name, db_conf)
    responses = list(all_responses({f["shortcode"] for f in forms}, db_conf))
    translated_responses = translate_responses(
        db_conf, forms, formcentral_url, responses
    )

    rdf = pd.DataFrame(translated_responses)
    df = format_response_df(rdf, forms, form_keys, ["clusterid"], "clusterid")
    df = df[df.question_ref.notna()]
    tried_twice = df[
        df.duplicated(
            [
                "userid",
                "wave",
                "version",
                "language",
                "clusterid",
                "week",
                "month",
                "question_ref",
            ]
        )
    ].userid.unique()
    df = df[~df.userid.isin(tried_twice)]

    rdf = pivot_response_df(df, ["clusterid"], form_keys, ["week", "month", "surveyid"])
    rdf["wave"] = rdf.wave.astype(int)

    rdf = add_bednet_share(rdf)

    return rdf
