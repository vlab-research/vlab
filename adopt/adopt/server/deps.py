"""Shared FastAPI dependencies and route decorators.

`User`, `security` and `get_current_user` live here rather than in `server.py`
so that route modules (studies, api keys, schemas) can depend on authentication
without importing `server`, which imports them — a cycle. `server.py` re-exports
these names, so existing `from .server import User` imports keep working.

`async_timeout` is here for exactly the same reason: it was defined in
`server.py` and used only by the two optimize routes, and `meta.py` needs it
too. Moving it rather than copying it keeps one definition of what a timed-out
handler returns.
"""

import asyncio
from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .auth import AuthError, verify_tokens


class User(BaseModel):
    user_id: str


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_tokens(token)
        user: str = payload.get("sub")

        if user is None:
            raise credentials_exception

        return User(user_id=user)

    except AuthError:
        raise credentials_exception


def async_timeout(seconds: int = 300):
    """Fail a handler with 504 if it has not finished within `seconds`.

    Moved here from `server.py`, unchanged, so that `meta.py` can use it
    without importing `server` (which imports `meta`).

    Worth knowing what this does and does not do. `asyncio.wait_for` cancels
    the *awaiting coroutine*, which frees the event loop and answers the
    client. It does not kill work already running in a worker thread — that
    thread runs to completion on its own schedule. So this is a bound on how
    long a client waits and on how long a request occupies the event loop, not
    a bound on the work itself. Whatever runs in the thread needs its own
    timeout; for the Meta proxy that is the per-call socket timeout plus the
    page cap (see `meta.GRAPH_TIMEOUT_SECONDS` and `meta.MAX_PAGES`).
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Operation timed out after {seconds} seconds",
                )

        return wrapper

    return decorator
