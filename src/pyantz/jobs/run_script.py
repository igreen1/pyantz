"""Specify a script to run and run it"""

import logging
import os
import subprocess  # nosec

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

from pyantz.infrastructure.config.base import *
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """Parameters for running a script"""

    script_path: Annotated[
        str, BeforeValidator(lambda x: x if os.path.exists(x) else None)
    ]
    script_args: list[str] | None = None
    script_prepend: list[str] | None = None
    stdout_save_file: str | None = None
    stderr_save_file: str | None = None
    current_working_dir: str | None = None


@simple_job
def run_script(parameters: ParametersType, logger: logging.Logger) -> Status:
    """Run the script provided by parameters

    Args:
        parameters (ParametersType): _description_

    Returns:
        Status: _description_
    """

    run_parameters = Parameters.model_validate(parameters)

    cmd = []
    if run_parameters.script_prepend is not None:
        cmd.extend(run_parameters.script_prepend)
    if not os.path.exists(run_parameters.script_path):
        raise RuntimeError(f"Unable to find  {run_parameters.script_path}")
    cmd.append(run_parameters.script_path)
    if run_parameters.script_args is not None:
        cmd.extend(run_parameters.script_args)

    try:
        ret = subprocess.run(
            cmd,
            capture_output=True,
            cwd=run_parameters.current_working_dir,
            shell=False,
            check=True,
        )  # nosec

        if run_parameters.stdout_save_file is not None:
            with open(run_parameters.stdout_save_file, "wb") as fh:
                fh.write(ret.stdout)
        if run_parameters.stderr_save_file is not None:
            with open(run_parameters.stderr_save_file, "wb") as fh:
                fh.write(ret.stderr)
    except subprocess.CalledProcessError as exc:
        logger.error("Unknown error in run_script", exc_info=exc)
        # catch all errors because we don't know what will happen
        return Status.ERROR

    return Status.SUCCESS
