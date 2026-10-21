"""Serve the api and the built web ui from one server (``pyantz-frontend``)."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING

import uvicorn

from .backend import create_app
from .settings import check_safe_to_bind, get_frontend_dir, get_settings

if TYPE_CHECKING:
    from pathlib import Path

NOT_INSTALLED = (
    "The web ui is not installed: install it with `pip install 'pyantz[frontend]'`"
)


def get_bundled_frontend_dir() -> Path:
    """Get the directory with the web ui which comes with ``pyantz[frontend]``.

    Raises:
        ValueError: if the `frontend` feature is not installed, or its ui is not built

    """
    try:
        package = import_module("pyantz_frontend")
    except ModuleNotFoundError as exc:
        raise ValueError(NOT_INSTALLED) from exc
    directory: Path = package.STATIC_DIR
    if not (directory / "index.html").is_file():
        msg = (
            f"The web ui is not built: {str(directory)!r} has no index.html. "
            "Run `make frontend-bundle`, or reinstall `pyantz[frontend]`"
        )
        raise ValueError(msg)
    return directory


def start_frontend_server() -> None:
    """Start the api and serve the web ui at ``/``.

    The ui is the one installed with ``pyantz[frontend]``, unless
    `PYANTZ_FRONTEND_DIR` names another build.
    """
    try:
        settings = get_settings()
        check_safe_to_bind(settings)
        directory = get_frontend_dir() or get_bundled_frontend_dir()
        application = create_app(frontend_dir=directory)
    except ValueError as exc:
        sys.exit(str(exc))
    uvicorn.run(
        application,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
