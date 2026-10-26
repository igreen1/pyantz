"""Test dependents of a slurm job wait on every child the job submits."""

from __future__ import annotations

import inspect
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import JobConfig
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import slurm_runner

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"
CURRENT_JOB = "100"
DEPENDENT = "200"


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock slurm: record commands, number the sbatch-ed jobs from 301."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        sbatch_count = len([c for c in calls if c[0] == "sbatch"])
        return subprocess.CompletedProcess(cmd, 0, f"{300 + sbatch_count}\n".encode())

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setenv("SLURM_JOB_ID", CURRENT_JOB)
    # job 200 waits on the current job (100) and an unrelated one (50)
    monkeypatch.setattr(
        slurm_runner,
        "_get_dependent_jobs",
        lambda **_kwargs: {DEPENDENT: ["50", CURRENT_JOB]},
    )
    return calls


def _make_submitter(tmp_path: Path, *, inherit_dependencies: bool = True) -> Any:  # noqa: ANN401
    config = SlurmRunnerConfig(
        working_dir=tmp_path,
        inherit_dependencies=inherit_dependencies,
    )
    extra_args: list[Any] = []
    if len(inspect.signature(slurm_runner._create_job_submitter).parameters) > 1:  # noqa: SLF001
        extra_args.append(tmp_path / "slurm_config.json")
    return slurm_runner._create_job_submitter(config, *extra_args)  # noqa: SLF001


def _child(index: int) -> JobConfig:
    return JobConfig.model_validate(
        {"job_id": f"child_{index}", "function": NOP, "parameters": {}},
    )


def _scontrol(commands: list[list[str]]) -> list[str]:
    return [" ".join(c) for c in commands if c[0] == "scontrol"]


def test_each_update_keeps_earlier_children(
    tmp_path: Path,
    commands: list[list[str]],
) -> None:
    """After three children, the last update lists all three and the originals."""
    submit = _make_submitter(tmp_path)

    for index in range(3):
        submit(_child(index))

    updates = _scontrol(commands)
    assert len(updates) == 3  # noqa: PLR2004
    assert updates[0].endswith(
        f"JobId={DEPENDENT} Dependency=afterok:50,afterok:{CURRENT_JOB},afterok:301",
    )
    assert updates[-1].endswith(
        f"JobId={DEPENDENT} "
        f"Dependency=afterok:50,afterok:{CURRENT_JOB},"
        "afterok:301,afterok:302,afterok:303",
    )


def test_no_updates_when_not_inheriting(
    tmp_path: Path,
    commands: list[list[str]],
) -> None:
    """With inherit_dependencies off, dependents are left alone."""
    submit = _make_submitter(tmp_path, inherit_dependencies=False)

    submit(_child(0))
    submit(_child(1))

    assert not _scontrol(commands)
