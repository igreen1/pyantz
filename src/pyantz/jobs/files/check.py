"""Jobs for asserting conditions about files.

:func:`file_exists` checks that a path exists; :func:`file_contains` uses
memory-mapped I/O to efficiently search for a substring anywhere in a file.
Both return ``False`` (signalling job failure) when the condition is not met.
"""

from __future__ import annotations

import mmap
from pathlib import Path

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class ExistsParams(BaseModel):
    """Parameters needed to check if a file exists."""

    file: Path
    """File (or directory) which must exist."""


@add_parameters(ExistsParams)
@no_submit_fn
def file_exists(params: ExistsParams) -> bool:
    """Check if a file exists.

    Args:
        params: the job's parameters, validated as :class:`ExistsParams`.

    Parameters:
        file (Path): file (or directory) which must exist.

    Returns:
        bool: True if the path exists, otherwise False.

    Raises:
        None: a missing file is reported by returning False.

    Example:
        .. testsetup:: files-check-exists

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-check-exists

            from pathlib import Path

            from pyantz.jobs.files.check import file_exists

            Path("here.txt").touch()
            print(file_exists({"file": "here.txt"}, lambda job: None))
            print(file_exists({"file": "not_here.txt"}, lambda job: None))

        .. testoutput:: files-check-exists

            True
            False

        .. testcleanup:: files-check-exists

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    return params.file.exists()


class FileContentsParams(BaseModel):
    """Parameters to check if a file contains a substring."""

    file: Path
    """File to check."""

    substring: str
    """Substring to search for in the file; it may span lines, in which case it
    must include the line breaks."""


@add_parameters(FileContentsParams)
@no_submit_fn
def file_contains(params: FileContentsParams) -> bool:
    r"""Check if a file contains a substring.

    The file is memory mapped instead of read into memory, so large files can be
    searched. The substring is encoded as UTF-8 and may span several lines.

    Args:
        params: the job's parameters, validated as :class:`FileContentsParams`.

    Parameters:
        file (Path): file to check.
        substring (str): substring to search for, including any line breaks.

    Returns:
        bool: True if the file contains the substring, False if it doesn't or the
        file doesn't exist.

    Raises:
        OSError: if the file exists but can't be read.

    Example:
        .. testsetup:: files-check-contains

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-check-contains

            from pathlib import Path

            from pyantz.jobs.files.check import file_contains

            def submit(job):
                pass

            Path("log.txt").write_text("step 1: ok\nstep 2: ok\n")
            for substring in ("ok\nstep 2", "error"):
                params = {"file": "log.txt", "substring": substring}
                print(file_contains(params, submit))

        .. testoutput:: files-check-contains

            True
            False

        .. testcleanup:: files-check-contains

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if not params.file.exists():
        return False

    # an empty file can't be memory mapped; it only contains the empty substring
    if params.file.stat().st_size == 0:
        return params.substring == ""

    # use memory mapping to efficiently load the file without overloading ram
    # and allow for substrings to span multiple lines
    # user must include line breaks if they wish to search for them
    with (
        params.file.open("rb", 0) as fh,
        mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm,
    ):
        return mm.find(params.substring.encode("utf-8")) != -1
