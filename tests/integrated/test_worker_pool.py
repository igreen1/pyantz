"""Test the default local runner mode: a pool of separate worker processes."""

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.config.runners import LocalRunnerConfig

if TYPE_CHECKING:
    from pathlib import Path


def test_default_does_not_depend_on_environment(tmp_path: Path) -> None:
    """The default is fixed (a pool), even though pytest sets PYTEST_* variables."""
    assert "PYTEST_VERSION" in os.environ
    assert LocalRunnerConfig(working_directory=tmp_path).use_same_proc is False


def test_default_runs_jobs_in_a_pool_of_processes(tmp_path: Path) -> None:
    """Without use_same_proc, jobs run in worker processes and all complete."""
    work = tmp_path / "work"
    work.mkdir()
    jobs: list[dict[str, Any]] = [
        {
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            "parameters": {"path": os.fspath(tmp_path / f"file_{i}.txt")},
        }
        for i in range(4)
    ]

    start(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "local_proc",
                "working_directory": os.fspath(work),
                "poll_timeout": 0.05,
                "number_processes": 2,
            },
        },
    )

    assert {p.name for p in tmp_path.glob("file_*.txt")} == {
        f"file_{i}.txt" for i in range(4)
    }
