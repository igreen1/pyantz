"""Optional token authentication of the api."""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import Header, HTTPException, status

from .settings import get_api_token


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Reject requests without ``Authorization: Bearer <token>``, if a token is set.

    The token is read from `PYANTZ_API_TOKEN` on each request. Without one, every
    request is let through (the servers only listen on localhost in that case).

    Args:
        authorization: the request's ``Authorization`` header, if any.

    Returns:
        None.

    Raises:
        HTTPException: 401 if a token is set and the header doesn't carry it.

    Example:
        .. testcode::

            import os

            from fastapi import HTTPException

            from pyantz.api.auth import require_token

            os.environ["PYANTZ_API_TOKEN"] = "secret"
            try:
                require_token("Bearer secret")  # accepted
                require_token("Bearer guess")
            except HTTPException as exc:
                print(exc.status_code)
            finally:
                del os.environ["PYANTZ_API_TOKEN"]

        .. testoutput::

            401

    """
    token = get_api_token()
    if token is None:
        return
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.encode(), token.encode()
    ):
        logging.getLogger(__name__).debug(
            "Rejected request with a missing or bad token"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
