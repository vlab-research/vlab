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


def test_get_unsaturated_clusters_with_saturation_function():
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

    fil = is_saturated([('rand', lambda x: x > 100)], 2)
    res = get_unsaturated_clusters(df, 'dist', fil)

    assert res.tolist() == ['foo', 'baz']
