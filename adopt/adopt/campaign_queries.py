import json
from typing import Any, Dict, List, Union

import orjson

from .responses import query

DBConf = str

AdOptReport = Dict[str, Dict[str, Union[int, float]]]


def get_user_info(study_id, cnf):
    q = """
    with t as (
    SELECT
      studies.user_id,
      sc.conf->>'credentials_key' as credentials_key,
      sc.conf->>'credentials_entity' as credentials_entity
    FROM studies
    JOIN study_confs sc
    ON studies.id = sc.study_id
    WHERE studies.id = %s
    AND sc.conf_type = 'general'
    )
    SELECT
      details->>'access_token' as token,
      t.user_id as survey_user
    FROM t
    join credentials c
      ON t.credentials_key = c.key
      AND c.user_id = t.user_id
    ORDER BY c.created DESC
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


def create_campaign_for_user(id_, name, cnf: DBConf, key):
    # TODO: this makes name = slug!
    q = """
       INSERT INTO studies(name, slug, user_id, credentials_key)
       VALUES (%s, %s, %s, %s)
       RETURNING *
    """
    return list(query(cnf, q, (name, name, id_, key), as_dict=True))[0]


def get_campaigns_for_user(id_, cnf: DBConf):
    q = """
       SELECT *
       FROM studies
       WHERE user_id = %s
    """

    return list(query(cnf, q, (id_,), as_dict=True))


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
       WHERE user_id = %s
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
