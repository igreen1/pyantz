"""Test that bad dependency graphs give clear errors when compiling."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import InitialConfig

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _config(jobs: list[dict[str, Any]], work_dir: Path) -> dict[str, Any]:
    return {
        "jobs": jobs,
        "submitter": {
            "type_": "local_proc",
            "working_directory": os.fspath(work_dir),
        },
    }


def _job(job_id: str, deps: list[str] | None = None) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "function": NOP,
        "parameters": {},
        "depends_on": deps,
    }


def _virtual(job_id: str) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "function": "pyantz.virtual.add_variables.AddVariables",
        "parameters": {"variables": {"a": 1}},
    }


def test_unknown_dependency_with_virtual_job_names_jobs(tmp_path: Path) -> None:
    """An unknown dependency names the job and the missing id."""
    jobs = [_virtual("v"), _job("child", ["v", "ghost"])]
    with pytest.raises(ValidationError, match=r"child.*ghost"):
        InitialConfig.model_validate(_config(jobs, tmp_path))


def test_cycle_without_virtual_jobs_names_jobs(tmp_path: Path) -> None:
    """A two-job cycle is reported with the jobs involved."""
    jobs = [_job("a", ["b"]), _job("b", ["a"])]
    with pytest.raises(ValidationError, match=r"Dependency cycle.*[ab] -> [ab]"):
        InitialConfig.model_validate(_config(jobs, tmp_path))


def test_cycle_with_virtual_jobs_names_jobs(tmp_path: Path) -> None:
    """Cycles are also reported when virtual jobs are present."""
    jobs = [_virtual("v"), _job("a", ["b", "v"]), _job("b", ["a"])]
    with pytest.raises(ValidationError, match="Dependency cycle"):
        InitialConfig.model_validate(_config(jobs, tmp_path))


def test_valid_graph_still_compiles(tmp_path: Path) -> None:
    """A valid DAG with a virtual job is unaffected."""
    jobs = [_virtual("v"), _job("a", ["v"]), _job("b", ["a"])]
    config = InitialConfig.model_validate(_config(jobs, tmp_path))
    assert config.jobs
