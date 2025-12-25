"""Move a file."""

from pathlib import Path

from pydantic import BaseModel, DirectoryPath, FilePath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class MoveParams(BaseModel):
    """Parameters to copy file."""

    # source file to move over
    src: FilePath | DirectoryPath

    # location to place the reuslt
    dst: Path


@add_parameters(MoveParams)
@no_submit_fn
def move(params: MoveParams) -> bool:
    """Move `src` to `dest`."""
    params.src.rename(params.dst)
    return True
