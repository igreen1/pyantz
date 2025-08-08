"""Make dirs calls os.makedirs to create directories."""

import logging
import pathlib

from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel):
    """Parameters for make_dirs."""

    path: str
    exist_ok: bool = False


@config_base.simple_job(Parameters)
def make_dirs(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Make directories for a given path.

    Args:
        parameters (Parameters): parameters with the path to create
        logger (logging.Logger): logger

    """
    params_parsed = Parameters.model_validate(parameters)

    try:
        pathlib.Path(params_parsed.path).mkdir(parents=True, exist_ok=params_parsed.exist_ok)
    except FileExistsError as exc:
        logger.exception("Directory %s already exists", params_parsed.path, exc_info=exc)
        return Status.ERROR
    except PermissionError as exc:
        logger.exception("Permission denied to create directory", exc_info=exc)
        return Status.ERROR

    return Status.SUCCESS
