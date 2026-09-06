import logging
from contextlib import contextmanager
from contextvars import ContextVar

import backoff
from facebook_business.api import Cursor
from facebook_business.exceptions import FacebookRequestError

# Setup backoff logging
logging.getLogger("backoff").addHandler(logging.StreamHandler())


INTERVAL = 5 * 60

# Graph error code 17, "User request limit reached": Meta is throttling the
# whole ad account, and the only cure is to wait.
RATE_LIMIT_CODE = 17

# Errors Meta itself says are worth retrying:
#   2      - temporary issue on Meta's side
#   17     - request limit reached (see above)
#   368    - page blocked from sending messages (should be??)
#   80004  - ads-management call volume limit
RETRYABLE_CODES = {2, RATE_LIMIT_CODE, 368, 80004}

# When set, `call` gives up on the FIRST error instead of sleeping INTERVAL
# and retrying. The cron jobs leave it unset: they run unattended, and waiting
# five minutes for Meta to lift a rate limit is exactly right there. The
# dashboard's request handlers set it, because a browser click that sleeps
# five minutes is not a retry, it is a hang -- on 2026-09-05 that hang blocked
# a uvicorn worker's event loop, failed its /health probe, and got the pod
# SIGKILLed while researchers saw "something went wrong". Those handlers turn
# the error into a 429 the dashboard can explain instead.
#
# A ContextVar rather than a module flag so it scopes to one request: uvicorn
# serves many requests per process, and asyncio.to_thread copies the context
# into the worker thread, so the flag follows the request there.
FAIL_FAST: ContextVar[bool] = ContextVar("facebook_fail_fast", default=False)


@contextmanager
def fail_fast():
    """Within this block, `call` raises on the first Graph error, never sleeps."""
    token = FAIL_FAST.set(True)
    try:
        yield
    finally:
        FAIL_FAST.reset(token)


def is_rate_limit(e: FacebookRequestError) -> bool:
    return e.api_error_code() == RATE_LIMIT_CODE


def fatal_code(e):
    if FAIL_FAST.get():
        return True
    return e.api_error_code() not in RETRYABLE_CODES


@backoff.on_exception(
    backoff.constant, FacebookRequestError, interval=INTERVAL, giveup=fatal_code
)
def call(fn, *args, **kwargs):
    res = fn(**kwargs)

    if isinstance(res, Cursor):
        return [r for r in res]
    return res
