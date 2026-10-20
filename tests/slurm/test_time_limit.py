"""Test the maximum job time is given to slurm."""

import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import start

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


@pytest.fixture
def sbatch_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock subprocess.run, recording sbatch commands and numbering the jobs."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, f"{1000 + len(calls)}\n".encode())

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    return calls


def _start(tmp_path: Path, **submitter: Any) -> None:  # noqa: ANN401
    config = InitialConfig[SlurmRunnerConfig].model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {
                "type_": "slurm_sbatch",
                "working_dir": os.fspath(tmp_path),
                **submitter,
            },
        },
    )
    start(config)


def _time_args(cmd: list[str]) -> list[str]:
    return [arg for arg in cmd if arg.startswith(("--time", "-t"))]


def test_default_limit_is_passed_in_minutes(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """The default 10000 seconds is 167 minutes (rounded up)."""
    _start(tmp_path)

    assert _time_args(sbatch_calls[0]) == ["--time=167"]


def test_configured_limit_is_used(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """A configured limit is converted, rounding up to whole minutes."""
    _start(tmp_path, max_job_time_seconds=3600)
    _start(tmp_path, max_job_time_seconds=61)

    assert _time_args(sbatch_calls[0]) == ["--time=60"]
    assert _time_args(sbatch_calls[1]) == ["--time=2"]


@pytest.mark.parametrize(
    "user_args",
    [["--time=00:10:00"], ["--time", "00:10:00"], ["-t", "10"], ["-t10"]],
)
def test_user_time_limit_wins(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
    user_args: list[str],
) -> None:
    """If the user sets a time limit in slurm_args, none is added."""
    _start(tmp_path, slurm_args=user_args)

    cmd = sbatch_calls[0]
    assert not [
        arg for arg in cmd if arg.startswith("--time=") and arg not in user_args
    ]
    for arg in user_args:
        assert arg in cmd
