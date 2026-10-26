"""Run arbitrary executables as subprocesses.

:func:`dispatch` wraps Python's :func:`subprocess.run` with optional
stdout/stderr capture to files, environment variable overrides, a working
directory, and a timeout.  It returns ``True`` on success (exit code 0)
and ``False`` on :exc:`subprocess.CalledProcessError` or timeout.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, DirectoryPath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class DispatchParams(BaseModel):
    """Parameters for dispatching jobs."""

    cmd: tuple[str, ...]
    """Command to run: the program followed by its arguments."""

    timeout: float | None = None
    """If set, and if the timeout (in seconds) expires, the child process is
    killed and waited for."""

    input_stream: bytes | None = None
    """Input to provide to the subprocess in stdin."""

    cwd: DirectoryPath | None = None
    """Working directory of the subprocess; it must exist."""

    env: Mapping[str, str] | None = None
    """If not None, the environment variables of the new process, used instead of
    inheriting the current process environment."""

    stdout_file: Path | str | None = None
    """File to write stdout to, overwriting any existing file. If the same as
    ``stderr_file``, it starts with stdout and then has stderr appended after a
    header."""

    stderr_file: Path | str | None = None
    """File to write stderr to. If the same as ``stdout_file``, stderr is appended
    after stdout and a header."""


STDERR_HEADER = b"\n--- stderr ---\n"
"""Separates stdout from stderr when both are written to the same file."""


def _save_output(params: DispatchParams, stdout: bytes, stderr: bytes) -> None:
    """Write the captured output to the files the user asked for.

    Missing parent directories are created. When ``stdout_file`` and
    ``stderr_file`` are the same file, it holds stdout, :data:`STDERR_HEADER` and
    then stderr.

    Args:
        params: the dispatch parameters naming the output files.
        stdout: the captured stdout.
        stderr: the captured stderr.

    Returns:
        None.

    Raises:
        OSError: if a file can't be written.

    Example:
        .. testsetup:: subproc-save-output

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: subproc-save-output

            from pathlib import Path

            from pyantz.jobs.subproc.dispatch import DispatchParams, _save_output

            params = DispatchParams(
                cmd=("unused",), stdout_file="logs/out.txt", stderr_file="logs/out.txt"
            )
            _save_output(params, b"some output", b"a warning")
            print(Path("logs/out.txt").read_text())

        .. testoutput:: subproc-save-output

            some output
            --- stderr ---
            a warning

        .. testcleanup:: subproc-save-output

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
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
    The command is run directly, without a shell.

    Args:
        params: the job's parameters, validated as :class:`DispatchParams`.

    Parameters:
        cmd (tuple[str, ...]): the program to run followed by its arguments.
        timeout (float | None): seconds after which the process is killed.
            Defaults to None (no timeout).
        input_stream (bytes | None): input for the process's stdin. Defaults to
            None.
        cwd (Path | None): working directory of the process, which must exist.
            Defaults to None (this process's).
        env (Mapping[str, str] | None): environment variables of the process,
            replacing this process's. Defaults to None (inherit them).
        stdout_file (Path | str | None): file to write stdout to. Defaults to
            None.
        stderr_file (Path | str | None): file to write stderr to; it may be
            ``stdout_file``. Defaults to None.

    Returns:
        bool: True if the command exited with code 0, False if it exited with
        another code, timed out or couldn't be started.

    Raises:
        OSError: if an output file can't be written.

    Example:
        .. testsetup:: subproc-dispatch

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: subproc-dispatch

            import sys
            from pathlib import Path

            from pyantz.jobs.subproc.dispatch import dispatch

            success = dispatch(
                {
                    "cmd": [sys.executable, "-c", "print(input().upper())"],
                    "input_stream": b"hello",
                    "stdout_file": "stdout.txt",
                },
                lambda job: None,
            )
            print(success, Path("stdout.txt").read_text().strip())

        .. testoutput:: subproc-dispatch

            True HELLO

        .. testcleanup:: subproc-dispatch

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

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
