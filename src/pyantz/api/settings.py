"""Settings of the api servers, read from the environment when a server starts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

HOST_VARIABLE = "PYANTZ_HOST"
"""Environment variable with the address the api server listens on."""

PORT_VARIABLE = "PYANTZ_PORT"
"""Environment variable with the port the api server listens on."""

DEFAULT_HOST = "127.0.0.1"
"""Address the server listens on by default (only this machine)."""

DEFAULT_PORT = 8000
"""Port the server listens on by default."""

MAX_PORT = 65535
"""Largest valid port."""


class Settings(BaseModel):
    """Where the api server listens."""

    model_config = ConfigDict(frozen=True)

    host: str = DEFAULT_HOST
    """Address to listen on."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=MAX_PORT)
    """Port to listen on."""


def get_settings() -> Settings:
    """Read the settings from `PYANTZ_HOST` and `PYANTZ_PORT`.

    Args:
        None.

    Returns:
        Settings: the settings, with defaults for the variables which aren't set.

    Raises:
        ValueError: if a value is invalid; the message names the variable

    Example:
        .. testcode::

            import os

            from pyantz.api.settings import get_settings

            os.environ["PYANTZ_PORT"] = "70000"
            try:
                get_settings()
            except ValueError as exc:
                print(str(exc).split(":")[1].strip())
            finally:
                del os.environ["PYANTZ_PORT"]

        .. testoutput::

            PYANTZ_PORT='70000'

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
"""Environment variable with the comma separated origins allowed by CORS."""

API_TOKEN_VARIABLE = "PYANTZ_API_TOKEN"  # noqa: S105
"""Environment variable with the token clients must send, if any."""

RUNS_DIR_VARIABLE = "PYANTZ_RUNS_DIR"
"""Environment variable with the directory holding the runs' directories."""

FRONTEND_DIR_VARIABLE = "PYANTZ_FRONTEND_DIR"
"""Environment variable with the directory of a built web ui to serve."""

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
"""Addresses which only this machine can reach."""


def get_cors_origins() -> list[str]:
    """Get the origins allowed to call the api from `PYANTZ_CORS_ORIGINS`.

    The variable holds comma separated origins, e.g. ``http://localhost:5173``.

    Args:
        None.

    Returns:
        list[str]: the origins; empty if the variable isn't set.

    Raises:
        None.

    Example:
        .. testcode::

            import os

            from pyantz.api.settings import get_cors_origins

            os.environ["PYANTZ_CORS_ORIGINS"] = "http://localhost:5173, ,http://a.b"
            try:
                print(get_cors_origins())
            finally:
                del os.environ["PYANTZ_CORS_ORIGINS"]

        .. testoutput::

            ['http://localhost:5173', 'http://a.b']

    """
    return [
        origin.strip()
        for origin in os.environ.get(CORS_ORIGINS_VARIABLE, "").split(",")
        if origin.strip()
    ]


def get_api_token() -> str | None:
    """Get the token which clients must send, if `PYANTZ_API_TOKEN` is set.

    Args:
        None.

    Returns:
        str | None: the token, or None if the variable isn't set or is empty.

    Raises:
        None.

    """
    return os.environ.get(API_TOKEN_VARIABLE) or None


def get_runs_dir() -> Path:
    """Get the directory holding one working directory per run.

    Args:
        None.

    Returns:
        Path: `PYANTZ_RUNS_DIR` if set, otherwise ``pyantz-runs`` in the system's
        temporary directory.

    Raises:
        None.

    """
    if RUNS_DIR_VARIABLE in os.environ:
        return Path(os.environ[RUNS_DIR_VARIABLE])
    return Path(tempfile.gettempdir()) / "pyantz-runs"


def get_frontend_dir() -> Path | None:
    """Get the directory with the built web ui, if `PYANTZ_FRONTEND_DIR` is set.

    Build it with ``npm run build`` in ``frontend/pyantz``, which makes ``dist``.
    The server serves it at ``/`` next to the api, without asking for the token:
    the page has to load to ask the user for it.

    Args:
        None.

    Returns:
        Path | None: the directory, or None if the variable isn't set.

    Raises:
        None.

    """
    directory = os.environ.get(FRONTEND_DIR_VARIABLE, "").strip()
    return Path(directory) if directory else None


def check_safe_to_bind(settings: Settings) -> None:
    """Refuse to listen on a non-local address when no token protects the api.

    Args:
        settings: where the server is to listen.

    Returns:
        None.

    Raises:
        ValueError: if the host is reachable from other machines and there is no
            `PYANTZ_API_TOKEN`

    Example:
        .. testcode::

            from pyantz.api.settings import Settings, check_safe_to_bind

            check_safe_to_bind(Settings(host="localhost"))  # fine
            try:
                check_safe_to_bind(Settings(host="0.0.0.0"))
            except ValueError:
                print("refused")

        .. testoutput::

            refused

    """
    if settings.host not in LOCAL_HOSTS and get_api_token() is None:
        msg = (
            f"Refusing to listen on {settings.host!r} without authentication: "
            f"set {API_TOKEN_VARIABLE}, or use one of {sorted(LOCAL_HOSTS)}"
        )
        raise ValueError(msg)
