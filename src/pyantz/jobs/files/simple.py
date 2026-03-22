"""Simle file (CRUD) operations."""

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class CopyParams(BaseModel):
    """Parameters to copy file."""

    model_config = ConfigDict(frozen=True)

    # source file to copy over
    src: Path

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

    model_config = ConfigDict(frozen=True)

    # source file to move over
    src: Path

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

    model_config = ConfigDict(frozen=True)

    # location to delete
    path: Path

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

    model_config = ConfigDict(frozen=True)

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


class Mkdirparams(BaseModel):
    """Required input to create a directory."""

    model_config = ConfigDict(frozen=True)

    dir_path: Path


@add_parameters(Mkdirparams)
@no_submit_fn
def mkdir(params: Mkdirparams) -> bool:
    """Create the file as requested and write contents if provided."""
    params.dir_path.mkdir(parents=True, exist_ok=True)

    return True
