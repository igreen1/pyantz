"""Test running a pipeline repeatedly with the same working directory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def _config(work: Path, output: Path, **submitter: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "jobs": [
            {
                "job_id": "first",
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(output / "first.txt")},
            },
            {
                "job_id": "second",
                "depends_on": ["first"],
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(output / "second.txt")},
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
            **submitter,
        },
    }


def test_second_run_runs_jobs_again(tmp_path: Path) -> None:
    """Fixed job ids don't collide with the previous run's queue."""
    work = tmp_path / "work"
    work.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    config = _config(work, output)

    start(config)
    assert (output / "second.txt").exists()
    for path in output.iterdir():
        path.unlink()

    start(config)  # would raise IntegrityError on the stale queue
    assert (output / "first.txt").exists()
    assert (output / "second.txt").exists()


def test_unfinished_jobs_of_old_run_are_not_run(tmp_path: Path) -> None:
    """A job left READY in an old queue doesn't run in the new run."""
    work = tmp_path / "work"
    work.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    with SqliteQueue(work / "queue.db") as old_queue:
        old_queue.add_job(
            JobWithContext.model_validate(
                {
                    "job_id": "old_job",
                    "function": "pyantz.jobs.testing.touch_file.touch_file",
                    "parameters": {"path": os.fspath(output / "old.txt")},
                },
            ),
            None,
        )

    start(_config(work, output))

    assert not (output / "old.txt").exists()
    assert (output / "second.txt").exists()
