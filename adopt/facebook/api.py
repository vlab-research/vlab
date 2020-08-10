import logging
import backoff
from facebook_business.exceptions import FacebookRequestError
from facebook_business.api import Cursor

# Setup backoff logging
logging.getLogger('backoff').addHandler(logging.StreamHandler())


interval = 5*60


@backoff.on_exception(backoff.constant, FacebookRequestError, interval=interval)
def call(fn, params, fields):
    res = fn(params=params, fields=fields)

    if isinstance(res, Cursor):
        return [r for r in res]
    return res
