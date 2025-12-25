"""Copy files or directories."""

import shutil
from pathlib import Path

from pydantic import BaseModel, DirectoryPath, FilePath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class CopyParams(BaseModel):
    """Parameters to copy file."""

    # source file to copy over
    src: FilePath | DirectoryPath

    # location to create the copy
    dst: Path


@add_parameters(CopyParams)
@no_submit_fn
def copy(params: CopyParams) -> bool:
    """Copy from src to destination."""
    if params.src.is_file():
        shutil.copy2(params.src, params.dst)
    else:
        shutil.copytree(params.src, params.dst)
    return True
