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

    Matched on `(user_id, key, entity IN facebook-ish)`. Two halves, and both
    of them matter:

    * **`key`, not `(entity, key)`.** This is bug-compatibility with
      `get_user_info`, which is what actually resolves the token when adopt
      talks to Meta on a study's behalf: it selects `credentials_entity` out of
      the general conf and then never joins on it. If this query were stricter
      than that one, the proxy could report "no such credential" for a key a
      study is happily running on, or resolve a *different* row and show the
      agent an ad-account list the study can never use. Since both entities
      that carry a Facebook token in production are in
      `FACEBOOK_CREDENTIAL_ENTITIES`, the entity set below does not narrow
      anything `get_user_info` would have found.

    * **The entity set is still applied**, because `credentials` holds tokens
      for other providers too (`typeform`, `fly`, `whatsapp_business`, …) and
      several of those also store a field called `access_token`. Without this
      predicate, `?credentials_key=<name of my typeform credential>` would ship
      that token to graph.facebook.com — the caller's own token, so not a
      cross-tenant leak, but a credential sent to a third party that has no
      business seeing it. It would also make the 404's "Available:" list a lie,
      since that list comes from `list_facebook_credentials`, which has always
      filtered on entity: the two queries have to accept the same rows or the
      error message contradicts the lookup.

    `ORDER BY created DESC LIMIT 1` is likewise `get_user_info`'s tie-break.
    `unique_entity_key_per_user` makes a tie possible only across entities
    (the same name under `facebook` and `facebook_ad_user`), and newest-wins is
    what the run-time path already does with that.
    """
    q = """
    SELECT details ->> 'access_token' AS token
    FROM credentials
    WHERE user_id = %s
    AND key = %s
    AND entity = ANY(%s)
    AND details ->> 'access_token' IS NOT NULL
    ORDER BY created DESC
    LIMIT 1
    """
    rows = list(
        query(
            db_cnf,
            q,
            (user_id, credentials_key, list(FACEBOOK_CREDENTIAL_ENTITIES)),
            as_dict=True,
        )
    )
    return rows[0]["token"] if rows else None


# --------------------------------------------------------------------------
# Connected accounts, for `server/accounts.py`
# --------------------------------------------------------------------------

# The `entity` values that are CONNECTED ACCOUNTS -- a named third-party
# credential a study's `data-sources` section (or, for Facebook,
# `general.credentials_key`) refers to by name.
#
# Enumerated rather than "everything in `credentials`", which is what the Go
# service's `/accounts` list does. That table is not only accounts: since the
# 2026-09-04 hardening it also holds vlab's own API-token rows (`api_token`)
# and the legacy-key tombstones (`api_token_revoked`), and those are
# `list_api_keys`'s business, with their own shape and their own revocation
# route. Listing them here would report the same key twice under two shapes and
# offer a `DELETE` that looks like revocation and is not (deleting the account
# row for a minted key does NOT revoke the key -- only removing the `api_token`
# row does).
#
# `facebook_ad_user` is in the set for the same reason `list_facebook_credentials`
# accepts it: it is the entity real production Facebook rows are under, and
# omitting it would hide a credential a study is demonstrably running on.
ACCOUNT_ENTITIES = (
    "typeform",
    "fly",
    "alchemer",
    "qualtrics",
    "facebook",
    "facebook_ad_user",
    "api_key",
)


def list_accounts(user_id: str, auth_type=None):
    """The caller's connected-account rows, INCLUDING their `details`.

    The secret stripping happens in the route (`server/accounts.py`), not here,
    because what counts as non-secret is per auth type and the route is where
    that table lives. Nothing else calls this.

    `credentials` is user-scoped, not org-scoped: the `org_id` column added by
    the organisation migration is never populated by the Go account-create path
    (see `list_facebook_credentials`). So there is no org filter, and these
    routes live under `/users/...` rather than `/{org_id}/...` to say so.

    Sorted by `(entity, key)` rather than the Go route's `created DESC`: the
    caller's question is "which credentials_key do I use", and a stable
    alphabetical listing answers it the same way twice running, where a
    recency ordering reshuffles on every write.
    """
    if auth_type is None:
        q = """
        SELECT key, entity, details, created
        FROM credentials
        WHERE user_id = %s
        AND entity = ANY(%s)
        ORDER BY entity, key
        """
        vals = (user_id, list(ACCOUNT_ENTITIES))
    else:
        q = """
        SELECT key, entity, details, created
        FROM credentials
        WHERE user_id = %s
        AND entity = ANY(%s)
        AND entity = %s
        ORDER BY entity, key
        """
        # Still ANDed with the whole set, so a filter cannot be used to reach a
        # row the unfiltered listing would not have returned -- `?auth_type=api_token`
        # has to be empty, not a way around the enumeration above.
        vals = (user_id, list(ACCOUNT_ENTITIES), auth_type)

    return list(query(db_cnf, q, vals, as_dict=True))


def upsert_account(user_id: str, entity: str, key: str, details: Any):
    """Replace one credential row, in ONE transaction. Returns its `created`.

    DELETE-then-INSERT because that is what the Go handler does
    (`api/internal/server/handler/accounts/create.go`): `credentials` has
    `unique_entity_key_per_user` on `(user_id, entity, key)` and no update
    route, so re-connecting an account under a name it already has is a
    replace.

    THE DIFFERENCE FROM GO, DELIBERATE. Go issues the two statements on
    separate connections with no transaction around them, so a failure between
    them -- or a crash, or the insert violating some other constraint -- leaves
    the user with NO credential under a name their study's
    `general.credentials_key` still points at, and the next reconcile of that
    study cannot authenticate. One transaction makes the replace atomic: either
    the new row is there or the old one still is, never neither.

    An `ON CONFLICT ... DO UPDATE` would be atomic too and is the obvious
    alternative. It is not used because the conflict target would have to name
    the constraint, and `details` is the only column it could set -- so it
    would silently preserve the original `created`, which is the one field a
    caller uses to tell a re-connected credential from a stale one.
    """
    q_delete = """
    DELETE FROM credentials
    WHERE user_id = %s AND entity = %s AND key = %s
    """
    q_insert = """
    INSERT INTO credentials (user_id, entity, key, details)
    VALUES (%s, %s, %s, %s)
    RETURNING created
    """

    payload = orjson.dumps(details).decode("utf8")

    # One connection, one transaction: psycopg3's connection context manager
    # commits on a clean exit and rolls back on an exception, so the two
    # statements land together or not at all. `db.execute` opens a connection
    # per call and could not give that.
    with psycopg.connect(db_cnf) as conn:
        with conn.cursor() as cur:
            cur.execute(q_delete, (user_id, entity, key))
            cur.execute(q_insert, (user_id, entity, key, payload))
            return cur.fetchone()[0]


def delete_account(user_id: str, entity: str, key: str) -> bool:
    """Delete one credential row. True if there was one.

    Scoped to the caller in SQL rather than checked afterwards, the same way
    `api_keys._delete_api_token_row` is: a miss and somebody else's credential
    are then the same answer, so this never confirms that another user's
    account exists.
    """
    q = """
    DELETE FROM credentials
    WHERE user_id = %s AND entity = %s AND key = %s
    RETURNING key
    """
    return bool(list(query(db_cnf, q, (user_id, entity, key), as_dict=True)))


def user_in_org(user_id: str, org_id: str) -> bool:
    """Membership, as a standalone check.

    Every other route in this service gets membership for free by joining
    `orgs_lookup` on the way to a study. The Meta routes have no study to join
    through, so the check has to be its own query -- and so does `list_studies`
    below, for a different reason: a SELECT that returns no rows cannot say
    whether the caller is not a member or the org is simply empty, and those
    two need different answers.
    """
    q = """
    SELECT 1
    FROM orgs_lookup
    WHERE user_id = %s
    AND org_id = %s
    LIMIT 1
    """
    return bool(list(query(db_cnf, q, (user_id, org_id))))


def list_orgs(user_id: str):
    """The organisations `user_id` belongs to. `[]` for a user in none.

    The port of the Go dashboard API's `GetUserOrgIDs`
    (`api/internal/storage/user.go`), which is Auth0-only -- so until now an
    API key could configure a study inside an org but had no way to learn that
    the org existed. See planning/list-orgs-studies.md.

    ORDER BY is ours; Go has none. A list an agent reads twice should come back
    the same way twice. `orgs.name` is UNIQUE but NULLABLE (Go scans it into a
    `sql.NullString`, and the route's model allows None for the same reason),
    and SQL UNIQUE permits any number of NULLs -- so `name` alone is NOT a
    total order for a user in two unnamed orgs. `id` is the tie-break, for the
    same reason `list_studies` below orders on `created, id`.
    """
    q = """
    SELECT o.id, o.name
    FROM orgs o
    JOIN orgs_lookup ol ON ol.org_id = o.id
    WHERE ol.user_id = %s
    ORDER BY o.name, o.id
    """
    return list(query(db_cnf, q, (user_id,), as_dict=True))


def list_studies(user_id: str, org_id: str, limit: int, offset: int):
    """Studies in `org_id`, newest first, for a caller who is a member of it.

    DELIBERATELY NOT the Go dashboard query, which is
    `WHERE user_id = $3 OR org_id = $4` (`api/internal/storage/study.go`
    `GetStudies`). Both halves of that OR are wrong on this service:

    * `org_id = $4` with no membership check is safe in the dashboard because
      the org id comes from the browser's own session state. Here it is a path
      segment supplied by whoever holds the API key, so the Go query would let
      any authenticated key list any org's studies by guessing a UUID.
    * `user_id = $3` returns the caller's studies from OTHER orgs under the
      requested org's URL. Harmless in a UI where the two sets coincide;
      incoherent in an API whose every study address is `/{org}/studies/{slug}`.

    So the rule is the one every other read here enforces by join and the
    create route enforces by INSERT ... SELECT: studies in an org the caller is
    a member of, whoever created them.

    A consequence worth stating: a study with a NULL `org_id` -- rows predating
    the 2023 organisation migration, and anything `create_campaign_for_user`
    wrote (see `create_study` below) -- matches nothing here. That is not a
    gap in this query; such a study is unreachable through EVERY route on this
    service, and listing it would advertise a slug that 404s.

    Membership is the caller's to check (`user_in_org`) before calling this:
    an empty result here means "no studies", not "not your org".

    `s.id` is in the ORDER BY as a tie-break, not for its own sake. `created`
    is not unique -- two studies created in the same microsecond are entirely
    possible from a script -- and LIMIT/OFFSET over a partial order can skip a
    row and repeat another between two pages.
    """
    q = """
    SELECT s.id, s.name, s.slug, s.created
    FROM studies s
    JOIN orgs_lookup ol ON ol.org_id = s.org_id
    WHERE ol.user_id = %s
    AND s.org_id = %s
    ORDER BY s.created DESC, s.id DESC
    LIMIT %s OFFSET %s
    """
    return list(query(db_cnf, q, (user_id, org_id, limit, offset), as_dict=True))


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
