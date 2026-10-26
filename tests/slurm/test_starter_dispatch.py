"""Test that the top-level starter routes SLURM configs to the SLURM runner."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

NUM_JOBS = 2

FAKE_SBATCH = """#!/bin/bash
echo "$@" >> "$FAKE_SBATCH_LOG"
n=$(wc -l < "$FAKE_SBATCH_LOG")
echo "$((1000 + n))"
"""


@pytest.fixture
def sbatch_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a fake ``sbatch`` on PATH which logs its arguments."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sbatch = bin_dir / "sbatch"
    sbatch.write_text(FAKE_SBATCH)
    sbatch.chmod(sbatch.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "sbatch.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_SBATCH_LOG", os.fspath(log))
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    return log


def _config(work_dir: Path) -> dict[str, Any]:
    work_dir.mkdir(exist_ok=True)
    return {
        "jobs": [
            {
                "job_id": "a",
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
            },
            {
                "job_id": "b",
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
                "depends_on": ["a"],
            },
        ],
        "submitter": {"type_": "slurm_sbatch", "working_dir": os.fspath(work_dir)},
    }


def test_start_dispatches_slurm_config(tmp_path: Path, sbatch_log: Path) -> None:
    """`start` with a slurm submitter calls sbatch once per job."""
    start(_config(tmp_path / "work"))

    lines = sbatch_log.read_text().splitlines()
    assert len(lines) == NUM_JOBS
    assert all("--parsable" in line for line in lines)


def test_start_slurm_chains_dependencies(tmp_path: Path, sbatch_log: Path) -> None:
    """Jobs are submitted in dependency order, with the child using afterok."""
    work = tmp_path / "work"
    start(_config(work))

    first, second = sbatch_log.read_text().splitlines()
    assert "--dependency" not in first
    assert "--dependency=afterok:1001" in second
