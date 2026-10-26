"""File and directory transfer operations.

Provides :func:`rsync` (shell-based, ideal for remote or large trees) and
pure-Python :func:`copy` / :func:`move` alternatives built on
:mod:`shutil`.  All three log errors and return ``False`` on failure rather
than raising exceptions.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn


def _remove(path: Path) -> None:
    """Delete a file or directory tree if it exists.

    Args:
        path: the file, symbolic link or directory to delete.

    Returns:
        None.

    Raises:
        OSError: if the path exists but can't be deleted.

    Example:
        .. testsetup:: files-moving-remove

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-moving-remove

            from pathlib import Path

            from pyantz.jobs.files.moving import _remove

            Path("tree/inner").mkdir(parents=True)
            _remove(Path("tree"))
            _remove(Path("never_existed.txt"))  # missing paths are fine
            print(Path("tree").exists())

        .. testoutput:: files-moving-remove

            False

        .. testcleanup:: files-moving-remove

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


class RsyncParams(BaseModel):
    """Rsync parameters to copy from location to location."""

    source: Path
    """Source directory or file."""

    destination: Path
    """Destination directory or file."""


@add_parameters(RsyncParams)
@no_submit_fn
def rsync(params: RsyncParams) -> bool:
    """Use rsync to copy from source to destination.

    Runs ``rsync -av source destination``, so the ``rsync`` program must be
    installed. As with rsync itself, a trailing ``/`` on a source directory copies
    its contents instead of the directory.

    Args:
        params: the job's parameters, validated as :class:`RsyncParams`.

    Parameters:
        source (Path): source directory or file.
        destination (Path): destination directory or file.

    Returns:
        bool: True if rsync succeeded, False if the source doesn't exist, rsync
        can't be run or rsync fails.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: files-moving-rsync

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-moving-rsync

            import shutil
            from pathlib import Path

            from pyantz.jobs.files.moving import rsync

            Path("data.txt").write_text("hello")
            if shutil.which("rsync"):
                rsync({"source": "data.txt", "destination": "synced.txt"}, None)
            else:  # not installed here, so do what rsync would have done
                shutil.copy("data.txt", "synced.txt")
            print(Path("synced.txt").read_text())

        .. testoutput:: files-moving-rsync

            hello

        .. testcleanup:: files-moving-rsync

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)
    cmd = [
        "rsync",
        "-av",
        os.fspath(params.source),
        os.fspath(params.destination),
    ]

    if not params.source.exists():
        logger.error(
            "Cannot copy - it doesn't exist! %s",
            params.source,
        )
        return False

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            check=True,
            shell=False,
            capture_output=True,
        )
        logger.debug("Rsync copying: %s", result.stdout.decode())
    except subprocess.CalledProcessError as exc:
        logger.exception(
            "Failed to rsync %s: %s",
            params.source,
            exc.stderr.decode(errors="replace"),
            exc_info=exc,
        )
        return False
    except OSError as exc:  # for example, rsync is not installed
        logger.exception("Cannot run rsync", exc_info=exc)
        return False
    else:
        return True


class CopyParams(BaseModel):
    """Copy parameters to copy from location to location."""

    source: Path | str
    """Source directory or file."""

    destination: Path | str
    """Destination directory or file."""

    overwrite: bool = True
    """If true, will overwrite the destination."""


@add_parameters(CopyParams)
@no_submit_fn
def copy(params: CopyParams) -> bool:
    """Use python shutil to copy directories and files.

    The copy is made next to the destination first, and only replaces an existing
    destination once it is complete, so a failed copy leaves the destination as
    it was.

    Args:
        params: the job's parameters, validated as :class:`CopyParams`.

    Parameters:
        source (Path | str): source directory or file.
        destination (Path | str): destination directory or file.
        overwrite (bool): if True, replace an existing destination. Defaults to
            True.

    Returns:
        bool: True if copied, False if the source doesn't exist, the destination
        exists and ``overwrite`` is False, or the copy fails.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: files-moving-copy

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-moving-copy

            from pathlib import Path

            from pyantz.jobs.files.moving import copy

            def submit(job):
                pass

            Path("new.txt").write_text("new")
            Path("old.txt").write_text("old")
            params = {"source": "new.txt", "destination": "old.txt"}
            print(copy({**params, "overwrite": False}, submit))
            print(copy(params, submit), Path("old.txt").read_text())

        .. testoutput:: files-moving-copy

            False
            True new

        .. testcleanup:: files-moving-copy

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)

    source = Path(params.source)
    destination = Path(params.destination)

    if not source.exists():
        logger.error(
            "Cannot copy - it doesn't exist! %s",
            params.source,
        )
        return False
    if destination.exists():
        logger.warning("Destination file already exists!")
        if not params.overwrite:
            logger.error("File exists and not overwriting - cannot copy ")
            return False

    # copy next to the destination first: the existing destination is only
    # replaced once the copy has worked, so a failure doesn't lose its data
    staging = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        if source.is_file():
            shutil.copy2(source, staging)
        else:
            shutil.copytree(source, staging)
        _remove(destination)
        staging.rename(destination)
    except OSError as exc:
        logger.exception("Cannot copy file: %s", source, exc_info=exc)
        _remove(staging)
        return False
    else:
        return True


class MoveParams(BaseModel):
    """Parameters to move a file or directory."""

    source: Path
    """Source directory or file."""

    destination: Path
    """Destination directory or file."""

    overwrite: bool = True
    """If true, will overwrite the destination."""


@add_parameters(MoveParams)
@no_submit_fn
def move(params: MoveParams) -> bool:
    """Move from a source to a destination.

    Uses :func:`shutil.move`, so the move may cross file systems. An existing
    destination is kept aside until the move has worked, and restored if it
    fails.

    Args:
        params: the job's parameters, validated as :class:`MoveParams`.

    Parameters:
        source (Path): source directory or file.
        destination (Path): destination directory or file.
        overwrite (bool): if True, replace an existing destination. Defaults to
            True.

    Returns:
        bool: True if moved, False if the source doesn't exist, the destination
        exists and ``overwrite`` is False, or the move fails.

    Raises:
        OSError: if an existing destination can't be set aside before the move.

    Example:
        .. testsetup:: files-moving-move

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-moving-move

            from pathlib import Path

            from pyantz.jobs.files.moving import move

            Path("results").mkdir()
            Path("results/out.txt").write_text("done")
            move({"source": "results", "destination": "archive"}, lambda job: None)
            print(Path("results").exists(), Path("archive/out.txt").read_text())

        .. testoutput:: files-moving-move

            False done

        .. testcleanup:: files-moving-move

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)

    if not params.source.exists():
        logger.error(
            "Cannot move - it doesn't exist! %s",
            params.source,
        )
        return False
    backup: Path | None = None
    if params.destination.exists():
        logger.warning("Destination file already exists!")
        if not params.overwrite:
            logger.error("File exists and not overwriting - cannot copy ")
            return False
        # keep the old destination until the move has worked
        backup = params.destination.with_name(
            f".{params.destination.name}.{uuid.uuid4().hex}.bak",
        )
        params.destination.rename(backup)

    try:
        shutil.move(params.source, params.destination)
    except OSError as exc:
        logger.exception(
            "Cannot move file! %s",
            params.source,
            exc_info=exc,
        )
        if backup is not None:
            _remove(params.destination)  # anything the failed move left behind
            backup.rename(params.destination)
        return False
    else:
        if backup is not None:
            _remove(backup)
        return True
