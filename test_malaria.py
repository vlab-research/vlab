from datetime import datetime, timezone
import pandas as pd
import pytest
from test.dbfix import db
from malaria import *


def _d(ref, response, userid):
    cols = ['parent_survey_id', 'parent_shortcode', 'surveyid', 'shortcode', 'userid', 'seed', 'flowid', 'question_idx', 'timestamp', 'question_text']
    default = {c:'foo' for c in cols}

    return {**default, 'question_ref': ref, 'response': response, 'userid': userid}

def test_get_unsaturated_clusters_with_saturation_function():
    df = pd.DataFrame([
        _d('dist', 1234, 1),
        _d('dist', 3456, 2),
        _d('dist', 234, 3),
        _d('dist', 7890, 4),
        _d('dist', 495809, 5)
    ])

    res = list(synthetic_district('dist', df))

    assert len(res) == 5
    assert [r['response'] for r in res] == ['123', '345', '234', '789', '495']
    assert [r['question_ref'] for r in res] == ['synth-district']*5
    assert [r['question_text'] for r in res] == ['district']*5
    assert [isinstance(r['timestamp'], datetime) for r in res] == [True]*5

    # just assure it concats to original without problem
    alls = pd.concat([df, pd.DataFrame(res)])
    assert alls.shape[0] == 10



@pytest.fixture()
def dat(db):
    conn, cur = db

    q = """
    INSERT INTO responses(surveyid, userid, question_ref, response, timestamp)
    VALUES (%s, %s, %s, %s, %s)
    """

    rows = [
        ('1', '1', '1', '1234', datetime(2020, 5, 1, tzinfo=timezone.utc)),
        ('1', '2', '1', '1245', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('1', '2', '2', 'foo', datetime(2020, 5, 2, tzinfo=timezone.utc)),

        ('2', '1', '1', '1234', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('2', '1', '2', 'yes', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('2', '2', '1', '1245', datetime(2020, 5, 1, tzinfo=timezone.utc)),
        ('2', '2', '2', 'no', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('2', '3', '1', '1245', datetime(2020, 5, 1, tzinfo=timezone.utc)),

        ('3', '1', '1', '1234', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('3', '1', '2', 'yes', datetime(2020, 5, 2, tzinfo=timezone.utc)),
        ('3', '2', '1', '1245', datetime(2020, 5, 1, tzinfo=timezone.utc)),
        ('3', '2', '2', 'yes', datetime(2020, 5, 2, tzinfo=timezone.utc)),
    ]

    for r in rows:
        cur.execute(q, r)

    conn.commit()

    yield True

    cur.execute('DELETE FROM responses;')
    conn.commit()

def test_malaria_opt_nothing_filled(db, dat):
    cnf = {
        'target_value': 'yes',
        'q_district': '1',
        'q_target': '2',
        'surveyid': '1',
        'cluster_size': 2,
        'dbname': 'test',
        'dbuser': 'test',
        'lookup_loc': './test/district-lookup.csv'
    }

    clusters, users = opt(cnf)

    assert len(clusters) == 3
    assert users == []


def test_malaria_opt_user_fulfilled(db, dat):
    cnf = {
        'target_value': 'yes',
        'q_district': '1',
        'q_target': '2',
        'surveyid': '2',
        'cluster_size': 2,
        'dbname': 'test',
        'dbuser': 'test',
        'lookup_loc': './test/district-lookup.csv'
    }

    clusters, users = opt(cnf)

    assert len(clusters) == 3
    assert users == ['1']


def test_malaria_opt_clusters_partially_fulfilled(db, dat):
    cnf = {
        'target_value': 'yes',
        'q_district': '1',
        'q_target': '2',
        'surveyid': '2',
        'cluster_size': 1,
        'dbname': 'test',
        'dbuser': 'test',
        'lookup_loc': './test/district-lookup.csv'
    }

    clusters, users = opt(cnf)

    assert len(clusters) == 1
    assert users == ['1']


def test_malaria_opt_clusters_all_fulfilled(db, dat):
    cnf = {
        'target_value': 'yes',
        'q_district': '1',
        'q_target': '2',
        'surveyid': '3',
        'cluster_size': 1,
        'dbname': 'test',
        'dbuser': 'test',
        'lookup_loc': './test/district-lookup.csv'
    }

    clusters, users = opt(cnf)

    assert len(clusters) == 0
    assert users == ['1', '2']
