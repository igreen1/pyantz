"""Test a job depending on more than one virtual job."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.config import InitialConfig

if TYPE_CHECKING:
    from pathlib import Path


def _add_variables(job_id: str, variables: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "function": "pyantz.virtual.add_variables.AddVariables",
        "parameters": {"variables": variables},
    }


def _config(tmp_path: Path) -> dict[str, Any]:
    work = tmp_path / "work"
    work.mkdir()
    return {
        "jobs": [
            _add_variables("v1", {"a": "one"}),
            _add_variables("v2", {"b": "two"}),
            {
                "job_id": "j",
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(tmp_path / "out_%{a}_%{b}.txt")},
                "depends_on": ["v1", "v2"],
            },
        ],
        "submitter": {"type_": "local_proc", "working_directory": os.fspath(work)},
    }


def _all_dependencies(jobs: Any) -> set[str]:  # noqa: ANN401
    return {dep for job in jobs for dep in (job.depends_on or set())}


def test_no_dangling_references_to_virtual_jobs(tmp_path: Path) -> None:
    """Compiled jobs reference only jobs which exist."""
    config = InitialConfig.model_validate(_config(tmp_path))

    existing = {job.job_id for job in config.jobs}
    assert _all_dependencies(config.jobs) <= existing
    assert not {"v1", "v2"} & _all_dependencies(config.jobs)


def test_job_receives_variables_of_both_virtual_jobs(tmp_path: Path) -> None:
    """The dependent job runs with the variables from both virtual parents."""
    report = start(_config(tmp_path))

    assert report is None or report.all_succeeded
    assert (tmp_path / "out_one_two.txt").exists()
