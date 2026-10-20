"""Where the application is defined."""

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import endpoints
from .auth import require_token
from .settings import check_safe_to_bind, get_cors_origins, get_settings


def create_app() -> FastAPI:
    """Create the application, reading the cors origins from the environment."""
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
