"""Test that duplicate job ids are rejected rather than silently dropped."""

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


def _job(job_id: str) -> dict[str, Any]:
    return {"job_id": job_id, "function": NOP, "parameters": {}}


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    """Two jobs with one id fail validation naming the id."""
    with pytest.raises(ValidationError, match="Duplicate job_id"):
        InitialConfig.model_validate(
            _config([_job("x"), _job("x")], tmp_path),
        )


def test_duplicate_ids_among_virtual_jobs_rejected(tmp_path: Path) -> None:
    """Duplicates are detected when virtual jobs are present as well."""
    virtual = {
        "job_id": "x",
        "function": "pyantz.virtual.add_variables.AddVariables",
        "parameters": {"variables": {"a": 1}},
    }
    with pytest.raises(ValidationError, match="'x'"):
        InitialConfig.model_validate(_config([virtual, _job("x")], tmp_path))


def test_unique_ids_unaffected(tmp_path: Path) -> None:
    """Unique ids still compile all jobs."""
    config = InitialConfig.model_validate(
        _config([_job("x"), _job("y"), _job("z")], tmp_path),
    )
    assert {job.job_id for job in config.jobs} == {"x", "y", "z"}
