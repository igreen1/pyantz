"""Basic file-system CRUD operations.

Each function is decorated with :func:`~pyantz.infrastructure.config.add_parameters`
so it integrates with PyAntz's type-checked parameter system.

Available jobs:

* :func:`copy` — copy a file or directory tree.
* :func:`move` — rename/move a path.
* :func:`delete` — delete a file or directory.
* :func:`create` — create a file with optional contents.
* :func:`mkdir` — create a directory (including parents).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class CopyParams(BaseModel):
    """Parameters to copy file."""

    model_config = ConfigDict(frozen=True)

    src: Path
    """Source file or directory to copy."""

    dst: Path
    """Location to create the copy."""


@add_parameters(CopyParams)
@no_submit_fn
def copy(params: CopyParams) -> bool:
    """Copy from src to destination.

    A file is copied with its metadata (:func:`shutil.copy2`); a directory is
    copied with everything inside it (:func:`shutil.copytree`).

    Args:
        params: the job's parameters, validated as :class:`CopyParams`.

    Parameters:
        src (Path): source file or directory to copy.
        dst (Path): location to create the copy.

    Returns:
        bool: True once the copy is made.

    Raises:
        OSError: if the copy fails, e.g., ``src`` doesn't exist or ``dst`` is a
            directory which already exists.

    Example:
        .. testsetup:: files-simple-copy

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-simple-copy

            from pathlib import Path

            from pyantz.jobs.files.simple import copy

            Path("original.txt").write_text("hello")
            copy({"src": "original.txt", "dst": "copied.txt"}, lambda job: None)
            print(Path("copied.txt").read_text())

        .. testoutput:: files-simple-copy

            hello

        .. testcleanup:: files-simple-copy

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if params.src.is_file():
        shutil.copy2(params.src, params.dst)
    else:
        shutil.copytree(params.src, params.dst)
    return True


class MoveParams(BaseModel):
    """Parameters to move a file."""

    model_config = ConfigDict(frozen=True)

    src: Path
    """Source file or directory to move."""

    dst: Path
    """Location to place the result."""


@add_parameters(MoveParams)
@no_submit_fn
def move(params: MoveParams) -> bool:
    """Move `src` to `dst`.

    Uses :meth:`pathlib.Path.rename`, so both paths must be on the same file
    system; see :func:`pyantz.jobs.files.moving.move` for moves across them.

    Args:
        params: the job's parameters, validated as :class:`MoveParams`.

    Parameters:
        src (Path): source file or directory to move.
        dst (Path): location to place the result.

    Returns:
        bool: True once moved.

    Raises:
        OSError: if the move fails, e.g., ``src`` doesn't exist.

    Example:
        .. testsetup:: files-simple-move

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-simple-move

            from pathlib import Path

            from pyantz.jobs.files.simple import move

            Path("before.txt").write_text("hello")
            move({"src": "before.txt", "dst": "after.txt"}, lambda job: None)
            print(Path("before.txt").exists(), Path("after.txt").read_text())

        .. testoutput:: files-simple-move

            False hello

        .. testcleanup:: files-simple-move

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    params.src.rename(params.dst)
    return True


class DeleteParams(BaseModel):
    """Parameters to define what to delete."""

    model_config = ConfigDict(frozen=True)

    path: Path
    """Location to delete."""

    missing_ok: bool = True
    """If true, deleting a path which doesn't exist succeeds."""

    recursive: bool = False
    """If true, directories are deleted with everything inside them (otherwise
    only empty directories can be deleted)."""


@add_parameters(DeleteParams)
@no_submit_fn
def delete(params: DeleteParams) -> bool:
    """Delete the file passed in delete params.

    Args:
        params: the job's parameters, validated as :class:`DeleteParams`.

    Parameters:
        path (Path): file or directory to delete.
        missing_ok (bool): if True, a missing path counts as success. Defaults to
            True.
        recursive (bool): if True, delete directories with everything inside
            them. Defaults to False.

    Returns:
        bool: True if the path was deleted (or was missing and ``missing_ok``),
        False if it was missing and not ``missing_ok``, or is a directory which
        isn't empty and not ``recursive``.

    Raises:
        OSError: if a file or tree can't be deleted, e.g., for lack of permission.

    Example:
        .. testsetup:: files-simple-delete

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-simple-delete

            from pathlib import Path

            from pyantz.jobs.files.simple import delete

            def submit(job):
                pass

            Path("full_dir").mkdir()
            Path("full_dir/file.txt").touch()
            print(delete({"path": "full_dir"}, submit))
            print(delete({"path": "full_dir", "recursive": True}, submit))
            print(delete({"path": "full_dir", "missing_ok": False}, submit))

        .. testoutput:: files-simple-delete

            False
            True
            False

        .. testcleanup:: files-simple-delete

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if not params.path.exists():
        return params.missing_ok

    if params.path.is_file():
        params.path.unlink()
    elif params.recursive:
        shutil.rmtree(params.path)
    else:
        try:
            params.path.rmdir()
        except OSError:
            logging.getLogger(__name__).exception(
                "Cannot delete %s: it is not empty (use recursive to delete it anyway)",
                params.path,
            )
            return False

    return True


class CreateFileParams(BaseModel):
    """Required inputs to create a file."""

    model_config = ConfigDict(frozen=True)

    path: Path
    """Path to the file to create."""

    contents: str | None = None
    """Optionally, text to write to the file."""

    overwrite: bool = True
    """If true, replaces the file if it exists (if ``contents`` is empty, clears
    it)."""


@add_parameters(CreateFileParams)
@no_submit_fn
def create(params: CreateFileParams) -> bool:
    """Create the file as requested and write contents if provided.

    If the file exists and `overwrite` is false, its contents are never changed:
    asking to write contents to it fails.

    Args:
        params: the job's parameters, validated as :class:`CreateFileParams`.

    Parameters:
        path (Path): path to the file to create.
        contents (str | None): text to write to the file. Defaults to None (an
            empty file).
        overwrite (bool): if True, replace an existing file. Defaults to True.

    Returns:
        bool: True if the file was created, False if it exists, ``overwrite`` is
        False and ``contents`` were given.

    Raises:
        OSError: if the file can't be written, e.g., its directory doesn't exist.

    Example:
        .. testsetup:: files-simple-create

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-simple-create

            from pathlib import Path

            from pyantz.jobs.files.simple import create

            def submit(job):
                pass

            print(create({"path": "new.txt", "contents": "first"}, submit))
            print(
                create(
                    {"path": "new.txt", "contents": "second", "overwrite": False},
                    submit,
                )
            )
            print(Path("new.txt").read_text())

        .. testoutput:: files-simple-create

            True
            False
            first

        .. testcleanup:: files-simple-create

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if params.path.exists() and not params.overwrite and params.contents:
        logging.getLogger(__name__).error(
            "Not writing to %s: it exists and overwrite is false",
            params.path,
        )
        return False
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
    """Path of the directory to create."""


@add_parameters(Mkdirparams)
@no_submit_fn
def mkdir(params: Mkdirparams) -> bool:
    """Create the directory, and any missing parents (it may already exist).

    Args:
        params: the job's parameters, validated as :class:`Mkdirparams`.

    Parameters:
        dir_path (Path): path of the directory to create.

    Returns:
        bool: True once the directory exists.

    Raises:
        OSError: if the directory can't be created, e.g., a file has its path.

    Example:
        .. testsetup:: files-simple-mkdir

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-simple-mkdir

            from pathlib import Path

            from pyantz.jobs.files.simple import mkdir

            mkdir({"dir_path": "a/b/c"}, lambda job: None)
            print(Path("a/b/c").is_dir())

        .. testoutput:: files-simple-mkdir

            True

        .. testcleanup:: files-simple-mkdir

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    params.dir_path.mkdir(parents=True, exist_ok=True)

    return True
