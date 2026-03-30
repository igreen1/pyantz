"""Common pytest code."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pyantz import start
from pyantz.infrastructure.config import JobConfig, InitialConfig
from pyantz.infrastructure.config.runners.local_runner import LocalRunnerConfig

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


@pytest.fixture
def run_integrated_jobs(tmp_path: Path) -> Callable[[list[dict[str, Any]]], None]:
    """Run a job in an integrated pipeline."""
    working_dir = tmp_path / "_working_dir"
    working_dir.mkdir()

    default_config = {
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }

    def _run(jobs: list[dict[str, Any]]) -> None:

        jobs_validated = [JobConfig.model_validate(j) for j in jobs]

        config = {
            **default_config,
            "jobs": jobs_validated,
        }

        initial_config = InitialConfig[LocalRunnerConfig].model_validate(config)

        start(initial_config)

    return _run
