"""Test the arguments given to sbatch."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig
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


def _start(tmp_path: Path, slurm_args: list[str], jobs: int = 1) -> None:
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"job_id": f"job_{i}", "function": NOP, "parameters": {}}
                for i in range(jobs)
            ],
            "submitter": {
                "type_": "slurm_sbatch",
                "working_dir": os.fspath(tmp_path),
                "slurm_args": slurm_args,
            },
        },
    )
    start(config)


def _slurm_options(cmd: list[str]) -> list[str]:
    """Get the user's options between `sbatch` and the script being submitted.

    Options pyantz adds on its own (time limit, invalid dependency handling) are
    left out.
    """
    script = next(i for i, arg in enumerate(cmd) if arg.endswith("run.sh"))
    return [
        arg
        for arg in cmd[1:script]
        if not arg.startswith(("--time=", "--kill-on-invalid-dep"))
    ]


def test_arguments_keep_their_order(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """Options with values stay next to their values, in the user's order."""
    args = ["--partition", "gpu", "--mem", "4G", "--time", "01:00:00"]

    _start(tmp_path, args)

    assert _slurm_options(sbatch_calls[0]) == [
        *args,
        "--parsable",
    ]


def test_repeated_flags_are_kept(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """The same value may legitimately appear more than once."""
    args = ["--export", "A=1", "--export", "A=1"]

    _start(tmp_path, args)

    assert _slurm_options(sbatch_calls[0]) == [
        *args,
        "--parsable",
    ]


def test_parsable_is_not_duplicated(
    tmp_path: Path,
    sbatch_calls: list[list[str]],
) -> None:
    """If the user already passes --parsable it isn't added a second time."""
    _start(tmp_path, ["--parsable", "--mem", "1G"])

    assert _slurm_options(sbatch_calls[0]) == [
        "--parsable",
        "--mem",
        "1G",
    ]
