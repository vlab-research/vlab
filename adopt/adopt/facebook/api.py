import logging

import backoff
from facebook_business.api import Cursor
from facebook_business.exceptions import FacebookRequestError

# Setup backoff logging
logging.getLogger("backoff").addHandler(logging.StreamHandler())


INTERVAL = 5 * 60

# TODO:
# check status code
# only retry on known codes
# 17, user request limit reached

# 368 - page blocked from sending messages...


@backoff.on_exception(backoff.constant, FacebookRequestError, interval=INTERVAL)
def call(fn, *args, **kwargs):
    res = fn(**kwargs)

    if isinstance(res, Cursor):
        return [r for r in res]
    return res
