"""Operations for copying files and directories."""

import logging
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn

if TYPE_CHECKING:
    from pathlib import Path


class RsyncParams(BaseModel):
    """Rsync parameters to copy from location to location."""

    # source directory or file
    source: Path

    # destination directory or file
    destination: Path


@add_parameters(RsyncParams)
@no_submit_fn
def rsync(params: RsyncParams) -> bool:
    """Use rsync to copy from source to destination."""
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
        )
        logger.debug("Rsync copying: %s", result.stdout.decode())
    except subprocess.CalledProcessError as exc:
        logger.exception(
            "Failed to rsync %s",
            params.source,
            exc_info=exc,
        )
        return False
    else:
        return True


class CopyParams(BaseModel):
    """Copy parameters to copy from location to location."""

    # source directory or file
    source: Path

    # destination directory or file
    destination: Path

    # if true, will overwrite the destination
    overwrite: bool = True


@add_parameters(CopyParams)
@no_submit_fn
def copy(params: CopyParams) -> bool:
    """Use python shutil to copy directories and files."""
    logger = logging.getLogger(__name__)

    if not params.source.exists():
        logger.error(
            "Cannot copy - it doesn't exist! %s",
            params.source,
        )
        return False
    if params.destination.exists():
        logger.warning("Destination file already exists!")
        if params.overwrite:
            if params.destination.is_file():
                params.destination.unlink()
            else:
                shutil.rmtree(params.destination)
        else:
            logger.error("File exists and not overwriting - cannot copy ")
            return False
    try:
        if params.source.is_file():
            shutil.copy2(params.source, params.destination)
        else:
            shutil.copytree(params.source, params.destination)
    except OSError as exc:
        logger.exception("Cannot copy file: %s", params.source, exc_info=exc)
        return False
    else:
        return True


class MoveParams(BaseModel):
    """Parameters to move a file or directory."""

    # source directory or file
    source: Path

    # destination directory or file
    destination: Path

    # if true, will overwrite the destination
    overwrite: bool = True


@add_parameters(MoveParams)
@no_submit_fn
def move(params: MoveParams) -> bool:
    """Move from a source to a destination."""
    logger = logging.getLogger(__name__)

    if not params.source.exists():
        logger.error(
            "Cannot move - it doesn't exist! %s",
            params.source,
        )
        return False
    if params.destination.exists():
        logger.warning("Destination file already exists!")
        if params.overwrite:
            if params.destination.is_file():
                params.destination.unlink()
            else:
                shutil.rmtree(params.destination)
        else:
            logger.error("File exists and not overwriting - cannot copy ")
            return False

    try:
        shutil.move(params.source, params.destination)
    except OSError as exc:
        logger.exception(
            "Cannot move file! %s",
            params.source,
            exc_info=exc,
        )
        return False
    else:
        return True
