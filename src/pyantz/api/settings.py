"""Settings of the api servers, read from the environment when a server starts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

HOST_VARIABLE = "PYANTZ_HOST"
PORT_VARIABLE = "PYANTZ_PORT"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MAX_PORT = 65535


class Settings(BaseModel):
    """Where the api server listens."""

    model_config = ConfigDict(frozen=True)

    host: str = DEFAULT_HOST
    port: int = Field(default=DEFAULT_PORT, ge=1, le=MAX_PORT)


def get_settings() -> Settings:
    """Read the settings from `PYANTZ_HOST` and `PYANTZ_PORT`.

    Raises:
        ValueError: if a value is invalid; the message names the variable

    """
    values: dict[str, str] = {}
    if HOST_VARIABLE in os.environ:
        values["host"] = os.environ[HOST_VARIABLE]
    if PORT_VARIABLE in os.environ:
        values["port"] = os.environ[PORT_VARIABLE]
    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        names = {"host": HOST_VARIABLE, "port": PORT_VARIABLE}
        problems = "; ".join(
            f"{names[str(error['loc'][0])]}={values.get(str(error['loc'][0]))!r}: "
            f"{error['msg']}"
            for error in exc.errors()
        )
        msg = f"Invalid server settings: {problems}"
        raise ValueError(msg) from exc


CORS_ORIGINS_VARIABLE = "PYANTZ_CORS_ORIGINS"
API_TOKEN_VARIABLE = "PYANTZ_API_TOKEN"  # noqa: S105
RUNS_DIR_VARIABLE = "PYANTZ_RUNS_DIR"
FRONTEND_DIR_VARIABLE = "PYANTZ_FRONTEND_DIR"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def get_cors_origins() -> list[str]:
    """Get the origins allowed to call the api from `PYANTZ_CORS_ORIGINS`.

    The variable holds comma separated origins, e.g. ``http://localhost:5173``.
    """
    return [
        origin.strip()
        for origin in os.environ.get(CORS_ORIGINS_VARIABLE, "").split(",")
        if origin.strip()
    ]


def get_api_token() -> str | None:
    """Get the token which clients must send, if `PYANTZ_API_TOKEN` is set."""
    return os.environ.get(API_TOKEN_VARIABLE) or None


def get_runs_dir() -> Path:
    """Get the directory holding one working directory per run."""
    if RUNS_DIR_VARIABLE in os.environ:
        return Path(os.environ[RUNS_DIR_VARIABLE])
    return Path(tempfile.gettempdir()) / "pyantz-runs"


def get_frontend_dir() -> Path | None:
    """Get the directory with the built web ui, if `PYANTZ_FRONTEND_DIR` is set.

    Build it with ``npm run build`` in ``frontend/pyantz``, which makes ``dist``.
    The server serves it at ``/`` next to the api, without asking for the token:
    the page has to load to ask the user for it.
    """
    directory = os.environ.get(FRONTEND_DIR_VARIABLE, "").strip()
    return Path(directory) if directory else None


def check_safe_to_bind(settings: Settings) -> None:
    """Refuse to listen on a non-local address when no token protects the api.

    Raises:
        ValueError: if the host is reachable from other machines and there is no
            `PYANTZ_API_TOKEN`

    """
    if settings.host not in LOCAL_HOSTS and get_api_token() is None:
        msg = (
            f"Refusing to listen on {settings.host!r} without authentication: "
            f"set {API_TOKEN_VARIABLE}, or use one of {sorted(LOCAL_HOSTS)}"
        )
        raise ValueError(msg)
