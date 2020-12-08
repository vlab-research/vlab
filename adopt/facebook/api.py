import logging

import backoff
from facebook_business.api import Cursor
from facebook_business.exceptions import FacebookRequestError

# Setup backoff logging
logging.getLogger("backoff").addHandler(logging.StreamHandler())


interval = 5 * 60

# TODO:
# check status code
# only retry on known codes


@backoff.on_exception(backoff.constant, FacebookRequestError, interval=interval)
def call(fn, params, fields):
    res = fn(params=params, fields=fields)

    if isinstance(res, Cursor):
        return [r for r in res]
    return res
