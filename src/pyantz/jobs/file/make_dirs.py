"""Make dirs calls os.makedirs to create directories."""

import logging
import os

from pydantic import BaseModel

from pyantz.infrastructure.config.base import ParametersType, simple_job
from pyantz.infrastructure.core.status import Status


class MakeDirsModel(BaseModel):
    """Parameters for make_dirs"""

    path: str
    exist_ok: bool = False


@simple_job
def make_dirs(parameters: ParametersType, logger: logging.Logger) -> None:
    """Make directories for a given path

    Args:
        path (str): path to create
    """
    params_parsed = MakeDirsModel.model_validate(parameters)

    try:
        print(params_parsed.exist_ok)
        os.makedirs(params_parsed.path, exist_ok=params_parsed.exist_ok)
    except FileExistsError as exc:
        logger.error(f"Directory {params_parsed.path} already exists", exc_info=exc)
        return Status.ERROR
    except Exception as exc:
        logger.error(f"Failed to create directory {params_parsed.path}", exc_info=exc)
        return Status.ERROR

    return Status.SUCCESS
