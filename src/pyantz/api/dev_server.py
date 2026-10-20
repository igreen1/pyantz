"""Primary server to run."""

import uvicorn

from .settings import get_settings


def start_dev_server() -> None:
    """Start a development server."""
    settings = get_settings()
    uvicorn.run(
        "pyantz.api.backend:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
