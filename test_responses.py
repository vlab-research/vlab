from datetime import datetime, timezone
import pytest
from test.dbfix import db
from responses import *

@pytest.fixture()
def dat(db):
    conn, cur = db

    q = """
    INSERT INTO responses(surveyid, userid, question_ref, response, timestamp)
    VALUES (%s, %s, %s, %s, %s)
    """

    rows = [
        ('1', '1', '1', 'foo', datetime(2020, 5, 1, tzinfo=timezone.utc)),
        ('1', '1', '1', 'bar', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('1', '1', '2', 'bar', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('1', '1', '2', 'foo', datetime(2020, 5, 1, tzinfo=timezone.utc)),
        ('1', '1', '3', 'foo', datetime(2020, 5, 1, tzinfo=timezone.utc))
    ]

    for r in rows:
        cur.execute(q, r)

    conn.commit()

    yield True

    cur.execute('DELETE FROM responses;')
    conn.commit()


def test_last_responses_gets_only_last_answer(db, dat):
    res = list(last_responses('1', ['1'], 'test', 'test'))
    assert len(res) == 1
    assert res[0]['response'] == 'bar'


def test_last_responses_works_with_multiple_questions(db, dat):
    res = list(last_responses('1', ['1', '2', '3'], 'test', 'test'))
    assert len(res) == 3
    assert res[0]['question_ref'] == '1'
    assert res[0]['response'] == 'bar'
    assert res[1]['question_ref'] == '2'
    assert res[1]['response'] == 'bar'
    assert res[2]['question_ref'] == '3'
    assert res[2]['response'] == 'foo'
