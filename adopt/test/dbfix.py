from dataclasses import dataclass

import psycopg
import pytest

from adopt.db import _query

cnf = "postgresql://root@localhost:5433/test"


@dataclass
class DB:
    conn: psycopg.Connection

    def query(self, q, vals=(), as_dict=False):
        for x in _query(self.conn.cursor(), q, vals, as_dict):
            yield x
        self.conn.commit()

    def execute(self, q, vals=()):
        with self.conn.cursor() as cur:
            cur.execute(q, vals)
            self.conn.commit()

    def reset(self):
        with self.conn.cursor() as cur:
            tables = ["study_confs", "recruitment_data_events", "studies", "users"]
            for t in tables:
                cur.execute(f"delete from {t} cascade")
            self.conn.commit()


@pytest.fixture(scope="package")
def db():
    conn = psycopg.connect(cnf)
    db = DB(conn)

    db.reset()
    yield db

    # teardown
    db.conn.close()
