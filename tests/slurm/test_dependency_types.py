"""Test the kinds of dependency between slurm jobs."""

import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import InitialConfig, JobConfig
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


def _start(tmp_path: Path, jobs: list[dict[str, Any]]) -> None:
    config = InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}, **job} for job in jobs],
            "submitter": {"type_": "slurm_sbatch", "working_dir": os.fspath(tmp_path)},
        },
    )
    start(config)


def _dependency(cmd: list[str]) -> str | None:
    found = [arg for arg in cmd if arg.startswith("--dependency=")]
    return found[0] if found else None


@pytest.mark.parametrize("kind", ["afterok", "afterany", "afternotok"])
def test_job_uses_its_dependency_type(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
    kind: str,
) -> None:
    """The type of the job appears in its --dependency argument."""
    _start(
        tmp_path,
        [
            {"job_id": "a"},
            {"job_id": "b", "depends_on": ["a"], "dependency_type": kind},
        ],
    )

    first, second = sbatch_calls
    assert _dependency(first) is None
    assert _dependency(second) == f"--dependency={kind}:1001"


def test_default_is_afterok(tmp_path: Path, sbatch_calls: list[list[str]]) -> None:
    """Jobs which don't choose keep waiting for success."""
    _start(tmp_path, [{"job_id": "a"}, {"job_id": "b", "depends_on": ["a"]}])

    assert _dependency(sbatch_calls[1]) == "--dependency=afterok:1001"


def test_types_apply_per_job(tmp_path: Path, sbatch_calls: list[list[str]]) -> None:
    """A cleanup job after two others uses afterany while the others use afterok."""
    _start(
        tmp_path,
        [
            {"job_id": "a"},
            {"job_id": "b", "depends_on": ["a"]},
            {
                "job_id": "cleanup",
                "depends_on": ["a", "b"],
                "dependency_type": "afterany",
            },
        ],
    )

    dependencies = [_dependency(cmd) for cmd in sbatch_calls]
    assert dependencies[0] is None
    assert dependencies[1] == "--dependency=afterok:1001"
    cleanup = dependencies[2]
    assert cleanup is not None
    assert cleanup.startswith("--dependency=afterany:")
    assert "afterok" not in cleanup


def test_unknown_type_is_rejected() -> None:
    """Only the three slurm kinds are accepted."""
    with pytest.raises(ValidationError):
        JobConfig.model_validate(
            {"function": NOP, "parameters": {}, "dependency_type": "afterburner"},
        )
