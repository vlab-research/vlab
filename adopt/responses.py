import json
from datetime import datetime
from functools import lru_cache

import pandas as pd
import psycopg2
from toolz import dissoc


def query(cnf, q, vals=(), as_dict=False):
    with psycopg2.connect(
        dbname=cnf["db"],
        user=cnf["user"],
        host=cnf["host"],
        port=cnf["port"],
        password=cnf["password"],
    ) as conn:

        with conn.cursor() as cur:
            cur.execute(q, vals)
            column_names = [desc[0] for desc in cur.description]
            for record in cur:
                if as_dict:
                    yield dict(zip(column_names, record))
                else:
                    yield record

            # surveyid VARCHAR NOT NULL,
            # shortcode VARCHAR,
            # userid VARCHAR NOT NULL,
            # question_ref VARCHAR NOT NULL,
            # response VARCHAR NOT NULL,
            # metadata JSONB,
            # timestamp TIMESTAMPTZ NOT NULL


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


def get_all_forms(survey_name, cnf):
    q = """
    SELECT id, metadata, form_json, created, shortcode
    FROM surveys
    WHERE survey_name = %s
    """

    res = query(cnf, q, (survey_name,), as_dict=True)
    return res


def temp_translation_target(surveyid, cnf):
    q = """
    WITH t AS
      (SELECT created,
              survey_name,
              form_json,
              translation_conf,
              jsonb_set(metadata,
                        ARRAY['language'],
                        '"english"') AS ref_metadata
       FROM surveys
       WHERE id = %s
       LIMIT 1)
    SELECT surveys.id AS dest, surveys.shortcode AS shortcode, surveys.form_json as dest_form, t.form_json as form_json
    FROM t
    LEFT JOIN surveys
    ON t.survey_name = surveys.survey_name
    AND t.ref_metadata = surveys.metadata
    ORDER BY surveys.created
    LIMIT 1
    """

    res = query(dict(cnf), q, (surveyid,), as_dict=True)
    return next(res)


@lru_cache(maxsize=512)
def _get_translation_form(surveyid, cnf):
    q = """
    WITH t AS
      (SELECT created,
              form_json,
              survey_name,
              translation_conf,
              jsonb_set(metadata,
                        ARRAY[(translation_conf->>'field')],
                        translation_conf->'reference') AS ref_metadata
       FROM surveys
       WHERE id = %s
       LIMIT 1)
    SELECT surveys.form_json AS target_form, t.form_json AS source_form
    FROM t
    LEFT JOIN surveys
    ON t.survey_name = surveys.survey_name
    AND t.ref_metadata = surveys.metadata
    ORDER BY surveys.created
    LIMIT 1
    """

    res = query(dict(cnf), q, (surveyid,), as_dict=True)
    return next(res)


def get_translation_form(surveyid, cnf):
    return _get_translation_form(surveyid, frozenset(cnf.items()))


def all_responses(shortcodes, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY question_ref, userid, surveyid ORDER BY timestamp DESC) as n
      FROM responses
      WHERE shortcode in %s
    )
    SELECT metadata, userid, surveyid, shortcode, question_ref, response, timestamp FROM t WHERE n = 1
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (shortcodes,), as_dict=True)
    return res


def last_responses(surveyids, questions, cnf):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY question_ref, userid, surveyid ORDER BY timestamp DESC) as n
      FROM responses
      WHERE question_ref in %s
      AND surveyid in %s
    )
    SELECT userid, surveyid, shortcode, question_ref, response, translated_response, timestamp FROM t WHERE n = 1
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
    WHERE surveyid in %s
    ORDER BY surveyid, timestamp DESC
    """

    shortcodes = tuple(shortcodes)
    res = query(cnf, q, (shortcodes), as_dict=True)
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


def get_response_df(survey_user, shortcodes, questions, database_cnf):

    surveyids = get_surveyids(shortcodes, survey_user, database_cnf)

    responses = last_responses(surveyids, questions, database_cnf)

    df = pd.DataFrame(list(responses))

    if df.shape[0] == 0:
        print(
            f"Warning: no responses were found in the database \
        for shortcodes: {shortcodes} and questions: {questions}"
        )
        return None

    # add synthetic district responses
    md = get_metadata(surveyids, database_cnf)
    md = pd.DataFrame(md)

    # could remove original district questions...
    df = pd.concat([md, df]).reset_index(drop=True)

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
