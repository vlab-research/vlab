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


# --------------------------------------------------------------------------
# Facebook credentials, for the Meta Graph proxy (`server/meta.py`)
# --------------------------------------------------------------------------

# The `entity` values a Facebook access token is stored under. There are two,
# and the split is historical rather than meaningful:
#
#   * `facebook` — what the dashboard's OAuth exchange writes
#     (`api/internal/storage/account.go`, entity = the account's auth type),
#     and what the General form hardcodes into every `general` conf
#     (`dashboard/.../forms/general/General.tsx:26`).
#   * `facebook_ad_user` — the DEFAULT of the vestigial
#     `studies.credentials_entity` column
#     (`devops/migrations/20230322111807_init.up.sql:12`), and the entity real
#     production rows are under (e.g. the `virtual-lab-vlab` credential in
#     `planning/encoded-ref-probe-runbook.md:524`).
#
# Nothing in the running system has ever had to agree on which is right,
# because the one query that resolves a token — `get_user_info`
# (`adopt/campaign_queries.py:13`) — selects `credentials_entity` out of the
# general conf and then never uses it in the join. Both are accepted here for
# the same reason: refusing either would hide a credential a study is
# demonstrably using.
FACEBOOK_CREDENTIAL_ENTITIES = ("facebook", "facebook_ad_user")


def list_facebook_credentials(user_id: str):
    """The caller's Facebook credentials, WITHOUT their tokens.

    Rows without an `access_token` are excluded: `get_user_info` reads exactly
    that field, so a row lacking it cannot authenticate anything and offering
    it as a choice would only produce a confusing failure later. (The dev seed
    at `devops/seeds/20230405094547_credentials.up.sql:28` is such a row — it
    stores `{"token": ...}` — which is why this is a real case and not a
    hypothetical one.)

    `credentials` is user-scoped, not org-scoped: the `org_id` column added by
    the organisation migration is never populated by the Go account-create
    path. So there is no org filter here, and the org segment in the route is
    a membership check, not a partition of the data.
    """
    q = """
    SELECT key, entity, created
    FROM credentials
    WHERE user_id = %s
    AND entity = ANY(%s)
    AND details ->> 'access_token' IS NOT NULL
    ORDER BY created DESC
    """
    return list(
        query(db_cnf, q, (user_id, list(FACEBOOK_CREDENTIAL_ENTITIES)), as_dict=True)
    )


def get_facebook_token(user_id: str, credentials_key: str):
    """The access token for one named credential, or None.

    Matched on `(user_id, key)` with the entity deliberately NOT in the
    predicate. That is not sloppiness — it is bug-compatibility with
    `get_user_info`, which is what actually resolves the token when adopt talks
    to Meta on this study's behalf. If this query were stricter than that one,
    the proxy could report "no such credential" for a key that a study is
    happily running on, or — worse — resolve a *different* row and show the
    agent an ad-account list the study will never be able to use.

    `ORDER BY created DESC LIMIT 1` is likewise `get_user_info`'s tie-break.
    `unique_entity_key_per_user` makes a tie possible only across entities
    (same name under `facebook` and `facebook_ad_user`), and newest-wins is
    what the run-time path already does with that.
    """
    q = """
    SELECT details ->> 'access_token' AS token
    FROM credentials
    WHERE user_id = %s
    AND key = %s
    AND details ->> 'access_token' IS NOT NULL
    ORDER BY created DESC
    LIMIT 1
    """
    rows = list(query(db_cnf, q, (user_id, credentials_key), as_dict=True))
    return rows[0]["token"] if rows else None


def user_in_org(user_id: str, org_id: str) -> bool:
    """Membership, as a standalone check.

    Every other route in this service gets membership for free by joining
    `orgs_lookup` on the way to a study. The Meta routes have no study to join
    through, so the check has to be its own query.
    """
    q = """
    SELECT 1
    FROM orgs_lookup
    WHERE user_id = %s
    AND org_id = %s
    LIMIT 1
    """
    return bool(list(query(db_cnf, q, (user_id, org_id))))


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


def create_study(user_id: str, org_id: str, name: str, slug: str):
    """Create a study row, owned by `user_id` and scoped to `org_id`.

    This is the Python port of the Go dashboard API's `CreateStudy`
    (`api/internal/storage/study.go`), which until now was the only way to
    bring a study into existence and is Auth0-only — so an API key could
    configure a study but not create one. See planning/agent-study-authoring.md
    §2.3 and Appendix A.1; the Go semantics are the spec here, because every
    live study was created through them.

    Two traps, both recorded in Appendix A.1/A.2, both of which the *other*
    Python implementation (`create_campaign_for_user`,
    `adopt/campaign_queries.py:66`) gets wrong:

    1. `org_id` is not optional. Every conf endpoint reaches a study through
       `JOIN orgs_lookup ol ON ol.org_id = s.org_id AND s.org_id = %s` (see
       `get_study_id` and `get_study_conf` above). A study row with a NULL
       `org_id` is therefore invisible to all of them: creatable, and then
       never configurable. `create_campaign_for_user` never sets it.

    2. `credentials_key` stays NULL. The column and its FK to
       `credentials(user_id, entity, key)` are vestigial on the modern path —
       Facebook credentials are resolved from the *general* study conf by
       `get_user_info` (`adopt/campaign_queries.py:13`), not from this column.
       Writing a key here fails the FK unless a matching credentials row
       already exists, and buys nothing. Leaving it NULL satisfies the FK
       vacuously, exactly as the Go path does.

    Authorisation is the INSERT itself. The row is built by selecting from
    `orgs_lookup`, so a user who is not a member of `org_id` simply matches no
    rows and nothing is written — there is no window between an "am I a
    member?" check and the write in which membership could be revoked. That is
    the same membership rule the read paths above enforce, expressed as a
    write.

    Returns the created row, or None if the caller is not a member of the org.
    Raises psycopg.errors.UniqueViolation on `unique_name`/`unique_slug`; both
    are per-USER, not per-org, and the caller maps them to 409.
    """
    q = """
    INSERT INTO studies (slug, name, user_id, org_id)
    SELECT %s, %s, ol.user_id, ol.org_id
    FROM orgs_lookup ol
    WHERE ol.user_id = %s
    AND ol.org_id = %s
    RETURNING id, name, slug, created
    """

    res = query(db_cnf, q, (slug, name, user_id, org_id), as_dict=True)
    rows = list(res)
    if not rows:
        return None
    return rows[0]


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
    # The destination is resolved through get_study_id, which scopes by user and
    # org, rather than inline in the INSERT.
    #
    # It used to be `(SELECT id FROM studies WHERE slug = %s)` — no user, no org,
    # no LIMIT — while `slug` comes straight off the request path and is unique
    # only per user (`unique_slug UNIQUE(user_id, slug)`). Naming a slug you did
    # not own therefore copied your configuration *into someone else's study*,
    # and two users sharing a slug failed instead on a multi-row subquery. The
    # source side above was always scoped correctly, which is what made the
    # asymmetry easy to miss.
    destination_study_id = get_study_id(user_id, org_id, slug)

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
    SELECT %s, conf_type, conf
    FROM t
    WHERE n = 1
    AND conf_type != 'general'
    RETURNING conf_type, conf
    """

    res = query(
        db_cnf,
        q,
        (user_id, org_id, source_study_slug, destination_study_id),
        as_dict=True,
    )
    rr = list(res)
    if not rr:
        message = f"Could not copy configuration from {source_study_slug} to {slug}. Potentially there is no configuration to copy?"
        raise HTTPException(status_code=404, detail=message)

    return {d["conf_type"]: d["conf"] for d in rr}
