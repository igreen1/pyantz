"""Test stopping a running pipeline with signals."""

import contextlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus

if TYPE_CHECKING:
    from pathlib import Path

WAIT_SECONDS = 30


def _start_sleeping_pipeline(
    tmp_path: Path,
    *,
    use_same_proc: bool,
) -> subprocess.Popen[bytes]:
    """Start `pyantz` on a pipeline with a job sleeping for a minute."""
    work = tmp_path / "work"
    work.mkdir()
    config = {
        "jobs": [
            {
                "job_id": "sleeper",
                "function": "pyantz.jobs.subproc.dispatch.dispatch",
                "parameters": {"cmd": ["sleep", "60"]},
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": os.fspath(work),
            "use_same_proc": use_same_proc,
            "number_processes": 2,
            "poll_timeout": 0.05,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    # own process group, so signals and leftovers are easy to find
    return subprocess.Popen(
        [sys.executable, "-m", "pyantz", os.fspath(config_file)],
        start_new_session=True,
    )


def _job_status(queue_file: Path) -> int | None:
    if not queue_file.exists():
        return None
    try:
        with sqlite3.connect(queue_file, timeout=5) as conn:
            row = conn.execute(
                "SELECT job_status FROM job_status WHERE job_id = 'sleeper'",
            ).fetchone()
    except sqlite3.Error:
        return None
    return None if row is None else row[0]


def _wait_until_running(queue_file: Path) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if _job_status(queue_file) == JobStatus.RUNNING:
            return
        time.sleep(0.1)
    pytest.fail("job never started running")


def _group_is_empty(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


@pytest.mark.parametrize("use_same_proc", [False, True])
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signal_stops_pipeline_and_cleans_up(
    tmp_path: Path,
    sig: signal.Signals,
    *,
    use_same_proc: bool,
) -> None:
    """The pipeline exits quickly, leaves no processes and no RUNNING job."""
    proc = _start_sleeping_pipeline(tmp_path, use_same_proc=use_same_proc)
    queue_file = tmp_path / "work" / "queue.db"
    try:
        _wait_until_running(queue_file)

        proc.send_signal(sig)
        proc.wait(timeout=WAIT_SECONDS)

        assert proc.returncode != 0
        deadline = time.monotonic() + WAIT_SECONDS
        while not _group_is_empty(proc.pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert _group_is_empty(proc.pid), "child processes were left running"
        assert _job_status(queue_file) == JobStatus.ERROR
    finally:
        if proc.poll() is None or not _group_is_empty(proc.pid):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
