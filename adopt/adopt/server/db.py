import json
import logging
from typing import Any

import orjson
import psycopg
from environs import Env
from fastapi import HTTPException

from ..db import execute, query

env = Env()
db_cnf = env("PG_URL")

# TODO: use asyncpg and pool for performance


def get_study_errors(study_id: str):
    """Derive the current open errors for a study from study_run_events.

    The event log is the source of truth; this query is the Phase 1 derivation
    from planning/study-errors-surfacing.md: latest event per (source,
    fingerprint), kept when it is an error/warning still inside the recency
    window. The recency predicate is the dead-man's switch — an error that
    stops being re-emitted (e.g. a fixed extraction problem) ages out without
    the writer having to close it. 90 minutes = 3x the 30-min swoosh cron.
    """
    q = """
    WITH latest AS (
      SELECT DISTINCT ON (source, fingerprint)
             source, fingerprint, event_type, severity, message, details,
             occurred_at AS last_seen
      FROM study_run_events
      WHERE study_id = %s
      ORDER BY source, fingerprint, occurred_at DESC
    ),
    open_errors AS (
      SELECT *
      FROM latest
      WHERE severity IN ('error', 'warning')
        AND last_seen > now() - INTERVAL '90 minutes'
    ),
    first_seen AS (
      SELECT source, fingerprint, min(occurred_at) AS first_seen
      FROM study_run_events
      WHERE study_id = %s
        AND severity IN ('error', 'warning')
      GROUP BY source, fingerprint
    )
    SELECT o.source, o.fingerprint, o.severity, o.message, o.details,
           o.last_seen, f.first_seen
    FROM open_errors o
    JOIN first_seen f ON f.source = o.source AND f.fingerprint = o.fingerprint
    -- errors before warnings: bare "severity DESC" would sort alphabetically
    -- ('warning' > 'error'), which is not the display priority.
    ORDER BY CASE o.severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
             o.last_seen DESC
    """

    try:
        return list(query(db_cnf, q, (study_id, study_id), as_dict=True))
    except psycopg.errors.UndefinedTable:
        # study_run_events migration not applied in this env — degrade to
        # "no errors" rather than 500. The dashboard must never break
        # because the events table isn't there yet.
        logging.warning("study_run_events table missing; returning no errors")
        return []


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
