import pandas as pd
from clustering import *


def test_get_unsaturated_clusters_with_simple_count_fn():
    cols = ['question_ref', 'response', 'userid']
    df = pd.DataFrame([
        ('dist', 'foo', 1),
        ('rand', 'foo', 1),
        ('dist', 'bar', 2),
        ('dist', 'bar', 3),
        ('dist', 'baz', 4),
    ], columns=cols)

    res = get_unsaturated_clusters(df, 'dist', lambda df: df.userid.unique().shape[0] > 1)

    assert res.tolist() == ['foo', 'baz']

def test_get_unsaturated_clusters_with_no_fulfilled():
    cols = ['question_ref', 'response', 'userid']
    df = pd.DataFrame([
        ('dist', 'foo', 1),
        ('rand', 'foo', 1),
        ('dist', 'bar', 2),
        ('dist', 'bar', 3),
        ('dist', 'baz', 4),
    ], columns=cols)

    res = get_unsaturated_clusters(df, 'dist', lambda df: df.userid.unique().shape[0] > 5)

    assert res.tolist() == ['foo', 'bar', 'baz']

def test_user_fulfilling_single():
    cols = ['question_ref', 'response', 'userid']
    df = pd.DataFrame([
        ('dist', 'foo', 1),
        ('rand', 50, 1),
        ('dist', 'bar', 2),
        ('rand', 55, 2),
        ('dist', 'bar', 3),
        ('rand', 101, 3),
        ('dist', 'bar', 4),
        ('rand', 103, 4),
        ('dist', 'baz', 5),
        ('rand', 103, 5),
    ], columns=cols)

    users = users_fulfilling([('rand', lambda x: x > 100)], df)

    assert users == [3, 4, 5]

def test_user_fulfilling_multiple():
    cols = ['question_ref', 'response', 'userid']
    df = pd.DataFrame([
        ('dist', 'foo', 1),
        ('rand', 50, 1),
        ('dist', 'bar', 2),
        ('rand', 55, 2),
        ('dist', 'bar', 3),
        ('rand', 101, 3),
        ('dist', 'bar', 4),
        ('rand', 103, 4),
        ('dist', 'baz', 5),
        ('rand', 103, 5),
    ], columns=cols)

    users = users_fulfilling([('rand', lambda x: x > 100),
                              ('rand', lambda x: x < 103),
                              ('dist', lambda x: x == 'bar')],
                             df)

    assert users == [3]

def test_all_users_fulfilling_from_multiple_surveys():
    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 50, 1, 'foo'),
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 101, 3, 'foo'),
        ('dist', 'bar', 4, 'bar'),
        ('rand', 103, 4, 'bar'),
        ('dist', 'baz', 5, 'bar'),
        ('rand', 99, 5, 'bar'),
    ], columns=cols)

    cnf = {'stratum':
           {'per_cluster_pop': 2,
            'surveys': [
                {'shortcode': 'foo',
                 'target_questions': [
                     {'ref': 'rand',
                      'op': 'greater_than',
                      'value': 100}]},
                {'shortcode': 'bar',
                 'target_questions': [
                     {'ref': 'rand',
                      'op': 'greater_than',
                      'value': 100}]}
            ]}}

    users = all_users_fulfilling(cnf['stratum']['surveys'], df)

    assert users == [3, 4]


def test_get_unsaturated_clusters_with_saturation_function():
    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 50, 1, 'foo'),
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 101, 3, 'foo'),
        ('dist', 'bar', 4, 'foo'),
        ('rand', 103, 4, 'foo'),
        ('dist', 'baz', 5, 'foo'),
        ('rand', 103, 5, 'foo'),
    ], columns=cols)

    cnf = {'stratum':
           {'per_cluster_pop': 2,
            'surveys': [
               {'shortcode': 'foo',
                'target_questions': [
                    {'ref': 'rand',
                     'op': 'greater_than',
                     'value': 100}]}]}}

    fil = is_saturated(cnf)
    res = get_unsaturated_clusters(df, 'dist', fil)

    assert res.tolist() == ['foo', 'baz']
