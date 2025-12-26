"""Simle file (CRUD) operations."""

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



class DeleteParams(BaseModel):
    """Parameters to define what to delete."""

    # location to delete
    path: FilePath | DirectoryPath

    missing_ok: bool = True


@add_parameters(DeleteParams)
@no_submit_fn
def delete(params: DeleteParams) -> bool:
    """Delete the file passed in delete params."""
    if not params.path.exists():
        return params.missing_ok

    if params.path.is_file():
        params.path.unlink()
    else:
        params.path.rmdir()

    return True


class CreateFileParams(BaseModel):
    """Required inputs to create a file."""

    # path to the file to create
    path: Path

    # optionally, write the text contents to file
    contents: str | None = None

    # if set to true, overwrites the contents of the file
    # if contents is empty and overwrite is true, clears it
    overwrite: bool = True


@add_parameters(CreateFileParams)
@no_submit_fn
def create(params: CreateFileParams) -> bool:
    """Create the file as requested and write contents if provided."""
    if params.overwrite:
        params.path.unlink(missing_ok=True)
    params.path.touch(exist_ok=True)

    if params.contents:
        params.path.write_text(params.contents, encoding="utf-8")

    return True
