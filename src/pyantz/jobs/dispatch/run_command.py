"""Run a job as a subprocess."""

import logging
import pathlib
import subprocess  # nosec

from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command."""

    cmd: list[str]
    environmental_variables: dict[str, str] | None = None
    cwd: str | None = None
    stdout_file: str | None = None
    stderr_file: str | None = None


@config_base.simple_job(Parameters)
def run_command(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Copy file or directory from parameters.soruce to parameters.destination.

    ParametersType {
        source: path/to/copy/from
        destination: path/to/copy/to
    }

    Args:
        parameters (ParametersType): ParametersType for the copy function
        logger (logging.Logger): logger instance

    Returns:
        Status: result of the job

    """
    params_parsed = Parameters.model_validate(parameters)

    try:
        check: bool = False
        if params_parsed.stdout_file or params_parsed.stderr_file:
            check = True

        result = subprocess.run(  # noqa: S603
            params_parsed.cmd,
            env=params_parsed.environmental_variables,
            cwd=params_parsed.cwd,
            check=check,
        )  # nosec

        if params_parsed.stdout_file is not None:  # pylint: disable=duplicate-code
            stdout_save_file = pathlib.Path(params_parsed.stdout_file)
            if not stdout_save_file.parent.exists():
                logger.exception(
                    "Cannot save to stdout file - parent doesn't exist %s", stdout_save_file
                )
                return Status.ERROR
            with stdout_save_file.open("wb") as fh:
                fh.write(result.stdout)
        if params_parsed.stderr_file is not None:  # pylint: disable=duplicate-code
            stderr_save_file = pathlib.Path(params_parsed.stderr_file)
            if not stderr_save_file.parent.exists():
                logger.exception(
                    "Cannot save to stdout file - parent doesn't exist %s", stderr_save_file
                )
                return Status.ERROR
            with stderr_save_file.open("wb") as fh:
                fh.write(result.stderr)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unknown error in submitting!", exc_info=e)
        return Status.ERROR

    return Status.SUCCESS
