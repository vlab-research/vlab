import psycopg
import pytest

from adopt.db import _connect

# cnf = "postgresql://root@localhost:5433/test"
cnf = "postgresql://ricardo:vPDF0NtZkxJObpTpvieGkg@free-tier9.gcp-us-west2.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full&options=--cluster%3Dmeat-moth-619"


def _reset_db():
    with _connect(cnf) as conn:
        with conn.cursor() as cur:
            tables = ["recruitment_data_events", "study_confs", "studies", "users"]
            for t in tables:
                cur.execute(f"delete from {t}")
                conn.commit()
