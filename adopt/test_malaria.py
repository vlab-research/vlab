from datetime import datetime, timezone
from test.dbfix import cnf as chatbase
from test.dbfix import db

import pandas as pd
import pytest

from .malaria import *


def _d(ref, response, userid):
    cols = [
        "parent_survey_id",
        "parent_shortcode",
        "surveyid",
        "shortcode",
        "userid",
        "seed",
        "flowid",
        "question_idx",
        "timestamp",
        "question_text",
    ]
    default = {c: "foo" for c in cols}

    return {**default, "question_ref": ref, "response": response, "userid": userid}


# def test_synthetic_district():
#     df = pd.DataFrame([
#         _d('dist', 1234, 1),
#         _d('dist', 3456, 2),
#         _d('dist', 234, 3),
#         _d('dist', 7890, 4),
#         _d('dist', 495809, 5)
#     ])

#     res = list(synthetic_district('dist', 'foo', df))

#     assert len(res) == 5
#     assert [r['response'] for r in res] == ['123', '345', '234', '789', '495']
#     assert [r['question_ref'] for r in res] == ['synth-district']*5
#     assert [r['question_text'] for r in res] == ['district']*5
#     assert [isinstance(r['timestamp'], datetime) for r in res] == [True]*5

#     # just assure it concats to original without problem
#     alls = pd.concat([df, pd.DataFrame(res)])
#     assert alls.shape[0] == 10


# @pytest.fixture()
# def surveys(db):
#     conn, cur = db

#     q = """
#     INSERT INTO surveys(id, shortcode, userid)
#     VALUES (%s, %s, %s)
#     """

#     rows = [
#         ("1", "foo", "111"),
#         ("2", "bar", "111"),
#         ("3", "baz", "111"),
#         ("4", "qux", "111"),
#     ]

#     for r in rows:
#         cur.execute(q, r)

#     conn.commit()

#     yield True

#     cur.execute("DELETE FROM surveys;")
#     conn.commit()


# @pytest.fixture()
# def dat(db):
#     conn, cur = db

#     q = """
#     INSERT INTO responses(shortcode, surveyid, userid, question_ref, response, metadata, timestamp)
#     VALUES (%s, %s, %s, %s, %s, %s, %s)
#     """

#     rows = [
#         (
#             "foo",
#             "1",
#             "1",
#             "1",
#             "1234",
#             '{"startTime": 123456, "cid": "0f1"}',
#             datetime(2020, 5, 1, tzinfo=timezone.utc),
#         ),
#         (
#             "foo",
#             "1",
#             "2",
#             "1",
#             "1245",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "foo",
#             "1",
#             "2",
#             "2",
#             "foo",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "bar",
#             "2",
#             "1",
#             "1",
#             "1234",
#             '{"startTime": 123456, "cid": "0f1"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "bar",
#             "2",
#             "1",
#             "2",
#             "yes",
#             '{"startTime": 123456, "cid": "0f1"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "bar",
#             "2",
#             "2",
#             "1",
#             "1245",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 1, tzinfo=timezone.utc),
#         ),
#         (
#             "bar",
#             "2",
#             "2",
#             "2",
#             "no",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "bar",
#             "2",
#             "3",
#             "1",
#             "1245",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 1, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "1",
#             "1",
#             "1234",
#             '{"startTime": 123456, "cid": "0f1"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "1",
#             "2",
#             "yes",
#             '{"startTime": 123456, "cid": "0f1"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "2",
#             "1",
#             "1245",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 1, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "2",
#             "2",
#             "yes",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "3",
#             "1",
#             "1245",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 1, tzinfo=timezone.utc),
#         ),
#         (
#             "baz",
#             "3",
#             "3",
#             "2",
#             "no",
#             '{"startTime": 123456, "cid": "0f2"}',
#             datetime(2020, 5, 2, tzinfo=timezone.utc),
#         ),
#     ]

#     for r in rows:
#         cur.execute(q, r)

#     conn.commit()

#     yield True

#     cur.execute("DELETE FROM responses;")
#     conn.commit()


# cnf = {
#     "lookup_loc": "test/district-lookup.csv",
#     "chatbase": chatbase,
#     "survey_user": "111",
#     "strata": [
#         {
#             "per_cluster_pop": 2,
#             "surveys": [
#                 {
#                     "shortcode": "foo",
#                     "cluster_question": {"ref": "md:cid"},
#                     "target_questions": [{"ref": "2", "op": "equal", "value": "yes"}],
#                     "exclude_questions": [],
#                 },
#             ],
#         }
#     ],
# }


# def test_malaria_opt_nothing_filled(surveys, db, dat):
#     clusters, users = opt(cnf)
#     assert len(clusters) == 3
#     assert users == []


# def test_malaria_opt_no_survey_filled(surveys, db, dat):
#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 2,
#                 "surveys": [
#                     {
#                         "shortcode": "qux",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [],
#                     }
#                 ],
#             }
#         ],
#     }
#     clusters, users = opt(c)
#     assert len(clusters) == 3
#     assert users == []


# def test_malaria_opt_no_questions_filled(surveys, db, dat):
#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 2,
#                 "surveys": [
#                     {
#                         "shortcode": "bar",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [],
#                     },
#                 ],
#             }
#         ],
#     }
#     clusters, users = opt(cnf)
#     assert len(clusters) == 3
#     assert users == []


# def test_malaria_opt_user_fulfilled(surveys, db, dat):
#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 2,
#                 "surveys": [
#                     {
#                         "shortcode": "bar",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [],
#                     },
#                 ],
#             }
#         ],
#     }

#     clusters, users = opt(c)
#     assert len(clusters) == 3
#     assert users == ["1"]


# def test_malaria_opt_clusters_partially_fulfilled(surveys, db, dat):

#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 1,
#                 "surveys": [
#                     {
#                         "shortcode": "bar",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [],
#                     },
#                 ],
#             }
#         ],
#     }

#     clusters, users = opt(c)

#     assert len(clusters) == 2
#     assert users == ["1"]


# def test_malaria_opt_clusters_all_fulfilled(surveys, db, dat):

#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 1,
#                 "surveys": [
#                     {
#                         "shortcode": "baz",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [],
#                     },
#                 ],
#             }
#         ],
#     }

#     clusters, users = opt(c)

#     assert len(clusters) == 1
#     assert clusters == ["0f3"]
#     assert users == ["1", "2"]


# def test_malaria_lookalike_users_and_anti_users(surveys, db, dat):
#     c = {
#         **cnf,
#         "strata": [
#             {
#                 "per_cluster_pop": 1,
#                 "surveys": [
#                     {
#                         "shortcode": "baz",
#                         "cluster_question": {"ref": "md:cid"},
#                         "target_questions": [
#                             {"ref": "2", "op": "equal", "value": "yes"}
#                         ],
#                         "exclude_questions": [
#                             {"ref": "2", "op": "equal", "value": "no"}
#                         ],
#                     },
#                 ],
#             }
#         ],
#     }

#     clusters, users, antis = opt(c, True)

#     assert len(clusters) == 1
#     assert clusters == ["0f3"]
#     assert users == ["1", "2"]
#     assert antis == ["3"]
