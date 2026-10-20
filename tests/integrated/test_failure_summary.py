"""Test the summary of failed jobs printed at the end of a local run."""

import logging
import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _config(tmp_path: Path) -> dict[str, Any]:
    work = tmp_path / "work"
    work.mkdir()
    existing = tmp_path / "exists.txt"
    existing.touch()
    return {
        "jobs": [
            {
                "job_id": "fine",
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
            },
            {
                "job_id": "broken",
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(existing), "exist_ok": False},
            },
        ],
        "submitter": {"type_": "local_proc", "working_directory": os.fspath(work)},
    }


def test_summary_lists_the_failed_job(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The final log names the failed job and why it failed, not the others."""
    with caplog.at_level(logging.ERROR):
        report = start(_config(tmp_path))

    assert report is not None
    assert report.error == 1
    summaries = [r.getMessage() for r in caplog.records if "failed:" in r.getMessage()]
    assert len(summaries) == 1
    assert "1 job(s) failed" in summaries[0]
    assert "broken" in summaries[0]
    assert "fine" not in summaries[0]


def test_failed_jobs_come_from_the_queue(tmp_path: Path) -> None:
    """The queue reports each failed job with its details."""
    start(_config(tmp_path))

    failed = SqliteQueue(tmp_path / "work" / "queue.db").get_failed_jobs()

    assert [job.job_id for job in failed] == ["broken"]
    assert failed[0].status == JobStatus.ERROR
    assert failed[0].status_details
