"""Primary server to run."""

import os

import uvicorn

host = os.environ.get("PYANTZ_HOST", "127.0.0.1")
port = int(os.environ.get("PYANTZ_PORT", "8000"))


def start_dev_server() -> None:
    """Start a development server."""
    uvicorn.run(
        "pyantz.api.backend:app",
        host=host,
        port=port,
        log_level="info",
    )
