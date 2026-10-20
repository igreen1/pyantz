"""Test dependents of failed slurm jobs are cancelled rather than left pending."""

import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner.slurm import start

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"
FLAG = "--kill-on-invalid-dep=yes"


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


def _start(tmp_path: Path, slurm_args: list[str]) -> None:
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"job_id": "a", "function": NOP, "parameters": {}},
                {"job_id": "b", "function": NOP, "parameters": {}, "depends_on": ["a"]},
            ],
            "submitter": {
                "type_": "slurm_sbatch",
                "working_dir": os.fspath(tmp_path),
                "slurm_args": slurm_args,
            },
        },
    )
    start(config)


def test_flag_added_by_default(tmp_path: Path, sbatch_calls: list[list[str]]) -> None:
    """Every sbatch command gets --kill-on-invalid-dep=yes."""
    _start(tmp_path, ["--mem=1G"])

    assert len(sbatch_calls) == 2  # noqa: PLR2004
    for cmd in sbatch_calls:
        assert cmd.count(FLAG) == 1
        assert "--mem=1G" in cmd


def test_user_choice_is_respected(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """If the user sets the option themselves, it is not overridden or repeated."""
    _start(tmp_path, ["--kill-on-invalid-dep=no"])

    for cmd in sbatch_calls:
        assert "--kill-on-invalid-dep=no" in cmd
        assert not [arg for arg in cmd if arg == FLAG]
        assert len([arg for arg in cmd if arg.startswith("--kill-on-invalid-dep")]) == 1
