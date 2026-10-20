"""Settings of the api servers, read from the environment when a server starts."""

import os

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
