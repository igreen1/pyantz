"""Where the application is defined."""

import os

import uvicorn
from fastapi import FastAPI

from . import endpoints

app = FastAPI()

app.include_router(endpoints.router)


host = os.environ.get("PYANTZ_HOST", "127.0.0.1")
port = int(os.environ.get("PYANTZ_PORT", "8000"))


def start_prod_server() -> None:
    """Start a production server."""
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
