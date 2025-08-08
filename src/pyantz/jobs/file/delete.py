"""Delete a file or directory.

params = {
    "path" (str): the path to delete
}
"""

import logging
import pathlib
import shutil

from pydantic import BaseModel, DirectoryPath, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command."""

    path: str


class _RuntimeParameters(BaseModel, frozen=True):
    """Parameters at runtime will check for existence.

    Files may be created during the pipeline, so must check at actual runtime.
    """

    path: FilePath | DirectoryPath


@config_base.simple_job(Parameters)
def delete(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Delete parameters.path.

    Args:
        parameters (ParametersType): params of form
            {
                path (str): path/to/delete
            }
        logger: logger for debugging

    Returns:
        Status: Resulting status of the job after execution

    """
    del_params = _RuntimeParameters.model_validate(parameters)
    path_to_delete = pathlib.Path(del_params.path)
    if path_to_delete.is_dir():
        try:
            # use rmtree to allow for directories with files
            shutil.rmtree(del_params.path)
        except (OSError, PermissionError, FileNotFoundError) as exc:
            logger.exception("Unable to delete dir", exc_info=exc)
            return Status.ERROR
    elif path_to_delete.is_file():
        try:
            path_to_delete.unlink()
        except (OSError, PermissionError, FileNotFoundError) as exc:
            logger.exception("Unable to delete file", exc_info=exc)
            return Status.ERROR
    else:
        return Status.ERROR

    return Status.SUCCESS
