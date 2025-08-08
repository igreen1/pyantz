"""Copy job will copy a file or directory to another location."""

import logging
import pathlib
import shutil
from shutil import SameFileError, SpecialFileError

from pydantic import BaseModel, DirectoryPath, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command."""

    source: str
    destination: str
    infer_name: bool = False


class _RuntimeParameters(BaseModel, frozen=True):
    """Parameters used at runtime to check for file existence.

    Source must exist for copy to work.
    """

    source: FilePath | DirectoryPath
    destination: str
    infer_name: bool = False


@config_base.simple_job(Parameters)
def copy(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Copy file or directory from parameters.soruce to parameters.destination.

    ParametersType {
        source: path/to/copy/from
        destination: path/to/copy/to
    }

    Args:
        parameters (ParametersType): ParametersType for the copy function
        logger (logging.Logger): logging instance

    Returns:
        Status: result of the job

    """
    copy_parameters = _RuntimeParameters.model_validate(parameters)

    source = pathlib.Path(copy_parameters.source)
    if not source.exists():
        return Status.ERROR

    if source.is_file():
        logger.debug("Copying file")
        return _copy_file(copy_parameters, logger)

    logger.debug("Copying directory")
    return _copy_dir(copy_parameters, logger)


def _copy_file(copy_parameters: _RuntimeParameters, logger: logging.Logger) -> Status:
    """Copy a file from source to destination.

    Args:
        copy_parameters (Parameters): ParametersType of the copy job
        logger (logging.Logger): logging instance

    Returns:
        Status: resulitng status after running the job

    """
    src = pathlib.Path(copy_parameters.source)
    dst = pathlib.Path(copy_parameters.destination)

    if dst.exists() and dst.is_dir() and copy_parameters.infer_name:
        dst = dst / src.name

    if dst.exists() and dst.is_dir():
        return Status.ERROR

    dst_dir = dst.parent
    dst_dir.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copyfile(src, dst)
    except (SameFileError, SpecialFileError, IsADirectoryError, FileNotFoundError) as exc:
        logger.exception("Unexpected error! Cannot copy %s to %s", src, dst, exc_info=exc)
        return Status.ERROR
    return Status.SUCCESS


def _copy_dir(
    copy_parameters: _RuntimeParameters,
    logger: logging.Logger,
) -> Status:
    """Copy a directory from a source to destination.

    Args:
        copy_parameters (CopyParameters): ParametersType of the copy job.
        logger (logging.Logger): logger instance

    Returns:
        Status: resulitng status after running the job

    """
    src = pathlib.Path(copy_parameters.source)
    dst = pathlib.Path(copy_parameters.destination)

    if dst.exists() and dst.is_file():
        logger.error("Cannot copy %s to existing file %s", src, dst)
        return Status.ERROR

    try:
        shutil.copytree(src, dst)
    # oserror,
    except OSError as exc:
        logger.exception("Unable to copy %s to dir %s", src, dst, exc_info=exc)
        return Status.ERROR
    return Status.SUCCESS
