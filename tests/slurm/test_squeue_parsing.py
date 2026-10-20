"""Test finding the jobs which depend on the current slurm job."""

import subprocess
from typing import Any

import pytest

from pyantz.infrastructure.runner.slurm.slurm_runner import _get_dependent_jobs

REALISTIC_OUTPUT = (
    "123|afterok:100(unfulfilled),afterok:101(unfulfilled)\n"
    "124|(null)\n"
    "125|afterok:101(unfulfilled)\n"
    "126|afterok:100_3(unfulfilled)\n"
)


@pytest.fixture
def squeue(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Mock subprocess.run to return realistic squeue output."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, REALISTIC_OUTPUT.encode())

    monkeypatch.setattr(subprocess, "run", _run)
    return calls


def test_finds_pending_dependents(squeue: list[list[str]]) -> None:
    """Only jobs waiting on the current job are returned, with all their deps."""
    assert _get_dependent_jobs("100") == {"123": ["100", "101"]}
    assert len(squeue) == 1


def test_other_job_ids_are_matched_exactly(squeue: list[list[str]]) -> None:
    """The id is matched as a whole: 10 is not 100, 101 is a different job."""
    assert _get_dependent_jobs("10") == {}
    assert _get_dependent_jobs("101") == {
        "123": ["100", "101"],
        "125": ["101"],
    }
    assert len(squeue) == 2  # noqa: PLR2004


def test_squeue_arguments_are_separate_and_unquoted(squeue: list[list[str]]) -> None:
    """The state and the format are passed as proper separate arguments."""
    _get_dependent_jobs("100")

    cmd = squeue[0]
    assert cmd[0] == "squeue"
    assert "-h" in cmd
    assert cmd[cmd.index("-t") + 1] == "PD"
    assert cmd[cmd.index("-o") + 1] == "%i|%E"
    assert not any('"' in arg or arg.startswith(" ") for arg in cmd)


def test_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """No pending jobs gives no dependents."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **_kwargs: subprocess.CompletedProcess(cmd, 0, b""),
    )
    assert _get_dependent_jobs("100") == {}
