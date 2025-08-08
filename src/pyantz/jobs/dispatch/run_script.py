"""Specify a script to run and run it."""

import logging
import os
import pathlib

from pydantic import BaseModel, ConfigDict, DirectoryPath, FilePath, JsonValue

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status

from .run_command import run_command


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

    model_config = ConfigDict(coerce_numbers_to_str=True)

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

    cwd: str | None = (
        os.fspath(run_parameters.current_working_dir)
        if run_parameters.current_working_dir is not None
        else run_parameters.current_working_dir
    )

    cmd_type_check: JsonValue = cmd  # type: ignore[assignment] # pyright: ignore[reportAssignmentType] # pylint: disable=line-too-long
    return run_command(
        {
            "cmd": cmd_type_check,
            "stdout_file": run_parameters.stdout_save_file,
            "stderr_file": run_parameters.stderr_save_file,
            "cwd": cwd,
        },
        logger,
    )
