"""Tests deleting things with delete.py."""

import logging
import os

from pyantz.infrastructure.config.base import JobConfig, Status
from pyantz.infrastructure.core.job import run_job
from pyantz.jobs.file.delete import delete

logger = logging.getLogger("test")
logger.setLevel(0)


def test_delete_directory(tmpdir: str | os.PathLike[str]) -> None:
    """Test deleting a newly made directory."""
    dir_name: str = "some_directory is cool"
    dir_path = os.path.join(tmpdir, dir_name)

    os.mkdir(dir_path)

    assert os.path.exists(dir_path)

    assert delete({"path": dir_path}, logger) == Status.SUCCESS

    assert not os.path.exists(dir_path)


def test_delete_file(tmpdir: str | os.PathLike[str]) -> None:
    """Test deleting a file."""
    file_name: str = "some_directory is cool"
    file_path = os.path.join(tmpdir, file_name)

    with open(file_path, "w") as fh:
        fh.write("HELLO\nTHERE TEST\t")

    assert os.path.exists(file_path)

    assert delete({"path": file_path}, logger) == Status.SUCCESS


def test_delete_file_in_job(tmpdir: str | os.PathLike[str]) -> None:
    """First level integration with the job."""
    file_name: str = "some_directory is cool"
    file_path = os.path.join(tmpdir, file_name)

    with open(file_path, "w") as fh:
        fh.write("HELLO\nTHERE TEST\t")

    assert os.path.exists(file_path)

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.delete.delete",
            "parameters": {"path": "%{tmpdir}" + os.sep + "%{file_name}"},
        }
    )

    assert (
        run_job(
            config=job_config,
            variables={"file_name": file_name, "tmpdir": os.fspath(tmpdir)},
            logger=logger,
        )
        == Status.SUCCESS
    )


def test_delete_file_in_job_non_existing(tmpdir: str | os.PathLike[str]) -> None:
    """First level integration with the job."""
    file_name: str = "some_directory is cool"

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.delete.delete",
            "parameters": {"path": "%{tmpdir}" + os.sep + "%{file_name}"},
        }
    )

    assert (
        run_job(
            config=job_config,
            variables={"file_name": file_name, "tmpdir": os.fspath(tmpdir)},
            logger=logger,
        )
        == Status.ERROR
    )


def test_delete_dir_in_job(tmpdir: str | os.PathLike[str]) -> None:
    """First level integration with the job."""
    dir_name: str = "some_directory is cool"
    dir_path = os.path.join(tmpdir, dir_name)

    os.mkdir(dir_path)

    assert os.path.exists(dir_path)

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.delete.delete",
            "parameters": {"path": "%{tmpdir}" + os.sep + "%{dir_name}"},
        }
    )

    assert (
        run_job(
            config=job_config,
            variables={"dir_name": dir_name, "tmpdir": os.fspath(tmpdir)},
            logger=logger,
        )
        == Status.SUCCESS
    )


def test_delete_dir_in_job_non_existing(tmpdir: str | os.PathLike[str]) -> None:
    """First level integration with the job."""
    file_name: str = "some_directory is cool"

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.delete.delete",
            "parameters": {"path": "%{tmpdir}" + os.sep + "%{file_name}"},
        }
    )

    assert (
        run_job(
            config=job_config,
            variables={"file_name": file_name, "tmpdir": os.fspath(tmpdir)},
            logger=logger,
        )
        == Status.ERROR
    )
