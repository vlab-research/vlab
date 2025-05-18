import json
from typing import Any

import orjson
from environs import Env
from fastapi import HTTPException

from ..db import execute, query

env = Env()
db_cnf = env("PG_URL")

# TODO: use asyncpg and pool for performance


def insert_credential(user_id: str, entity: str, key: str, details: Any):
    q = """
    INSERT INTO credentials (user_id, entity, key, details) VALUES (%s, %s, %s, %s)
"""

    deets = orjson.dumps(details).decode("utf8")
    execute(db_cnf, q, (user_id, entity, key, deets))


def get_study_conf(user_id: str, org_id: str, study_slug: str, conf_type: str):
    q = """
    SELECT conf
    FROM study_confs sc
    JOIN studies s on sc.study_id = s.id
    JOIN orgs_lookup ol on ol.org_id = s.org_id
    JOIN users u on ol.user_id = u.id
    WHERE u.id = %s
    AND s.org_id = %s
    AND s.slug = %s
    AND conf_type = %s
    ORDER BY sc.created DESC
    LIMIT 1
    """

    res = query(db_cnf, q, (user_id, org_id, study_slug, conf_type), as_dict=True)
    try:
        return list(res)[0]["conf"]
    except IndexError:
        raise Exception(
            f"Could not find study config for user {user_id},"
            f" org {org_id}, study {study_slug}, and config {conf_type}"
        )


def get_all_study_confs(user_id: str, org_id: str, study_slug: str):
    q = """
    with t AS (
               SELECT *,
               ROW_NUMBER() OVER
                 (PARTITION BY conf_type ORDER BY sc.created DESC)
               as n
               FROM study_confs sc
               JOIN studies s on sc.study_id = s.id
               JOIN orgs_lookup ol on ol.org_id = s.org_id
               JOIN users u on ol.user_id = u.id
               WHERE u.id = %s
               AND s.org_id = %s
               AND s.slug = %s
    ) SELECT conf_type, conf FROM t WHERE n = 1;
    """

    res = query(db_cnf, q, (user_id, org_id, study_slug), as_dict=True)
    try:
        confs = {d["conf_type"]: d["conf"] for d in res}
        return confs
    except IndexError:
        raise Exception(
            f"Could not find study configs for user {user_id},"
            f" org {org_id}, study {study_slug}"
        )


def get_study_id(user_id: str, org_id: str, study_slug: str):
    q = """
    SELECT s.id
    FROM studies s
    JOIN orgs_lookup ol on ol.org_id = s.org_id
    JOIN users u on ol.user_id = u.id
    WHERE u.id = %s
    AND s.org_id = %s
    AND s.slug = %s
    LIMIT 1
    """

    res = query(db_cnf, q, (user_id, org_id, study_slug), as_dict=True)
    try:
        return list(res)[0]["id"]
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Study not found: {study_slug}")


def create_study_conf(
    user_id: str,
    org_id: str,
    study_slug: str,
    conf_type: str,
    dat: list[dict[str, Any]],
):
    dats = (user_id, org_id, study_slug, conf_type, orjson.dumps(dat).decode("utf8"))

    q = """
    INSERT INTO study_confs(study_id, conf_type, conf)
    VALUES(
    (SELECT s.id
     FROM studies s
     JOIN orgs_lookup ol on ol.org_id = s.org_id
     JOIN users u on ol.user_id = u.id
     WHERE u.id = %s
     AND s.org_id = %s
     AND s.slug = %s),
    %s,
    %s)
    RETURNING *
    """

    res = query(db_cnf, q, dats, as_dict=True)
    try:
        return list(res)[0]
    except IndexError:
        raise Exception(
            f"Could not find study for user {user_id},"
            f" org {org_id}, study {study_slug}"
        )


def copy_confs(user_id: str, org_id: str, slug: str, source_study_slug: str):
    q = """
    with t AS (
               SELECT *,
               ROW_NUMBER() OVER
                 (PARTITION BY conf_type ORDER BY sc.created DESC)
               as n
               FROM study_confs sc
               JOIN studies s on sc.study_id = s.id
               JOIN orgs_lookup ol on ol.org_id = s.org_id
               JOIN users u on ol.user_id = u.id
               WHERE u.id = %s
               AND s.org_id = %s
               AND s.slug = %s
    )
    INSERT INTO study_confs(study_id, conf_type, conf)
    SELECT (SELECT id FROM studies WHERE slug = %s), conf_type, conf
    FROM t
    WHERE n = 1
    AND conf_type != 'general'
    RETURNING conf_type, conf
    """

    res = query(db_cnf, q, (user_id, org_id, source_study_slug, slug), as_dict=True)
    rr = list(res)
    if not rr:
        message = f"Could not copy configuration from {source_study_slug} to {slug}. Potentially there is no configuration to copy?"
        raise HTTPException(status_code=404, detail=message)

    return {d["conf_type"]: d["conf"] for d in rr}
