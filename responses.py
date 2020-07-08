import psycopg2
import pandas as pd
from datetime import datetime

def query(dbname, user, query, vals = (), as_dict=False):
    with psycopg2.connect(dbname=dbname, user=user, host='localhost', port='5432') as conn:
        with conn.cursor() as cur:
            cur.execute(query, vals)
            column_names = [desc[0] for desc in cur.description]
            for record in cur:
                if as_dict:
                    yield dict(zip(column_names, record))
                else:
                    yield record

def last_responses(surveyid, questions, dbname, user):
    q = """
    WITH t AS (
      SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY question_ref, userid ORDER BY timestamp DESC) as n
      FROM responses
      WHERE question_ref in %s
      AND surveyid = %s
    )
    SELECT * FROM t WHERE n = 1 LIMIT 200
    """

    questions = tuple(questions)
    res = query(dbname, user, q, (questions, surveyid), as_dict=True)
    return res


def format_synthetic(responses, ref, description):
    # responses:
    # iterable of dictionaries with the following keys:
    # parent_survey_id, parent_shortcode, surveyid, shortcode, userid, seed, response

    new_values = {
        'question_text': description,
        'question_ref': ref,
        'timestamp': datetime.utcnow(), # TODO: timezone?
        'flowid': 0,
        'question_idx': None,
    }

    return ({**r, **new_values} for r in responses)
