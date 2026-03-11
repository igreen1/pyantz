"""Run an executable file in a subprocess."""

import logging
import subprocess
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, DirectoryPath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class DispatchParams(BaseModel):
    """Parameters for dispatching jobs."""

    # command to pass to the subprocess
    cmd: tuple[str, ...]

    # If set, and if the timeout expires, the child process will be killed and waited
    timeout: float | None = None

    # input to provide to the subprocess in stdin
    input_stream: bytes | None = None

    # current working directory
    cwd: DirectoryPath | None = None

    # If env is not None, it must be a mapping that defines the environment variables
    # for the new process; these are used instead of the default behavior of inheriting
    # the current process environment
    env: Mapping[str, str] | None

    # file location to write stdout
    # will overwrite any existing file
    # if the same as stderr, will start will stdout and then append stderr
    # will add a header to help distinguish
    stdout_file: Path

    # file location to write stderr
    # if the same as stdout, will start will stdout and then append stderr
    # will add a header to help distinguish
    stderr_file: Path


@add_parameters(DispatchParams)
@no_submit_fn
def dispatch(params: DispatchParams) -> bool:
    """Dispatch a command in a subprocess."""
    logger = logging.getLogger(__name__)

    try:
        results = subprocess.run(  # noqa: S603
            params.cmd,
            capture_output=True,
            check=True,
            timeout=params.timeout,
            input=params.input_stream,
            cwd=params.cwd,
        )

        # save the output for the user
        if params.stdout_file:
            params.stdout_file.parent.mkdir(exist_ok=True, parents=True)
            with params.stdout_file.open("wb") as fh:
                fh.write(results.stdout)
        if params.stderr_file:
            mode = "a" if params.stdout_file else "w"
            with params.stderr_file.open(mode + "b") as fh:
                fh.write(results.stderr)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.exception("Error in dispatch", exc_info=exc)
        return False
    else:
        return True
