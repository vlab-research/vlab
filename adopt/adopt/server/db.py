from typing import Any

import orjson
from environs import Env

from ..db import query

env = Env()
db_cnf = env("PG_URL")

# TODO: use asyncpg and pool for performance


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
