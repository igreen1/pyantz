"""Test merging dependencies into the sbatch arguments."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner.slurm import start
from pyantz.infrastructure.runner.slurm.slurm_runner import _add_dependency_to_sbatch

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"
OTHER = ["--partition", "gpu", "--mem", "4G"]
EXPECTED = "--dependency=afterok:1,afterok:2"


@pytest.mark.parametrize(
    ("user_args", "expected_rest"),
    [
        (["--dependency=afterok:1"], []),
        (["--dependency", "afterok:1"], []),
        (["-d", "afterok:1"], []),
        (["-dafterok:1"], []),
        ([*OTHER, "--dependency=afterok:1"], OTHER),
        (["--dependency", "afterok:1", *OTHER], OTHER),
        (["--partition", "gpu", "-d", "afterok:1", "--mem", "4G"], OTHER),
    ],
)
def test_user_dependency_forms_are_merged(
    user_args: list[str],
    expected_rest: list[str],
) -> None:
    """Every spelling gives one merged argument and keeps the others in order."""
    result = _add_dependency_to_sbatch(user_args, ["2"])

    assert result == [*expected_rest, EXPECTED]


def test_no_user_dependency() -> None:
    """Without a user dependency, only the new ones are added."""
    assert _add_dependency_to_sbatch(OTHER, ["1", "2"]) == [
        *OTHER,
        "--dependency=afterok:1,afterok:2",
    ]


def test_similar_arguments_are_not_mistaken_for_dependency() -> None:
    """Only real dependency options are treated as the dependency."""
    args = ["--comment=--dependency", "--chdir", "/dd", "-D", "/work"]

    assert _add_dependency_to_sbatch(args, ["1"]) == [*args, "--dependency=afterok:1"]


def test_or_dependencies_are_rejected() -> None:
    """A '?' separated (OR) dependency can't be combined safely."""
    with pytest.raises(ValueError, match="uses '\\?' for OR"):
        _add_dependency_to_sbatch(["--dependency=afterok:1?afterok:2"], ["3"])


def test_dangling_option_is_rejected() -> None:
    """--dependency with no value is an error rather than corrupting the command."""
    with pytest.raises(ValueError, match="without a value"):
        _add_dependency_to_sbatch(["--mem", "1G", "--dependency"], ["3"])


def test_sbatch_command_for_job_with_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dependent job's sbatch gets the user's dependency plus its parent's."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, f"{500 + len(calls)}\n".encode())

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"job_id": "a", "function": NOP, "parameters": {}},
                {"job_id": "b", "function": NOP, "parameters": {}, "depends_on": ["a"]},
            ],
            "submitter": {
                "type_": "slurm_sbatch",
                "working_dir": os.fspath(tmp_path),
                "slurm_args": ["--dependency=afterok:9", "--mem=1G"],
            },
        },
    )

    start(config)

    first, second = calls
    assert "--dependency=afterok:9" in first
    assert "--dependency=afterok:9,afterok:501" in second
    assert "--mem=1G" in second
    assert "afterok:9afterok" not in " ".join(second)
