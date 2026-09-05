"""Shared FastAPI dependencies.

`User`, `security` and `get_current_user` live here rather than in `server.py`
so that route modules (studies, api keys, schemas) can depend on authentication
without importing `server`, which imports them — a cycle. `server.py` re-exports
these names, so existing `from .server import User` imports keep working.
"""

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
