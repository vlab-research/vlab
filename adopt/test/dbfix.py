import psycopg2
import pytest

cnf = {
    "db": "test",
    "user": "test",
    "host": "localhost",
    "port": "5433",
    "password": "",
}


@pytest.fixture(scope="module")
def db():
    with psycopg2.connect(
        dbname="defaultdb", user="root", host="localhost", port="5433"
    ) as conn:
        with conn.cursor() as cur:
            q = """
            CREATE DATABASE IF NOT EXISTS test;

            USE test;

            CREATE TABLE IF NOT EXISTS responses(
            surveyid VARCHAR NOT NULL,
            shortcode VARCHAR,
            userid VARCHAR NOT NULL,
            question_ref VARCHAR NOT NULL,
            response VARCHAR NOT NULL,
            translated_response VARCHAR,
            metadata JSONB,
            timestamp TIMESTAMPTZ NOT NULL
            );

            CREATE TABLE IF NOT EXISTS surveys(
            id VARCHAR NOT NULL,
            shortcode VARCHAR NOT NULL,
            userid VARCHAR NOT NULL
            );

            CREATE USER IF NOT EXISTS test;
            GRANT INSERT,SELECT,UPDATE ON TABLE responses to test;
            GRANT INSERT,SELECT,UPDATE ON TABLE surveys to test;
            """
            cur.execute(q)
            conn.commit()

            yield (conn, cur)

            q = """
            DROP TABLE test.responses;
            DROP TABLE test.surveys;
            """
            cur.execute(q)
            conn.commit()
