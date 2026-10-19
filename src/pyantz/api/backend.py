"""Where the application is defined."""

import uvicorn
from fastapi import FastAPI

from . import endpoints
from .settings import get_settings

app = FastAPI()

app.include_router(endpoints.router)


def start_prod_server() -> None:
    """Start a production server."""
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
