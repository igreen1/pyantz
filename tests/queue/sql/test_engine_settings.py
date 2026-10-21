"""Test the sqlite settings which make multi-process access safe."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import sqlalchemy as sa

from pyantz import start
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def _pragma(queue: SqliteQueue, name: str) -> object:
    with queue._engine.connect() as conn:  # noqa: SLF001
        return conn.execute(sa.text(f"PRAGMA {name}")).scalar()


def test_connections_use_wal_and_busy_timeout(tmp_path: Path) -> None:
    """Every connection uses write-ahead logging and waits for locks."""
    queue = SqliteQueue(tmp_path / "queue.db")

    assert _pragma(queue, "journal_mode") == "wal"
    assert _pragma(queue, "busy_timeout") == 30_000  # noqa: PLR2004
    assert _pragma(queue, "synchronous") == 1  # NORMAL


def test_many_worker_processes_share_queue(tmp_path: Path) -> None:
    """Several worker processes finish a batch of jobs without lock errors."""
    work = tmp_path / "work"
    work.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    num_jobs = 40
    jobs = [
        {
            "job_id": f"job_{i}",
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            "parameters": {"path": os.fspath(out / f"{i}.txt")},
            # a mix of independent jobs and short chains
            "depends_on": [f"job_{i - 1}"] if i % 4 else None,
        }
        for i in range(num_jobs)
    ]

    start(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "local_proc",
                "working_directory": os.fspath(work),
                "number_processes": 4,
                "poll_timeout": 0.01,
            },
        },
    )

    assert len(list(out.glob("*.txt"))) == num_jobs
