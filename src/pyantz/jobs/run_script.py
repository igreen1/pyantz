"""Specify a script to run and run it."""

import logging
import os
import pathlib
import subprocess  # nosec

from pydantic import BaseModel, DirectoryPath, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """Parameters for running a script."""

    script_path: str
    script_args: list[str] | None = None
    script_prepend: list[str] | None = None
    stdout_save_file: str | None = None
    stderr_save_file: str | None = None
    current_working_dir: str | None = None


class _RuntimeParameters(BaseModel, frozen=True):
    """Parameters for running a script.

    The files may not exist at 'compilation', but they must exist
    when we run the job. So, this class is used at rutnime
    """

    script_path: FilePath
    script_args: list[str] | None = None
    script_prepend: list[str] | None = None
    stdout_save_file: str | None = None  # will be created by this job
    stderr_save_file: str | None = None  # will be created by this job
    current_working_dir: DirectoryPath | None = None


@config_base.simple_job(Parameters)
def run_script(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Run the script provided by parameters.

    Args:
        parameters (ParametersType): parameters of this job
        logger: logger instance (handled by manager)

    Returns:
        Status: _description_

    """
    run_parameters = _RuntimeParameters.model_validate(parameters)

    cmd: list[str] = []
    if run_parameters.script_prepend is not None:
        cmd.extend(run_parameters.script_prepend)

    script_path = pathlib.Path(run_parameters.script_path)
    if not script_path.exists():
        msg = f"Unable to find  {run_parameters.script_path}"
        raise FileNotFoundError(msg)
    cmd.append(os.fspath(script_path))
    if run_parameters.script_args is not None:
        cmd.extend(run_parameters.script_args)

    try:
        ret = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            cwd=run_parameters.current_working_dir,
            shell=False,
            check=True,
        )  # nosec
        if run_parameters.stdout_save_file is not None:
            stdout_save_file = pathlib.Path(run_parameters.stdout_save_file)
            if not stdout_save_file.parent.exists():
                logger.exception(
                    "Cannot save to stdout file - parent doesn't exist %s", stdout_save_file
                )
                return Status.ERROR
            with stdout_save_file.open("wb") as fh:
                fh.write(ret.stdout)
        if run_parameters.stderr_save_file is not None:
            stderr_save_file = pathlib.Path(run_parameters.stderr_save_file)
            if not stderr_save_file.parent.exists():
                logger.exception(
                    "Cannot save to stdout file - parent doesn't exist %s", stderr_save_file
                )
                return Status.ERROR
            with stderr_save_file.open("wb") as fh:
                fh.write(ret.stderr)
    except subprocess.CalledProcessError as exc:
        logger.exception("Unknown error in run_script", exc_info=exc)
        # catch all errors because we don't know what will happen
        return Status.ERROR

    return Status.SUCCESS
