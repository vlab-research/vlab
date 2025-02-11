from functools import reduce
from typing import Any, Callable, Dict, Optional, Union

import pandas as pd
import logging
from .study_conf import AudienceConf, QuestionTargeting, Stratum, StratumConf, TargetVar


class MissingResponseError(BaseException):
    pass


def _users_by_predicate(df, pred):
    mask = df.apply(pred, 1)
    users = df[mask].user_id.unique()
    return users


def _filter_by_response(df, ref, pred):
    if df.shape[0] == 0:
        return df
    d = df[df.variable == ref].reset_index(drop=True)
    users = _users_by_predicate(d, pred)
    return df[df.user_id.isin(users)].reset_index(drop=True)


def get_var(v: Union[TargetVar, QuestionTargeting], d: Dict[str, Any]):
    if isinstance(v, QuestionTargeting):
        return make_pred(v)(d)

    if not isinstance(v, TargetVar):
        raise Exception(
            f"get_var must be passed TargetVar or QuestionTargeting. Was passed: {v}"
        )

    type_, value = v.type, v.value

    if type_ == "constant":
        return value

    if type_ == "variable":
        try:
            ans = d["value"][value]
            return ans
        except KeyError:
            return None

    raise Exception(f"Target Question Type not valid: {type_}")


def wrap(fn):
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TypeError:
            return False
        except ValueError:
            return False

    return _wrapped


def make_pred(q: Optional[QuestionTargeting]) -> Callable[[pd.DataFrame], bool]:
    if q is None:
        return lambda _: True

    fns = {
        "and": lambda a, b: a and b,
        "or": lambda a, b: a or b,
        "answered": lambda a, _: pd.notna(a),
        "not_equal": lambda a, b: pd.notna(a) and pd.notna(b) and a != b,
        "equal": lambda a, b: a == b,
        "greater_than": lambda a, b: float(a) > float(b),
        "less_than": lambda a, b: float(a) < float(b),
    }

    try:
        fn = fns[q.op]
        fn = wrap(fn)

    except KeyError as e:
        raise TypeError(f"op function: {q.op} is not supported!") from e

    if len(q.vars) == 1:
        v = q.vars[0]
        return lambda df: fn(get_var(v, df), None)

    vars_ = q.vars

    def pred(d):
        return reduce(fn, [get_var(var, d) for var in vars_])

    return pred


def users_fulfilling(pred, df):
    dis = [(u, df.to_dict()) for u, df in df.set_index("variable").groupby("user_id")]

    users = {u for u, d in dis if pred(d)}
    return df[df.user_id.isin(users)]


def only_target_users(df, stratum: Union[Stratum, StratumConf, AudienceConf]):
    pred = make_pred(stratum.question_targeting)
    if df.shape[0] == 0:
        return None

    filtered = users_fulfilling(pred, df)

    if filtered.shape[0] == 0:
        logging.info(f"No users found for stratum: {stratum.id}")
        return None

    return filtered


def get_saturated_clusters(df, strata):
    dfs = [(stratum, only_target_users(df, stratum)) for stratum in strata]
    dfs = [(s, d) for s, d in dfs if d is not None]

    saturated = [s.id for s, d in dfs if d.user_id.unique().shape[0] >= s.quota]
    return saturated
