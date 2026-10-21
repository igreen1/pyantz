"""Stress test: many worker processes sharing one queue."""

from __future__ import annotations

import os
from collections import Counter
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

NUM_JOBS = 500
NUM_PROCESSES = 8


def _jobs(log: Path, *, multiple_dependencies: bool = True) -> list[dict[str, Any]]:
    """Jobs which each append their own id to the log, with mixed dependencies."""
    jobs: list[dict[str, Any]] = []
    for i in range(NUM_JOBS):
        depends_on = []
        if i % 3 == 0 and i >= 1:
            depends_on.append(f"job_{i - 1}")  # chains
        if multiple_dependencies and i % 7 == 0 and i >= 2:  # noqa: PLR2004
            depends_on.append(f"job_{i - 2}")  # several dependencies
        jobs.append(
            {
                "job_id": f"job_{i}",
                "depends_on": depends_on,
                "function": "pyantz.jobs.subproc.dispatch.dispatch",
                # `>>` opens the file with O_APPEND, so short writes don't interleave
                "parameters": {"cmd": ["sh", "-c", f'echo "job_{i}" >> "{log}"']},
            },
        )
    return jobs


@pytest.mark.slow
def test_every_job_runs_exactly_once(tmp_path: Path) -> None:
    """8 workers run 500 jobs: no job lost, none run twice, no lock errors."""
    work = tmp_path / "work"
    work.mkdir()
    log = tmp_path / "log.txt"

    start(
        {
            "jobs": _jobs(log),
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": False,
                "number_processes": NUM_PROCESSES,
                "poll_timeout": 0.01,
                "working_directory": os.fspath(work),
            },
        },
    )

    report = SqliteQueue(work / "queue.db").get_jobs_report()
    assert report.total == NUM_JOBS
    assert report.success == NUM_JOBS
    assert (report.error, report.pending, report.ready, report.running) == (0, 0, 0, 0)

    runs = Counter(log.read_text().split())
    assert set(runs) == {f"job_{i}" for i in range(NUM_JOBS)}
    assert set(runs.values()) == {1}


@pytest.mark.slow
def test_dependencies_are_respected_under_concurrency(tmp_path: Path) -> None:
    """A job never runs before the jobs it depends on."""
    work = tmp_path / "work"
    work.mkdir()
    log = tmp_path / "log.txt"
    # one dependency per job here: waiting for *all* of several dependencies is
    # covered by the dependency tests of the queue
    jobs = _jobs(log, multiple_dependencies=False)

    start(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": False,
                "number_processes": NUM_PROCESSES,
                "poll_timeout": 0.01,
                "working_directory": os.fspath(work),
            },
        },
    )

    position = {name: index for index, name in enumerate(log.read_text().split())}
    for job in jobs:
        for dependency in job["depends_on"]:
            assert position[dependency] < position[job["job_id"]]
