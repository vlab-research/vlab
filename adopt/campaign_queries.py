from typing import Any, Dict, List

from .responses import query

DBConf = Dict[str, str]


def get_user_info(campaignid, cnf):
    q = """
    with t as (SELECT userid FROM campaigns WHERE id = %s)
    SELECT (SELECT details->>'token' as token
            FROM t
            JOIN credentials
            USING (userid)
            WHERE entity = 'facebook_ad_user'
            ORDER BY created DESC
            LIMIT 1) as token,
            t.userid as survey_user,
            pageid,
            instagramid
    FROM t
    JOIN facebook_pages
    USING (userid);
    """

    res = query(cnf, q, (campaignid,), as_dict=True)
    return next(res)


def get_pageid(survey_user, cnf):
    q = """
    SELECT pageid, instagramid
    FROM facebook_pages
    WHERE userid = %s
    LIMIT 1;
    """

    res = query(cnf, q, (survey_user,))
    return next(res)


def get_campaigns(cnf: DBConf):
    q = """
    SELECT id FROM campaigns
    """

    return [r["id"] for r in query(cnf, q, as_dict=True)]


def get_campaign_configs(campaignid, cnf: DBConf):
    q = """
    with t AS (
               SELECT *,
               ROW_NUMBER() OVER
                 (PARTITION BY conf_type, entity_name ORDER BY created DESC)
               as n
               FROM campaign_confs
               WHERE campaignid = %s
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
       FROM campaigns
       WHERE userid = (SELECT id FROM users WHERE email = %s)
       AND name = %s),
     {placeholders})
    """

    return q


def create_campaign_confs(dat: List[Any], cnf: DBConf):
    q = _insert_query(
        "campaign_confs", ["campaignid", "conf_type", "entity_name", "conf"]
    )
    list(query(cnf, q, dat, batch=True))
