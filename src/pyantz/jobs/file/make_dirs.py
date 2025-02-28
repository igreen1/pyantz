"""Make dirs calls os.makedirs to create directories."""

import logging
import os

from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class MakeDirsModel(BaseModel):
    """Parameters for make_dirs"""

    path: str
    exist_ok: bool = False


@config_base.simple_job(MakeDirsModel)
def make_dirs(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Make directories for a given path

    Args:
        path (str): path to create
    """
    params_parsed = MakeDirsModel.model_validate(parameters)

    try:
        os.makedirs(params_parsed.path, exist_ok=params_parsed.exist_ok)
    except FileExistsError as exc:
        logger.error("Directory %s already exists", params_parsed.path, exc_info=exc)
        return Status.ERROR
    except PermissionError as exc:
        logger.error("Permission denied to create directory", exc_info=exc)
        return Status.ERROR

    return Status.SUCCESS
