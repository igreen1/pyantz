"""Test the copy job"""

import glob
import logging
import os
import random
import string

from pyantz.infrastructure.core.status import Status
from pyantz.jobs.file.copy import copy

FILE_LENGTH_MAX: int = 8000

logger = logging.Logger("test")
logger.setLevel(0)


def test_copy_file(tmpdir: str | os.PathLike[str]) -> None:
    dir_path = os.fspath(tmpdir)
    src_dir = os.path.join(dir_path, "a")
    dst_dir = os.path.join(dir_path, "b")

    os.mkdir(src_dir)

    src_file = os.path.join(src_dir, "asdf")
    dst_file = os.path.join(dst_dir, "hjk")

    src_length: int = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )

    copy_params = {"source": src_file, "destination": dst_file}

    assert copy(copy_params, logger) == Status.SUCCESS

    assert os.path.exists(dst_file)

    with open(dst_file, "r") as fh:
        dst_contents = fh.read()
    with open(src_file, "r") as fh:
        src_contents = fh.read()

    assert src_contents == dst_contents


def test_copy_dir(tmpdir: str | os.PathLike[str]) -> None:
    dir_path = os.fspath(tmpdir)
    src_dir = os.path.join(dir_path, "a")
    dst_dir = os.path.join(dir_path, "b")

    os.mkdir(src_dir)

    src_file = os.path.join(src_dir, "asdf")
    src_length: int = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )
    src_file = os.path.join(src_dir, "qwerty")
    src_length = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )

    copy_params = {"source": src_dir, "destination": dst_dir}
    assert copy(copy_params, logger) == Status.SUCCESS

    os.path.exists(dst_dir)
    for file in glob.glob(os.path.join(dst_dir, "*")):
        bname = os.path.basename(file)
        with open(os.path.join(src_dir, bname)) as fh:
            src_content = fh.read()
        with open(os.path.join(dst_dir, bname)) as fh:
            dst_content = fh.read()
        assert src_content == dst_content


def test_copy_dir_to_existing_file(tmpdir: str | os.PathLike[str]) -> None:
    dir_path = os.fspath(tmpdir)
    src_dir = os.path.join(dir_path, "a")
    dst_dir = os.path.join(dir_path, "b")

    os.mkdir(src_dir)

    src_file = os.path.join(src_dir, "asdf")
    src_length: int = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )
    src_file = os.path.join(src_dir, "qwerty")
    src_length = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )

    with open(dst_dir, "w") as fh:
        fh.write("")

    copy_params = {"source": src_dir, "destination": dst_dir}
    assert copy(copy_params, logger) == Status.ERROR


def test_copy_file_to_existing_dir(tmpdir: str | os.PathLike[str]) -> None:
    dir_path = os.fspath(tmpdir)
    src_dir = os.path.join(dir_path, "a")
    dst_dir = os.path.join(dir_path, "b")

    os.mkdir(src_dir)
    os.mkdir(dst_dir)

    src_file = os.path.join(src_dir, "asdf")
    dst_file = os.path.join(dst_dir, "hjk")

    src_length: int = random.randint(0, FILE_LENGTH_MAX)
    with open(src_file, "w") as fh:
        fh.write(
            "".join(
                random.choice(string.ascii_uppercase + string.digits)
                for _ in range(src_length)
            )
        )

    copy_params = {"source": src_file, "destination": dst_dir}

    assert copy(copy_params, logger) == Status.ERROR

    assert os.path.exists(dst_dir)
    assert not os.path.exists(dst_file)
