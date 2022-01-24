import psycopg
import pytest

cnf = "postgresql://root@localhost:5433/test"


@pytest.fixture(scope="module")
def db():
    with psycopg.connect(cnf) as conn:
        with conn.cursor() as cur:
            yield (conn, cur)

            # cleanup
            # cur.execute()
            # conn.commit()
