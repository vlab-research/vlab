import json
from datetime import datetime
from typing import Optional

import pandas as pd
from toolz import dissoc

from .db import query


def get_surveyids(shortcodes, userid, cnf):
    q = """
      SELECT id
      FROM surveys
      WHERE shortcode in %s
      AND userid = %s
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (shortcodes, userid), as_dict=True)
    return [r["id"] for r in res]


def all_responses(shortcodes, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY question_ref, userid, surveyid
                           ORDER BY timestamp DESC) as n
      FROM responses
      WHERE shortcode in %s
    )
    SELECT metadata, userid, surveyid, shortcode, question_ref,
           response, timestamp, translated_response
    FROM t WHERE n = 1
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (shortcodes,), as_dict=True)
    return res


def last_responses(surveyids, questions, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY question_ref, userid, surveyid
                           ORDER BY timestamp DESC) as n
      FROM responses
      WHERE question_ref in %s
      AND surveyid in %s
    )
    SELECT userid, surveyid, shortcode, question_ref,
           response, translated_response, timestamp
    FROM t
    WHERE n = 1
    """

    surveyids = tuple(surveyids)
    questions = tuple(questions)
    res = query(cnf, q, (questions, surveyids), as_dict=True)
    return res


def get_metadata(surveyids, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY userid, surveyid ORDER BY timestamp DESC) as n
      FROM responses
      WHERE surveyid in %s
    )
    SELECT userid, surveyid, shortcode, metadata FROM t WHERE n = 1
    """

    surveyids = tuple(surveyids)
    res = query(cnf, q, (surveyids,), as_dict=True)
    res = (
        {**r, "question_ref": f"md:{k}", "response": v}
        for r in res
        for k, v in r["metadata"].items()
        if r.get("metadata")
    )

    return (dissoc(d, "metadata") for d in res)


def get_survey(surveyid, cnf):
    q = """
    SELECT form
    FROM surveys
    WHERE id = %s
    """

    # shortcodes = tuple(surveyids)
    res = query(cnf, q, (surveyid), as_dict=True)
    res = next(r["form"] for r in res)
    return json.loads(res)


def get_all_responses(shortcodes, cnf):
    q = """
    SELECT *
    FROM responses
    WHERE shortcode in %s
    ORDER BY surveyid, timestamp DESC
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (shortcodes,), as_dict=True)
    return res


def get_forms(survey_user, shortcodes, timestamp, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY shortcode) as n
      FROM surveys
      WHERE userid = %s
      AND shortcode in %s
      AND created <= %s
      ORDER BY created DESC
    )
    SELECT form
    FROM t
    WHERE n = 1
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (survey_user, shortcodes, timestamp), as_dict=True)
    res = (r["form"] for r in res)
    return (json.loads(r) for r in res)


def get_inference_data(survey_user, study_id, database_cnf) -> Optional[pd.DataFrame]:
    q = """
    select variable, value_type, value, timestamp
    from inference_data
    where user_id = %s
    and study_id = %s
    """

    res = query(database_cnf, q, [survey_user, study_id], as_dict=True)
    dat = list(res)
    if not dat:
        print(
            f"Warning: no responses were found in the database \
            for study_id: {study_id}"
        )
        return None

    return pd.DataFrame(dat)


def get_response_df(survey_user, shortcodes, questions, database_cnf):

    surveyids = get_surveyids(shortcodes, survey_user, database_cnf)

    responses = last_responses(surveyids, questions, database_cnf)
    df = pd.DataFrame(list(responses))

    # add synthetic district responses
    md = get_metadata(surveyids, database_cnf)
    md = pd.DataFrame(md)

    # could remove original district questions...
    df = pd.concat([md, df]).reset_index(drop=True)

    if df.shape[0] == 0:
        print(
            f"Warning: no responses were found in the database \
        for shortcodes: {shortcodes} and questions: {questions}"
        )

        return None

    return df


def format_synthetic(responses, ref, description):
    # responses:
    # iterable of dictionaries with the following keys:
    # parent_survey_id, parent_shortcode, surveyid, shortcode, userid, seed, response

    new_values = {
        "question_text": description,
        "question_ref": ref,
        "timestamp": datetime.utcnow(),  # TODO: timezone?
        "flowid": 0,
        "question_idx": None,
    }

    return ({**r, **new_values} for r in responses)
