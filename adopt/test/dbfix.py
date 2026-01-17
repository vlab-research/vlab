import psycopg
import pytest

from adopt.db import _connect

cnf = "postgresql://root@localhost:5433/test"


def _reset_db():
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            # Delete in order of dependencies (child tables first)
            # Tables must be deleted in reverse dependency order
            tables = [
                "adopt_reports",  # depends on studies
                "inference_data",  # depends on studies
                "inference_data_events",  # depends on studies
                "recruitment_data_events",  # depends on studies
                "study_confs",  # depends on studies (has ON DELETE CASCADE but clean up anyway)
                "studies",  # depends on users
                "credentials",  # depends on users
                "orgs_lookup",  # depends on users and orgs
                "orgs",  # no dependencies
                "users",  # no dependencies
            ]
            for t in tables:
                cur.execute(f"delete from {t}")
            conn.commit()


def _create_user(conn, user_id, org_id):
    with conn.cursor() as cur:
        cur.execute(
            "insert into users (id, org_id) values (%s, %s)",
            (user_id, org_id),
        )
        conn.commit()
