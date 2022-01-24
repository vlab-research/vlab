# from datetime import datetime, timezone
# import pytest
# from test.dbfix import db, cnf as chatbase
# from .responses import *

# @pytest.fixture()
# def dat(db):
#     conn, cur = db

#     q = """
#     INSERT INTO responses(surveyid, userid, question_ref, response, metadata, timestamp)
#     VALUES (%s, %s, %s, %s, %s, %s)
#     """

#     rows = [
#         ('1', '1', '1', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('1', '1', '1', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('1', '1', '2', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('1', '1', '2', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('1', '1', '3', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),

#         ('2', '2', '1', 'foo', '{"mykey": "foo"}', datetime(2020, 5, 1, tzinfo=timezone.utc)),
#         ('2', '2', '1', 'bar', '{"mykey": "baz"}', datetime(2020, 5, 2, tzinfo=timezone.utc)),
#         ('2', '2', '2', 'bar', '{"mykey": "bar"}', datetime(2020, 5, 1, tzinfo=timezone.utc))
#     ]

#     for r in rows:
#         cur.execute(q, r)

#     conn.commit()

#     yield True

#     cur.execute('DELETE FROM responses;')
#     conn.commit()


# def test_last_responses_gets_only_last_answer(db, dat):
#     res = list(last_responses('1', ['1'], chatbase))
#     assert len(res) == 1
#     assert res[0]['response'] == 'bar'


# def test_last_responses_gets_only_last_answer_multiple_surveys(db, dat):
#     res = list(last_responses(['1', '2'], ['1'], chatbase))
#     assert len(res) == 2
#     assert res[0]['response'] == 'bar'
#     assert res[1]['response'] == 'bar'


# def test_last_responses_works_with_multiple_questions(db, dat):
#     res = list(last_responses('1', ['1', '2', '3'], chatbase))
#     assert len(res) == 3
#     assert res[0]['question_ref'] == '1'
#     assert res[0]['response'] == 'bar'
#     assert res[1]['question_ref'] == '2'
#     assert res[1]['response'] == 'bar'
#     assert res[2]['question_ref'] == '3'
#     assert res[2]['response'] == 'foo'


# def test_last_responses_works_with_multiple_questions_and_surveys(db, dat):
#     res = list(last_responses(['1', '2'], ['1', '2'], chatbase))
#     assert len(res) == 4

#     assert {r['question_ref'] for r in res} == set(['1', '2'])
#     assert {r['response'] for r in res} == set(['bar'])

# def test_get_metadata_creates_question(db, dat):
#     res = list(get_metadata(['2'], chatbase))
#     assert res[0]['question_ref'] == 'md:mykey'
#     assert res[0]['response'] == 'baz'

# def test_get_metadata_creates_question_many_surveys(db, dat):
#     res = list(get_metadata(['1', '2'], chatbase))
#     assert res[0]['question_ref'] == 'md:mykey'
#     assert res[0]['response'] == 'bar'
#     assert res[1]['question_ref'] == 'md:mykey'
#     assert res[1]['response'] == 'baz'
#     assert len(res) == 2
