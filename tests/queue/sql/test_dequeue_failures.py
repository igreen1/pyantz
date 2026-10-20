"""Test that dequeued jobs are never lost."""

# regression tests for issue #19

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Session

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.distributed_queue.sql.orm import JobConfigTable
from pyantz.infrastructure.runner.local.local_runner import _worker

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _nop(job_id: str) -> JobWithContext:
    return JobWithContext.model_validate(
        {"job_id": job_id, "function": NOP, "parameters": {}},
    )


def _break_config(queue: SqliteQueue, job_id: str) -> None:
    """Make the stored config of a job reference a function that can't be imported."""
    broken = _nop(job_id).model_dump_json().replace(NOP, "no_such_module.some_fn")
    with Session(queue._engine) as sesh:  # noqa: SLF001
        sesh.execute(
            sa.update(JobConfigTable)
            .where(JobConfigTable.job_id == job_id)
            .values(job_config_content=broken),
        )
        sesh.commit()


def test_dequeued_job_is_running_immediately(tmp_path: Path) -> None:
    """A job handed to a worker is RUNNING, not READY, from the moment it leaves."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_nop("a"), None)

    assert queue.get_job().payload.type_ == "job"

    report = queue.get_jobs_report()
    assert report.running == 1
    assert report.ready == 0


def test_unloadable_job_is_failed_and_others_still_run(tmp_path: Path) -> None:
    """A job whose config can't be loaded is ERROR; the worker survives."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_nop("bad"), None)
    queue.add_job(_nop("good"), None)
    _break_config(queue, "bad")

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    report = queue.get_jobs_report()
    assert report.error == 1
    assert report.success == 1
    assert report.ready == report.running == report.pending == 0


def test_dependents_of_unloadable_job_are_failed(tmp_path: Path) -> None:
    """Dependents of the broken job error instead of hanging the pipeline."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_nop("bad"), None)
    dependent = JobWithContext.model_validate(
        {"job_id": "dep", "function": NOP, "parameters": {}, "depends_on": ["bad"]},
    )
    queue.add_job(dependent, None)
    _break_config(queue, "bad")

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=5)

    assert queue.get_jobs_report().error == 2  # noqa: PLR2004
