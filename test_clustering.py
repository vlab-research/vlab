import pandas as pd
from clustering import *

cnf = {'stratum':
       {'per_cluster_pop': 2,
        'surveys': [
            {'shortcode': 'foo',
             'cluster_question': {
                 'ref': 'dist'
             },
             'target_questions': [
                 {'ref': 'rand',
                  'op': 'greater_than',
                  'value': 100}]},
            {'shortcode': 'bar',
             'cluster_question': {
                 'ref': 'dist'
             },
             'target_questions': [
                 {'ref': 'rand',
                  'op': 'greater_than',
                  'value': 100}]}
        ]}}



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
                             'dist',
                             df)

    df.userid.unique().tolist == [3]


def test_get_saturated_clusters_with_some_fulfilled():

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


    res = get_saturated_clusters(df, cnf['stratum'])

    assert res == ['bar']

def test_get_saturated_clusters_with_no_fulfilled():
    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 50, 1, 'foo'),
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dist', 'bar', 4, 'bar'),
        ('rand', 105, 4, 'bar'),
        ('dist', 'baz', 5, 'bar'),
        ('rand', 99, 5, 'bar'),
    ], columns=cols)


    res = get_saturated_clusters(df, cnf['stratum'])

    assert res == []


def test_get_saturated_clusters_with_some_users_no_cluster():
    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 50, 1, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dist', 'bar', 4, 'bar'),
        ('rand', 105, 4, 'bar'),
        ('dist', 'baz', 5, 'bar'),
        ('rand', 99, 5, 'bar'),
    ], columns=cols)


    res = get_saturated_clusters(df, cnf['stratum'])

    assert res == []


def test_get_saturated_clusters_with_various_cluster_refs():

    cnf = {'stratum':
       {'per_cluster_pop': 2,
        'surveys': [
            {'shortcode': 'foo',
             'cluster_question': {
                 'ref': 'dist'
             },
             'target_questions': [
                 {'ref': 'rand',
                  'op': 'greater_than',
                  'value': 100}]},
            {'shortcode': 'bar',
             'cluster_question': {
                 'ref': 'dood'
             },
             'target_questions': [
                 {'ref': 'rand',
                  'op': 'greater_than',
                  'value': 100}]}
        ]}}

    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 50, 1, 'foo'),
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dood', 'bar', 4, 'bar'),
        ('rand', 105, 4, 'bar'),
        ('dood', 'baz', 5, 'bar'),
        ('rand', 105, 5, 'bar'),
    ], columns=cols)


    res = get_saturated_clusters(df, cnf['stratum'])
    assert res == []


def test_get_saturated_clusters_with_various_cluster_refs_and_target_refs():

    cnf = {'stratum':
       {'per_cluster_pop': 1,
        'surveys': [
            {'shortcode': 'foo',
             'cluster_question': {
                 'ref': 'dist'
             },
             'target_questions': [
                 {'ref': 'rand',
                  'op': 'greater_than',
                  'value': 100}]},
            {'shortcode': 'bar',
             'cluster_question': {
                 'ref': 'dood'
             },
             'target_questions': [
                 {'ref': 'rook',
                  'op': 'greater_than',
                  'value': 100}]}
        ]}}

    cols = ['question_ref', 'response', 'userid', 'shortcode']
    df = pd.DataFrame([
        ('dist', 'foo', 1, 'foo'),
        ('rand', 105, 1, 'foo'),
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dood', 'bar', 4, 'bar'),
        ('rook', 105, 4, 'bar'),
        ('dood', 'baz', 5, 'bar'),
        ('rand', 105, 5, 'bar'),
        ('rook', 99, 5, 'bar')
    ], columns=cols)


    res = get_saturated_clusters(df, cnf['stratum'])
    assert res == ['foo', 'bar']
