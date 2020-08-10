from datetime import datetime
import pandas as pd
from .clustering import *
from .facebook.state import unix_time_millis

DATE = datetime(2020, 1, 1)

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


def _format_df(df):
    df['surveyid'] = df.shortcode
    df = df.groupby(['userid', 'shortcode']) \
           .apply(lambda df: df.append([{
               **df.iloc[0].to_dict(),
               'question_ref': 'md:startTime',
               'response': unix_time_millis(DATE),
           }])) \
           .reset_index(drop=True)



    df = shape_df(df)
    return df


def test_user_fulfilling_multiple():
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

    df = _format_df(df)

    users = users_fulfilling([('rand', lambda x: x > 100),
                              ('rand', lambda x: x < 103),
                              ('dist', lambda x: x == 'bar')],
                             df)

    assert users.userid.unique().tolist() == [3]






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

    df = _format_df(df)

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

    df = _format_df(df)
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

    df = _format_df(df)

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

    df = _format_df(df)


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

    df = _format_df(df)

    res = get_saturated_clusters(df, cnf['stratum'])
    assert res == ['foo', 'bar']


def test_get_budget_lookup():

    cnf = {'stratum':
       {'per_cluster_pop': 5,
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
        ('rook', 90, 4, 'bar'),
        ('dood', 'baz', 5, 'bar'),
        ('rand', 105, 5, 'bar'),
        ('rook', 99, 5, 'bar')
    ], columns=cols)

    df = _format_df(df)

    window = BudgetWindow(DATE, DATE)

    spend = {'bar': 10.0, 'baz': 10.0, 'foo': 10.0}

    res = get_budget_lookup(df, cnf['stratum'], 30, 10, 5, window, spend)
    assert sum(res.values()) <= 30
    assert set(res.keys()) == {'bar', 'baz', 'foo'}

    assert res == {'bar': 10., 'baz': 10., 'foo': 8.}


def test_get_budget_lookup_respects_maximum_budget():

    cnf = {'stratum':
       {'per_cluster_pop': 5,
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
        ('rook', 90, 4, 'bar'),
        ('dood', 'baz', 5, 'bar'),
        ('rand', 105, 5, 'bar'),
        ('rook', 99, 5, 'bar')
    ], columns=cols)

    df = _format_df(df)

    window = BudgetWindow(DATE, DATE)

    spend = {'bar': 10.0, 'baz': 10.0, 'foo': 10.0}

    res = get_budget_lookup(df, cnf['stratum'], 20, 10, 2, window, spend)
    assert sum(res.values()) <= 20
    assert set(res.keys()) == {'bar', 'baz', 'foo'}


def test_get_budget_lookup_ignores_saturated_clusters():

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
        ('rook', 90, 4, 'bar'),
        ('dood', 'baz', 5, 'bar'),
        ('rand', 105, 5, 'bar'),
        ('rook', 99, 5, 'bar'),
        ('dood', 'baz', 6, 'bar'),
        ('rook', 105, 6, 'bar')
    ], columns=cols)

    df = _format_df(df)

    spend = {'bar': 10.0, 'baz': 10.0, 'foo': 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf['stratum'], 1000, 10, 5, window, spend)

    assert res == { 'bar': 2.0, 'foo': 0.0, 'baz': 0.0 }

def test_get_budget_lookup_works_with_missing_data_from_clusters():
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
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dood', 'bar', 4, 'bar'),
        ('rook', 90, 4, 'bar')
    ], columns=cols)

    df = _format_df(df)

    spend = {'bar': 10.0, 'qux': 10.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf['stratum'], 1000, 10, 5, window, spend)

    assert res == { 'bar': 2.0, 'qux': 2.0 }


def test_get_budget_lookup_handles_zero_spend():

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
        ('dist', 'bar', 2, 'foo'),
        ('rand', 55, 2, 'foo'),
        ('dist', 'bar', 3, 'foo'),
        ('rand', 60, 3, 'foo'),
        ('dood', 'bar', 4, 'bar'),
        ('rook', 90, 4, 'bar')
    ], columns=cols)

    df = _format_df(df)

    spend = {'bar': 10.0, 'qux': 0.0}
    window = BudgetWindow(DATE, DATE)
    res = get_budget_lookup(df, cnf['stratum'], 1000, 10, 5, window, spend)

    assert res == {'bar': 2.0}


def test_budget_trimming():
    budget = {'foo': 100, 'bar': 25}
    assert budget_trimming(budget, 100, 1) == {'foo': 75, 'bar': 25}

    budget = {'foo': 100, 'bar': 75, 'baz': 25}
    assert budget_trimming(budget, 75, 1) == {'foo': 25, 'bar': 25, 'baz': 25}

    budget = {'foo': 100, 'bar': 75, 'baz': 25}
    assert budget_trimming(budget, 50, 1) == {'foo': 16, 'bar': 16, 'baz': 16}



# def test_get_budget_lookup_does_something_with_empty_data():

#     cnf = {'stratum':
#        {'per_cluster_pop': 1,
#         'surveys': [
#             {'shortcode': 'foo',
#              'cluster_question': {
#                  'ref': 'dist'
#              },
#              'target_questions': [
#                  {'ref': 'rand',
#                   'op': 'greater_than',
#                   'value': 100}]},
#             {'shortcode': 'bar',
#              'cluster_question': {
#                  'ref': 'dood'
#              },
#              'target_questions': [
#                  {'ref': 'rook',
#                   'op': 'greater_than',
#                   'value': 100}]}
#         ]}}

#     cols = ['question_ref', 'response', 'userid', 'shortcode']
#     df = pd.DataFrame([
#         ('dist', 'foo', 1, 'foo'),
#         ('rook', 105, 5, 'bar')
#     ], columns=cols)

#     res = get_budget_lookup(df, cnf['stratum'])
#     assert res == { 'bar': 1.0 }
