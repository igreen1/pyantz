"""Test that sbatch-ed child jobs can start on a node."""

import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import start

FAKE_SBATCH = """#!/bin/bash
echo "$@" >> "$FAKE_SBATCH_LOG"
echo "1000"
"""

# a squeue with no pending jobs
FAKE_SQUEUE = """#!/bin/bash
echo "JOBID DEPENDENCY"
"""


def _install(bin_dir: Path, name: str, content: str) -> None:
    exe = bin_dir / name
    exe.write_text(content)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def slurm_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake slurm binaries on PATH; returns the sbatch log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install(bin_dir, "sbatch", FAKE_SBATCH)
    _install(bin_dir, "squeue", FAKE_SQUEUE)
    log = tmp_path / "sbatch.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_SBATCH_LOG", os.fspath(log))
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    return log


def _submit_one_job(tmp_path: Path) -> list[str]:
    """Run the submitter and return the argv given to the fake sbatch."""
    work = tmp_path / "work"
    work.mkdir()
    config = InitialConfig[SlurmRunnerConfig].model_validate(
        {
            "jobs": [
                {
                    "job_id": "a",
                    "function": "pyantz.jobs.testing.nop.do_nothing",
                    "parameters": {},
                },
            ],
            "submitter": {"type_": "slurm_sbatch", "working_dir": os.fspath(work)},
        },
    )
    start(config)
    return shlex.split(Path(os.environ["FAKE_SBATCH_LOG"]).read_text())


@pytest.mark.usefixtures("slurm_env")
def test_sbatch_command_passes_slurm_config(tmp_path: Path) -> None:
    """The sbatch command includes -i pointing at the saved slurm config."""
    argv = _submit_one_job(tmp_path)

    assert "-i" in argv
    assert "-c" in argv
    slurm_config = argv[argv.index("-i") + 1]
    assert SlurmRunnerConfig.model_validate_json(Path(slurm_config).read_text())


@pytest.mark.usefixtures("slurm_env")
def test_child_job_runs_from_sbatch_command(tmp_path: Path) -> None:
    """Executing the sbatch-ed command line on a 'node' runs the job."""
    argv = _submit_one_job(tmp_path)
    script_idx = next(i for i, a in enumerate(argv) if a.endswith("slurm_runner.py"))
    child_args = argv[script_idx:]

    # the node does not inherit the submitter's environment variable
    env = {k: v for k, v in os.environ.items() if k != "PYANTZ_SLURM_CONFIG_DIR"}
    env["SLURM_JOB_ID"] = "1000"
    result = subprocess.run(
        [sys.executable, *child_args],
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
