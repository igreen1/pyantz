"""Run arbitrary executables as subprocesses.

:func:`dispatch` wraps Python's :func:`subprocess.run` with optional
stdout/stderr capture to files, environment variable overrides, a working
directory, and a timeout.  It returns ``True`` on success (exit code 0)
and ``False`` on :exc:`subprocess.CalledProcessError` or timeout.
"""

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
    env: Mapping[str, str] | None = None

    # file location to write stdout
    # will overwrite any existing file
    # if the same as stderr, will start will stdout and then append stderr
    # will add a header to help distinguish
    stdout_file: Path | str | None = None

    # file location to write stderr
    # if the same as stdout, will start will stdout and then append stderr
    # will add a header to help distinguish
    stderr_file: Path | str | None = None


STDERR_HEADER = b"\n--- stderr ---\n"


def _save_output(params: DispatchParams, stdout: bytes, stderr: bytes) -> None:
    """Write the captured output to the files the user asked for."""
    stdout_file = Path(params.stdout_file) if params.stdout_file else None
    stderr_file = Path(params.stderr_file) if params.stderr_file else None

    if stdout_file:
        stdout_file.parent.mkdir(exist_ok=True, parents=True)
        stdout_file.write_bytes(stdout)
    if stderr_file:
        stderr_file.parent.mkdir(exist_ok=True, parents=True)
        if stdout_file and stdout_file.resolve() == stderr_file.resolve():
            # one file for both: stdout was just written, so add stderr after it
            with stderr_file.open("ab") as fh:
                fh.write(STDERR_HEADER + stderr)
        else:
            stderr_file.write_bytes(stderr)


@add_parameters(DispatchParams)
@no_submit_fn
def dispatch(params: DispatchParams) -> bool:
    """Dispatch a command in a subprocess.

    The output is saved to the requested files whether or not the command succeeds.
    """
    logger = logging.getLogger(__name__)

    try:
        results = subprocess.run(  # noqa: S603
            params.cmd,
            capture_output=True,
            check=True,
            timeout=params.timeout,
            input=params.input_stream,
            cwd=params.cwd,
            env=params.env,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        logger.exception(
            "Error in dispatch; stderr: %s",
            stderr.decode(errors="replace"),
            exc_info=exc,
        )
        _save_output(params, stdout, stderr)
        return False
    except OSError as exc:  # for example, the command does not exist
        logger.exception("Cannot run %s", params.cmd, exc_info=exc)
        return False

    _save_output(params, results.stdout, results.stderr)
    return True
