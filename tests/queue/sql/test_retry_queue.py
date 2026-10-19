"""Test putting a job back in the queue with a changed config."""

from typing import TYPE_CHECKING

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.common.return_types import (
    JobReturn,
    JobStatus,
)
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def _job(attempts: int = 0) -> JobWithContext:
    return JobWithContext.model_validate(
        {
            "job_id": "a",
            "function": "pyantz.jobs.testing.nop.do_nothing",
            "parameters": {},
            "num_attempted_runs": attempts,
            "max_retries": 3,
        },
    )


def test_changed_job_is_returned_again(tmp_path: Path) -> None:
    """After change_config_in_place and PENDING the worker gets the new config."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_job(), None)
    first = queue.get_job().payload
    assert isinstance(first, JobReturn)
    queue.update_job_status("a", JobStatus.RUNNING)

    queue.change_config_in_place(_job(attempts=1))
    queue.update_job_status("a", JobStatus.PENDING)

    again = queue.get_job().payload
    assert isinstance(again, JobReturn)
    assert again.job.num_attempted_runs == 1
    assert again.job.max_retries == 3  # noqa: PLR2004


def test_changing_a_queued_job_does_not_duplicate_it(tmp_path: Path) -> None:
    """A job still in the queue is changed, not added twice."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_job(), None)

    queue.change_config_in_place(_job(attempts=2))

    first = queue.get_job().payload
    assert isinstance(first, JobReturn)
    assert first.job.num_attempted_runs == 2  # noqa: PLR2004
    assert queue.get_job().payload.type_ == "pending"
