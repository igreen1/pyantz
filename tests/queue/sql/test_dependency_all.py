"""Regression tests: a job is READY only when ALL of its dependencies succeed."""

from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.config.job import JobWithContext
from pyantz.infrastructure.distributed_queue.common.return_types import (
    JobReturn,
    JobStatus,
)
from pyantz.infrastructure.distributed_queue.sql.sql_queue import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


@pytest.fixture
def queue(tmp_path: Path) -> SqliteQueue:
    """Create an empty queue."""
    return SqliteQueue(database_file=tmp_path / "queue.db")


def _job(job_id: str, deps: set[str] | None = None) -> JobWithContext:
    return JobWithContext(
        job_id=job_id,
        function=NOP,  # ty: ignore[invalid-argument-type]
        parameters={},
        depends_on=deps,
    )


def _next_job_id(queue: SqliteQueue) -> str:
    payload = queue.get_job().payload
    assert isinstance(payload, JobReturn)
    return str(payload.job.job_id)


def test_job_waits_for_all_dependencies(queue: SqliteQueue) -> None:
    """C depends on A and B: it stays PENDING until both are SUCCESS."""
    queue.add_job(_job("A"), None)
    queue.add_job(_job("B"), None)
    queue.add_job(_job("C", {"A", "B"}), None)

    first = _next_job_id(queue)
    queue.update_job_status(first, JobStatus.RUNNING)
    queue.update_job_status(first, JobStatus.SUCCESS)

    report = queue.get_jobs_report()
    assert report.ready == 1  # only the other root job
    assert report.pending == 1  # C is still waiting

    second = _next_job_id(queue)
    assert {first, second} == {"A", "B"}
    queue.update_job_status(second, JobStatus.RUNNING)
    queue.update_job_status(second, JobStatus.SUCCESS)

    assert queue.get_jobs_report().ready == 1
    assert _next_job_id(queue) == "C"


def test_parent_children_block_dependents(queue: SqliteQueue) -> None:
    """Dependents of a parent also wait for the children the parent submits."""
    queue.add_job(_job("P"), None)
    queue.add_job(_job("D", {"P"}), None)

    assert _next_job_id(queue) == "P"
    queue.update_job_status("P", JobStatus.RUNNING)
    queue.add_job(_job("child"), "P")
    queue.update_job_status("P", JobStatus.SUCCESS)

    # D must not run before the child finishes
    assert _next_job_id(queue) == "child"
    assert queue.get_jobs_report().pending == 1
    queue.update_job_status("child", JobStatus.RUNNING)
    assert queue.get_jobs_report().ready == 0

    queue.update_job_status("child", JobStatus.SUCCESS)
    assert _next_job_id(queue) == "D"
