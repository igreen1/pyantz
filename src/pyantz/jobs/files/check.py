"""Jobs for asserting conditions about files.

:func:`file_exists` checks that a path exists; :func:`file_contains` uses
memory-mapped I/O to efficiently search for a substring anywhere in a file.
Both return ``False`` (signalling job failure) when the condition is not met.
"""

import mmap
from pathlib import Path

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class ExistsParams(BaseModel):
    """Parameters needed to check if a file exists."""

    file: Path


@add_parameters(ExistsParams)
@no_submit_fn
def file_exists(params: ExistsParams) -> bool:
    """Check if a file exists."""
    return params.file.exists()


class FileContentsParams(BaseModel):
    """Parameters to check if a file contains a substring."""

    # file to check
    file: Path

    # substring to search for in the file
    substring: str


@add_parameters(FileContentsParams)
@no_submit_fn
def file_contains(params: FileContentsParams) -> bool:
    """Check if a file contains a substring."""
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
