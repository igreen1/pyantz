"""Test the reason a job failed is stored with its status."""

from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

from pyantz.infrastructure.config import (
    JobWithContext,
    SubmissionFnType,
    add_parameters,
)
from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.runner.local.local_runner import _worker

if TYPE_CHECKING:
    from pathlib import Path


class _NoParams(BaseModel):
    """Parameters of the test jobs."""


@add_parameters(_NoParams)
def boom(_params: _NoParams, _submit: SubmissionFnType) -> bool:
    """Fail by raising."""
    msg = "boom"
    raise RuntimeError(msg)


@add_parameters(_NoParams)
def returns_false(_params: _NoParams, _submit: SubmissionFnType) -> bool:
    """Fail by returning False."""
    return False


def _job(job_id: str, function: str, deps: list[str] | None = None) -> JobWithContext:
    return JobWithContext.model_validate(
        {
            "job_id": job_id,
            "function": function,
            "parameters": {},
            "depends_on": deps,
        },
    )


@pytest.fixture
def queue(tmp_path: Path) -> SqliteQueue:
    """Create an empty queue."""
    return SqliteQueue(tmp_path / "queue.db")


def test_exception_message_is_stored(tmp_path: Path, queue: SqliteQueue) -> None:
    """A job raising RuntimeError('boom') ends as ERROR with the message."""
    queue.add_job(_job("bad", f"{__name__}.boom"), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    report = queue.get_job_status("bad")
    assert report.status == JobStatus.ERROR
    assert report.status_details is not None
    assert "RuntimeError" in report.status_details
    assert "boom" in report.status_details


def test_false_result_is_explained(tmp_path: Path, queue: SqliteQueue) -> None:
    """A job returning False also has a reason stored."""
    queue.add_job(_job("bad", f"{__name__}.returns_false"), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    report = queue.get_job_status("bad")
    assert report.status == JobStatus.ERROR
    assert report.status_details


def test_dependents_say_why_they_failed(tmp_path: Path, queue: SqliteQueue) -> None:
    """Jobs failed because a dependency failed say so."""
    queue.add_job(_job("bad", f"{__name__}.boom"), None)
    queue.add_job(_job("child", "pyantz.jobs.testing.nop.do_nothing", ["bad"]), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    child = queue.get_job_status("child")
    assert child.status == JobStatus.ERROR
    assert child.status_details is not None
    assert "depends on" in child.status_details


def test_successful_job_has_no_details(tmp_path: Path, queue: SqliteQueue) -> None:
    """Successful jobs have a status and no details."""
    queue.add_job(_job("ok", "pyantz.jobs.testing.nop.do_nothing"), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    report = queue.get_job_status("ok")
    assert report.status == JobStatus.SUCCESS
    assert report.status_details is None


def test_unknown_job_raises_key_error(queue: SqliteQueue) -> None:
    """Looking up a job which doesn't exist is a KeyError."""
    with pytest.raises(KeyError):
        queue.get_job_status("missing")


def test_details_are_set_explicitly(queue: SqliteQueue) -> None:
    """update_job_status stores details given by the caller."""
    queue.add_job(_job("x", "pyantz.jobs.testing.nop.do_nothing"), None)
    queue.update_job_status("x", JobStatus.ERROR, details="custom reason")

    assert queue.get_job_status("x").status_details == "custom reason"
