from typing import Any, Dict, List, Tuple

from .responses import query

DBConf = Dict[str, str]


def get_user_info(campaignid, cnf):
    # add system user?
    q = """
    SELECT
      details->>'access_token' as token,
      userid as survey_user
    FROM campaigns
    JOIN credentials
    USING (userid)
    WHERE campaigns.id = %s
    AND entity = 'facebook_ad_user'
    ORDER BY credentials.created DESC
    LIMIT 1
    """

    res = query(cnf, q, (campaignid,), as_dict=True)
    try:
        return next(res)
    except StopIteration as e:
        raise Exception(f"Could not find credentials for campaign id: {campaignid}")


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


def create_campaign_for_user(email, name, cnf: DBConf):
    q = """
       INSERT INTO  campaigns(name, userid)
       VALUES (%s, (SELECT id FROM users WHERE email = %s))
       RETURNING *
    """
    return list(query(cnf, q, (name, email), as_dict=True))[0]


def get_campaigns_for_user(email, cnf: DBConf):
    q = """
       SELECT id
       FROM campaigns
       WHERE userid = (SELECT id FROM users WHERE email = %s)
    """

    return list(query(cnf, q, (email,), as_dict=True))


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


def create_campaign_confs(
    campaignid: str, conf_type: str, dat: List[Dict[str, Any]], cnf: DBConf
):

    dats = [(campaignid, conf_type, t["entity_name"], t["conf"]) for t in dat]

    q = """
    INSERT INTO campaign_confs(campaignid, conf_type, entity_name, conf)
    VALUES(%s, %s, %s, %s)
    """

    list(query(cnf, q, dats, batch=True))
