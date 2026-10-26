"""Test that child SLURM jobs exit non-zero when the job fails."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.runner.slurm import slurm_runner

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="the fake squeue is a bash script; slurm runs on Linux",
)

FAKE_SQUEUE = """#!/bin/bash
echo "JOBID DEPENDENCY"
"""


def _run_child(
    tmp_path: Path, job: dict[str, Any]
) -> subprocess.CompletedProcess[bytes]:
    """Run the slurm entry point as slurm would, for the given job."""
    work = tmp_path / "work"
    work.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    squeue = bin_dir / "squeue"
    squeue.write_text(FAKE_SQUEUE)
    squeue.chmod(squeue.stat().st_mode | stat.S_IEXEC)

    slurm_config = tmp_path / "slurm_config.json"
    slurm_config.write_text(
        json.dumps({"type_": "slurm_sbatch", "working_dir": os.fspath(work)}),
    )
    job_file = work / "job.json"
    job_file.write_text(json.dumps({"job_id": "j", "parameters": {}, **job}))

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "SLURM_JOB_ID": "1",
        "PYANTZ_SLURM_CONFIG_FILE": os.fspath(slurm_config),
    }
    return subprocess.run(
        [
            sys.executable,
            slurm_runner.__file__,
            "-i",
            os.fspath(slurm_config),
            "-c",
            os.fspath(job_file),
        ],
        capture_output=True,
        env=env,
        check=False,
    )


def test_successful_job_exits_zero(tmp_path: Path) -> None:
    """A job returning True gives exit code 0."""
    result = _run_child(
        tmp_path,
        {"function": "pyantz.jobs.testing.nop.do_nothing"},
    )
    assert result.returncode == 0, result.stderr.decode()


def test_job_returning_false_exits_nonzero(tmp_path: Path) -> None:
    """A job returning False (file exists, exist_ok False) gives a failing exit."""
    existing = tmp_path / "exists.txt"
    existing.touch()
    result = _run_child(
        tmp_path,
        {
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            "parameters": {"path": os.fspath(existing), "exist_ok": False},
        },
    )
    assert result.returncode != 0


def test_job_raising_exits_nonzero(tmp_path: Path) -> None:
    """A job raising an exception gives a failing exit."""
    missing_dir = tmp_path / "does" / "not" / "exist" / "file.txt"
    result = _run_child(
        tmp_path,
        {
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            "parameters": {"path": os.fspath(missing_dir)},
        },
    )
    assert result.returncode != 0
