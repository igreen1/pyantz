"""Test compiling virtual jobs."""

import os
from typing import TYPE_CHECKING

from pyantz.infrastructure.config.job import make_job
from pyantz.infrastructure.virtual import compile_virtual

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


def test_compilation() -> None:
    """Test compiling."""
    config = list(
        map(
            make_job,
            [
                {
                    "job_id": "1",
                    "function": "pyantz.virtual.add_variables.AddVariables",
                    "parameters": {
                        "variables": {
                            "my_path": "file_NAME.txt",
                        },
                    },
                },
                {
                    "job_id": "2",
                    "function": "pyantz.jobs.testing.touch_file",
                    "parameters": {
                        "path": "%{my_path}",
                    },
                    "depends_on": ["1"],
                },
            ],
        )
    )

    result = compile_virtual(config)

    assert len(result) == 1
    job = result[0]
    assert not job.depends_on
    assert job.parameters["shared_variables"] == {"my_path": "file_NAME.txt"}

    assert len(job.parameters["jobs"]) == 1
    child_job = job.parameters["jobs"][0]
    assert child_job.job_id == "2"
    assert not child_job.depends_on
    assert child_job.parameters == {"path": "%{my_path}"}


def test_add_variable(
    tmp_path: Path,
    run_integrated_jobs: Callable[[list[dict[str, Any]]], None],
) -> None:
    """Test adding variables using a virtual job."""
    config = [
        {
            "job_id": "1",
            "function": "pyantz.virtual.add_variables.AddVariables",
            "parameters": {
                "variables": {
                    "my_path": "file_NAME.txt",
                },
            },
        },
        {
            "job_id": "2",
            "function": "pyantz.jobs.testing.touch_file",
            "parameters": {
                "path": os.fspath(tmp_path / "%{my_path}"),
            },
            "depends_on": ["1"],
        },
    ]

    run_integrated_jobs(config)

    assert (tmp_path / "file_NAME.txt").exists()
