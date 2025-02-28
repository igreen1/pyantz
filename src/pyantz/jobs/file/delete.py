"""Delete a file or directory

params = {
    "path" (str): the path to delete
}
"""

import logging
import os
import shutil

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command"""

    path: Annotated[str, BeforeValidator(lambda x: x if os.path.exists(x) else None)]


@config_base.simple_job(Parameters)
def delete(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Deletes parameters.path

    Args:
        parameters (ParametersType): params of form
            {
                path (str): path/to/delete
            }

    Returns:
        Status: Resulting status of the job after execution
    """

    del_params = Parameters.model_validate(parameters)
    if os.path.isdir(del_params.path):
        try:
            shutil.rmtree(del_params.path)
        except (PermissionError, FileNotFoundError, IOError) as exc:
            logger.error("Unable to delete dir", exc_info=exc)
            return Status.ERROR
    elif os.path.isfile(del_params.path):
        try:
            os.remove(del_params.path)
        except (PermissionError, FileNotFoundError, IOError) as exc:
            logger.error("Unable to delete file", exc_info=exc)
            return Status.ERROR
    else:
        return Status.ERROR

    return Status.SUCCESS
