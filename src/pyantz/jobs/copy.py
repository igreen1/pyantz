"""Copy job will copy a file or directory to another location"""

import logging
import os
import shutil

from pydantic import BaseModel

from pyantz.infrastructure.config.base import ParametersType, simple_job
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command"""

    source: str
    destination: str
    infer_name: bool = False


@simple_job
def copy(parameters: ParametersType, logger: logging.Logger) -> Status:
    """Copy file or directory from parameters.soruce to parameters.destination

    ParametersType {
        source: path/to/copy/from
        destination: path/to/copy/to
    }

    Args:
        parameters (ParametersType): ParametersType for the copy function

    Returns:
        Status: result of the job
    """
    if parameters is None:
        return Status.ERROR
    copy_parameters = Parameters.model_validate(parameters)

    source = copy_parameters.source

    if not os.path.exists(source):
        return Status.ERROR
    source_is_file = os.path.isfile(source)

    if source_is_file:
        logger.debug("Copying file")
        return _copy_file(copy_parameters)

    logger.debug("Copying directory")
    return _copy_dir(copy_parameters)


def _copy_file(copy_parameters: Parameters) -> Status:
    """Copy a file from source to destination

    Args:
        copy_parameters (Parameters): ParametersType of the copy job

    Returns:
        Status: resulitng status after running the job
    """
    src = copy_parameters.source
    dst = copy_parameters.destination

    if os.path.exists(dst) and os.path.isdir(dst):
        if copy_parameters.infer_name:
            dst = os.path.join(dst, os.path.basename(src))

    if os.path.exists(dst) and os.path.isdir(dst):
        return Status.ERROR

    dst_dir = os.path.dirname(dst)
    os.makedirs(dst_dir, exist_ok=True)

    try:
        shutil.copyfile(src, dst)
        return Status.SUCCESS
    except Exception as _exc:  # pylint: disable=broad-exception-caught
        return Status.ERROR


def _copy_dir(copy_parameters: Parameters) -> Status:
    """Copy a directory from a source to destination
    Args:
        copy_parameters (CopyParameters): ParametersType of the copy job

    Returns:
        Status: resulitng status after running the job
    """

    src = copy_parameters.source
    dst = copy_parameters.destination

    if os.path.exists(dst) and os.path.isfile(dst):
        return Status.ERROR

    try:
        shutil.copytree(src, dst)
        return Status.SUCCESS
    except Exception as _exc:  # pylint: disable=broad-exception-caught
        return Status.ERROR
