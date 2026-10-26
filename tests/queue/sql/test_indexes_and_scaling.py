"""Test the queue has the indexes needed to stay fast with many jobs."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import sqlalchemy as sa

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.distributed_queue.common.return_types import (
    JobReturn,
    JobStatus,
)
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

# generous bound: a 1000 job chain takes about 3 seconds on a laptop
CHAIN_LENGTH = 1000
MAX_SECONDS = 60


def _indexed_columns(queue: SqliteQueue, table: str) -> set[str]:
    columns: set[str] = set()
    with queue._engine.connect() as conn:  # noqa: SLF001
        for index in conn.execute(sa.text(f"PRAGMA index_list({table})")):
            name = index[1]
            info = conn.execute(sa.text(f"PRAGMA index_info({name})"))
            columns.update(row[2] for row in info)
    return columns


def test_lookup_columns_are_indexed(tmp_path: Path) -> None:
    """The columns used to find ready jobs and dependents have indexes."""
    queue = SqliteQueue(tmp_path / "queue.db")

    assert "job_status" in _indexed_columns(queue, "job_status")
    assert "depends_on" in _indexed_columns(queue, "dependencies")
    assert "job_id" in _indexed_columns(queue, "job_queue")


def test_long_dependency_chain_runs_in_reasonable_time(tmp_path: Path) -> None:
    """A chain of 1000 jobs is enqueued and executed in order, quickly."""
    queue = SqliteQueue(tmp_path / "queue.db")
    start = time.monotonic()
    for i in range(CHAIN_LENGTH):
        queue.add_job(
            JobWithContext.model_validate(
                {
                    "job_id": f"job_{i}",
                    "function": "pyantz.jobs.testing.nop.do_nothing",
                    "parameters": {},
                    "depends_on": [f"job_{i - 1}"] if i else None,
                },
            ),
            None,
        )
    for i in range(CHAIN_LENGTH):
        payload = queue.get_job().payload
        assert isinstance(payload, JobReturn)
        assert payload.job.job_id == f"job_{i}"
        queue.update_job_status(payload.job.job_id, JobStatus.SUCCESS)

    assert queue.get_jobs_report().success == CHAIN_LENGTH
    assert time.monotonic() - start < MAX_SECONDS
