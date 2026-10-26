"""Optional token authentication of the api."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException, status

from .settings import get_api_token


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Reject requests without ``Authorization: Bearer <token>``, if a token is set.

    The token is read from `PYANTZ_API_TOKEN` on each request. Without one, every
    request is let through (the servers only listen on localhost in that case).
    """
    token = get_api_token()
    if token is None:
        return
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.encode(), token.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
