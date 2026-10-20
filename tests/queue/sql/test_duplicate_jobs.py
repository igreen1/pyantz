"""Test adding a job whose id is already in the queue."""

import os
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.runner.local.local_runner import _worker

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


@pytest.fixture
def queue(tmp_path: Path) -> SqliteQueue:
    """Create an empty queue."""
    return SqliteQueue(tmp_path / "queue.db")


def _nop(job_id: str) -> JobWithContext:
    return JobWithContext.model_validate(
        {"job_id": job_id, "function": NOP, "parameters": {}},
    )


def test_add_duplicate_returns_false(queue: SqliteQueue) -> None:
    """Adding the same job id twice returns False instead of raising."""
    assert queue.add_job(_nop("a"), None) is True
    assert queue.add_job(_nop("a"), None) is False


def test_add_duplicate_leaves_queue_unchanged(queue: SqliteQueue) -> None:
    """A rejected duplicate adds no rows: the queue still works normally."""
    queue.add_job(_nop("a"), None)
    queue.add_job(_nop("b"), None)
    queue.add_job(_nop("a"), None)

    report = queue.get_jobs_report()
    assert report.total == report.ready + report.pending == 2  # noqa: PLR2004
    first = queue.get_job().payload
    second = queue.get_job().payload
    assert {first.job.job_id, second.job.job_id} == {"a", "b"}  # ty: ignore[unresolved-attribute]
    assert queue.get_job().payload.type_ == "pending"


def test_worker_fails_job_that_submits_duplicate(
    tmp_path: Path,
    queue: SqliteQueue,
) -> None:
    """A job submitting an id already in the queue errors; other jobs still run."""
    touched = tmp_path / "touched.txt"
    parent = JobWithContext.model_validate(
        {
            "job_id": "parent",
            "function": "pyantz.jobs.branching.if_else.conditionally_execute",
            "parameters": {
                "left_side": 1,
                "right_side": 1,
                "comparator": "==",
                "if_true": {
                    "job_id": "other",
                    "function": "pyantz.jobs.testing.touch_file.touch_file",
                    "parameters": {"path": os.fspath(touched)},
                },
            },
        },
    )
    queue.add_job(parent, None)
    queue.add_job(_nop("other"), None)  # the parent's child id is taken

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    report = queue.get_jobs_report()
    assert report.error == 1
    assert report.success == 1
    assert not touched.exists()
