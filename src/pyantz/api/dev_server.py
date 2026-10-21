"""Primary server to run."""

from __future__ import annotations

import uvicorn

from .settings import check_safe_to_bind, get_settings


def start_dev_server() -> None:
    """Start a development server."""
    settings = get_settings()
    check_safe_to_bind(settings)
    uvicorn.run(
        "pyantz.api.backend:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
