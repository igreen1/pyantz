"""Primary server to run."""

from __future__ import annotations

import uvicorn

from .settings import check_safe_to_bind, get_settings


def start_dev_server() -> None:
    """Start a development server.

    Entry point of ``pyantz-dev``; listens where `PYANTZ_HOST` and `PYANTZ_PORT`
    say, until stopped.

    Args:
        None.

    Returns:
        None.

    Raises:
        ValueError: if the settings are invalid, or the host isn't local and no
            token is set.

    """
    settings = get_settings()
    check_safe_to_bind(settings)
    uvicorn.run(
        "pyantz.api.backend:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
