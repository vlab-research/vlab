import json
from typing import Any, Dict, List, Tuple

import orjson

from .clustering import AdOptReport
from .responses import query

DBConf = str


def get_user_info(study_id, cnf):
    q = """
    SELECT
      details->>'access_token' as token,
      studies.user_id as survey_user
    FROM studies
    JOIN credentials
    ON studies.user_id = credentials.user_id
    AND studies.credentials_entity = credentials.entity
    AND studies.credentials_key = credentials.key
    WHERE studies.id = %s
    ORDER BY credentials.created DESC -- not currently used!
    LIMIT 1
    """

    res = query(cnf, q, (study_id,), as_dict=True)
    try:
        return next(
            ({"token": u["token"], "survey_user": str(u["survey_user"])} for u in res)
        )
    except StopIteration:
        raise Exception(f"Could not find credentials for study id: {study_id}")


def get_pageid(survey_user, cnf):
    q = """
    SELECT pageid, instagramid
    FROM facebook_pages
    WHERE user_id = %s
    LIMIT 1;
    """

    res = query(cnf, q, (survey_user,))
    return next(res)


def get_campaigns(cnf: DBConf):
    q = """
    SELECT id FROM studies
    """

    return [r["id"] for r in query(cnf, q, as_dict=True)]


def create_campaign_for_user(email, name, cnf: DBConf, key):
    q = """
       INSERT INTO studies(name, user_id, credentials_key)
       VALUES (%s, (SELECT id FROM users WHERE email = %s), %s)
       RETURNING *
    """
    return list(query(cnf, q, (name, email, key), as_dict=True))[0]


def get_campaigns_for_user(email, cnf: DBConf):
    q = """
       SELECT *
       FROM studies
       WHERE user_id = (SELECT id FROM users WHERE email = %s)
    """

    return list(query(cnf, q, (email,), as_dict=True))


def get_campaign_configs(campaignid, cnf: DBConf):
    q = """
    with t AS (
               SELECT *,
               ROW_NUMBER() OVER
                 (PARTITION BY conf_type ORDER BY created DESC)
               as n
               FROM study_confs
               WHERE study_id = %s
    ) SELECT conf_type, conf FROM t WHERE n = 1;
    """

    res = query(cnf, q, (campaignid,), as_dict=True)
    return list(res)


def _insert_query(table, cols):
    placeholders = ",".join(["%s"] * (len(cols) - 1))
    q = f"""
    INSERT INTO {table}({','.join(cols)})
    VALUES(
      (SELECT id
       FROM studies
       WHERE user_id = (SELECT id FROM users WHERE email = %s)
       AND name = %s),
     {placeholders})
    """

    return q


def create_campaign_confs(
    campaignid: str, conf_type: str, dat: List[Dict[str, Any]], cnf: DBConf
):

    dats = (campaignid, conf_type, orjson.dumps(dat).decode("utf8"))

    q = """
    INSERT INTO study_confs(study_id, conf_type, conf)
    VALUES(%s, %s, %s)
    RETURNING *
    """

    return list(query(cnf, q, dats))[0]


def create_adopt_report(
    study_id: str, report_type: str, details: AdOptReport, cnf: DBConf
):
    q = """
    INSERT INTO adopt_reports(study_id, report_type, details)
    VALUES(%s, %s, %s)
    RETURNING *
    """

    return list(query(cnf, q, (study_id, report_type, json.dumps(details))))[0]


def get_last_adopt_report(campaignid: str, report_type: str, cnf: DBConf):
    q = """
    SELECT details
    FROM adopt_reports
    WHERE campaignid = %s
    AND report_type = %s
    ORDER BY created DESC
    LIMIT 1
    """

    return list(query(cnf, q, (campaignid, report_type)))[0][0]
