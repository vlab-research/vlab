import logging

import backoff
from facebook_business.api import Cursor
from facebook_business.exceptions import FacebookRequestError

# Setup backoff logging
logging.getLogger("backoff").addHandler(logging.StreamHandler())


INTERVAL = 5 * 60


def fatal_code(e):
    # Non-fatal error codes:
    # 17, user request limit reached
    # 368 - page blocked from sending messages (should be??)
    return e.api_error_code() not in {2, 17, 368, 80004}


@backoff.on_exception(
    backoff.constant, FacebookRequestError, interval=INTERVAL, giveup=fatal_code
)
def call(fn, *args, **kwargs):
    res = fn(**kwargs)

    if isinstance(res, Cursor):
        return [r for r in res]
    return res
