"""Test the pipeline recovers when a worker process is killed mid-job."""

from __future__ import annotations

import os
import signal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from pyantz import start
from pyantz.infrastructure.config import SubmissionFnType, add_parameters
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _run(tmp_path: Path, jobs: list[dict[str, Any]], processes: int = 2) -> SqliteQueue:
    work = tmp_path / "work"
    work.mkdir()
    start(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": False,
                "number_processes": processes,
                "poll_timeout": 0.05,
                "timeout": 20,
                "working_directory": os.fspath(work),
            },
        },
    )
    return SqliteQueue(work / "queue.db")


class _NoParams(BaseModel):
    """Parameters of the killer job."""


@add_parameters(_NoParams)
def kill_own_worker(_params: _NoParams, _submit: SubmissionFnType) -> bool:
    """Kill the worker process running this job, which can't clean up after it.

    SIGKILL can't be handled; Windows has no SIGKILL, but os.kill terminates the
    process there.
    """
    os.kill(os.getpid(), getattr(signal, "SIGKILL", signal.SIGTERM))
    return True


def _killer(**extra: Any) -> dict[str, Any]:  # noqa: ANN401
    """Job which kills the worker running it."""
    return {"function": f"{__name__}.kill_own_worker", "parameters": {}, **extra}


def test_killed_workers_job_is_failed_and_the_pipeline_finishes(
    tmp_path: Path,
) -> None:
    """The job of a worker that dies is ERROR, other jobs still complete."""
    other = tmp_path / "other"
    jobs = [
        _killer(job_id="victim"),
        {
            "job_id": "other",
            "function": TOUCH,
            "parameters": {"path": os.fspath(other)},
        },
    ]

    queue = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert report.running == 0
    assert report.error == 1
    assert report.success == 1
    assert other.exists()


def test_dependents_of_the_lost_job_fail(tmp_path: Path) -> None:
    """Jobs waiting for the lost job are failed rather than waiting forever."""
    after = tmp_path / "after"
    jobs = [
        _killer(job_id="victim"),
        {
            "job_id": "after",
            "depends_on": ["victim"],
            "function": TOUCH,
            "parameters": {"path": os.fspath(after)},
        },
    ]

    queue = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert (report.error, report.pending, report.running) == (2, 0, 0)
    assert not after.exists()


def test_normal_runs_are_unaffected(tmp_path: Path) -> None:
    """Without deaths nothing is failed."""
    jobs = [
        {
            "job_id": f"j{i}",
            "function": TOUCH,
            "parameters": {"path": os.fspath(tmp_path / f"f{i}")},
        }
        for i in range(4)
    ]

    queue = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert (report.success, report.error) == (4, 0)
