import psycopg
import pytest

from adopt.db import _connect

cnf = "postgresql://root@localhost:5433/test"


def _reset_db():
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            tables = [
                "recruitment_data_events",
                "study_confs",
                "studies",
                "orgs_lookup",
                "orgs",
                "users",
            ]
            for t in tables:
                cur.execute(f"delete from {t}")
                conn.commit()
