"""Test failing the jobs of a worker."""

from typing import TYPE_CHECKING

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def _job(job_id: str, deps: set[str] | None = None) -> JobWithContext:
    return JobWithContext.model_validate(
        {
            "job_id": job_id,
            "function": "pyantz.jobs.testing.nop.do_nothing",
            "parameters": {},
            "depends_on": deps,
        },
    )


def test_only_running_jobs_of_that_worker_fail(tmp_path: Path) -> None:
    """Jobs of other workers, and finished jobs, are left alone."""
    queue = SqliteQueue(tmp_path / "queue.db")
    for name in ("mine", "theirs", "done"):
        queue.add_job(_job(name), None)
        queue.get_job()
        queue.update_job_status(name, JobStatus.RUNNING)
    queue.set_job_worker("mine", 111)
    queue.set_job_worker("theirs", 222)
    queue.set_job_worker("done", 111)
    queue.update_job_status("done", JobStatus.SUCCESS)

    assert queue.fail_jobs_of_worker(111) == ["mine"]

    report = queue.get_jobs_report()
    assert (report.error, report.running, report.success) == (1, 1, 1)


def test_dependents_fail_with_the_worker_job(tmp_path: Path) -> None:
    """The failure propagates to waiting jobs."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_job("a"), None)
    queue.add_job(_job("b", {"a"}), None)
    queue.get_job()
    queue.update_job_status("a", JobStatus.RUNNING)
    queue.set_job_worker("a", 5)

    queue.fail_jobs_of_worker(5)

    report = queue.get_jobs_report()
    assert (report.error, report.pending, report.running) == (2, 0, 0)


def test_unknown_worker_fails_nothing(tmp_path: Path) -> None:
    """A worker without jobs changes nothing."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_job("a"), None)

    assert queue.fail_jobs_of_worker(999) == []
    assert queue.get_jobs_report().ready == 1
