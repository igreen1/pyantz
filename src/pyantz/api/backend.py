"""Where the application is defined."""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import endpoints
from .auth import require_token
from .settings import (
    FRONTEND_DIR_VARIABLE,
    check_safe_to_bind,
    get_cors_origins,
    get_frontend_dir,
    get_settings,
)

if TYPE_CHECKING:
    from pathlib import Path


def create_app(frontend_dir: Path | None = None) -> FastAPI:
    """Create the application, reading its settings from the environment.

    The cors origins are read from `PYANTZ_CORS_ORIGINS`, and the built web ui is
    served at ``/`` if `PYANTZ_FRONTEND_DIR` names it.

    Args:
        frontend_dir: the built web ui to serve at ``/``, instead of the one which
            `PYANTZ_FRONTEND_DIR` names

    Raises:
        ValueError: if `PYANTZ_FRONTEND_DIR` is not a directory with an index.html

    """
    application = FastAPI()
    origins = get_cors_origins()
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    application.include_router(endpoints.router, dependencies=[Depends(require_token)])
    frontend_dir = frontend_dir or get_frontend_dir()
    if frontend_dir is not None:
        if not (frontend_dir / "index.html").is_file():
            msg = (
                f"{FRONTEND_DIR_VARIABLE}={str(frontend_dir)!r} has no index.html: "
                "build the web ui with `npm run build` in frontend/pyantz"
            )
            raise ValueError(msg)
        # last, so that it never hides the api
        application.mount(
            "/", StaticFiles(directory=frontend_dir, html=True), name="frontend"
        )
    return application


app = create_app()


def start_prod_server() -> None:
    """Start a production server."""
    settings = get_settings()
    check_safe_to_bind(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
