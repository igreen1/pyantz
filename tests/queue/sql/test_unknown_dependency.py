"""Test jobs whose dependencies can never be satisfied."""

# regression tests for issue #17

from __future__ import annotations
import os
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import InitialConfig, JobWithContext
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.runner.local.local_runner import _worker

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _nop(job_id: str, deps: set[str] | None = None) -> JobWithContext:
    return JobWithContext.model_validate(
        {"job_id": job_id, "function": NOP, "parameters": {}, "depends_on": deps},
    )


def test_config_rejects_unknown_dependency(tmp_path: Path) -> None:
    """A dependency on a job not in the config fails validation, naming it."""
    with pytest.raises(ValidationError, match="nope"):
        InitialConfig.model_validate(
            {
                "jobs": [
                    {
                        "job_id": "x",
                        "function": NOP,
                        "parameters": {},
                        "depends_on": ["nope"],
                    },
                ],
                "submitter": {
                    "type_": "local_proc",
                    "working_directory": os.fspath(tmp_path),
                },
            },
        )


def test_config_with_known_dependencies_is_valid(tmp_path: Path) -> None:
    """Dependencies between jobs of the config are accepted."""
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"job_id": "a", "function": NOP, "parameters": {}},
                {
                    "job_id": "b",
                    "function": NOP,
                    "parameters": {},
                    "depends_on": ["a"],
                },
            ],
            "submitter": {
                "type_": "local_proc",
                "working_directory": os.fspath(tmp_path),
            },
        },
    )
    assert len(config.jobs) == 2  # noqa: PLR2004


def test_worker_returns_when_deadlocked(tmp_path: Path) -> None:
    """A queue with only unsatisfiable jobs does not hang the worker."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_nop("stuck", {"nope"}), None)
    queue.add_job(_nop("dependent", {"stuck"}), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=None)

    report = queue.get_jobs_report()
    assert report.error == report.total == 2  # noqa: PLR2004
    assert report.pending == 0


def test_deadlock_does_not_block_other_jobs(tmp_path: Path) -> None:
    """Runnable jobs still run; only the stuck job is failed."""
    queue = SqliteQueue(tmp_path / "queue.db")
    queue.add_job(_nop("stuck", {"nope"}), None)
    queue.add_job(_nop("fine"), None)

    _worker(tmp_path / "queue.db", poll_time=0.01, timeout=None)

    report = queue.get_jobs_report()
    assert report.success == 1
    assert report.error == 1
