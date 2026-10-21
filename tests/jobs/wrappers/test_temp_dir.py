"""Test running jobs with a temporary directory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz import start
from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.runner.job_manager import run_job
from pyantz.jobs.wrappers.variables import TemporaryDirectoryParams

if TYPE_CHECKING:
    from pathlib import Path

TEMP_DIR_JOB = "pyantz.jobs.wrappers.variables.run_jobs_with_temp_dir"
DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"


def _record_dir(record: Path) -> dict[str, Any]:
    """Job which writes the temporary directory path (from the variable) to a file."""
    return {
        "function": DISPATCH,
        "parameters": {
            "cmd": ["sh", "-c", f'echo "%{{tmp}}" > "{record}"; touch "%{{tmp}}/data"'],
        },
    }


def _run(parameters: dict[str, Any]) -> bool:
    job = JobWithContext.model_validate(
        {"function": TEMP_DIR_JOB, "parameters": parameters},
    )
    return run_job(job, lambda *_: None)


def _pipeline(tmp_path: Path, parameters: dict[str, Any]) -> dict[str, Any]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return {
        "jobs": [{"function": TEMP_DIR_JOB, "parameters": parameters}],
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
        },
    }


def test_local_mode_does_not_need_a_shared_directory(tmp_path: Path) -> None:
    """Local mode works with the system's temporary location."""
    record = tmp_path / "record"

    assert _run({"variable_name": "tmp", "jobs": [_record_dir(record)]}) is True

    used = record.read_text().strip()
    assert used
    assert not os.path.exists(used)  # noqa: PTH110  (deleted afterwards)


def test_local_mode_uses_the_shared_directory_as_parent(tmp_path: Path) -> None:
    """With shared_working_dir, the temporary directory is created inside it."""
    shared = tmp_path / "shared"
    shared.mkdir()
    record = tmp_path / "record"

    assert _run(
        {
            "variable_name": "tmp",
            "shared_working_dir": os.fspath(shared),
            "jobs": [_record_dir(record)],
        },
    )

    assert record.read_text().strip().startswith(os.fspath(shared))
    assert not list(shared.iterdir())  # and cleaned up


def test_local_mode_jobs_cannot_submit(tmp_path: Path) -> None:
    """Submitting from a local-mode job fails with an explanation, not later."""
    job = {
        "function": "pyantz.jobs.branching.if_else.conditionally_execute",
        "parameters": {
            "left_side": 1,
            "right_side": 1,
            "comparator": "==",
            "if_true": {
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(tmp_path / "never")},
            },
        },
    }

    assert _run({"variable_name": "tmp", "jobs": [job]}) is False
    assert not (tmp_path / "never").exists()


def test_remote_mode_requires_a_shared_directory() -> None:
    """Remote mode can't pick a location by itself."""
    with pytest.raises(ValidationError, match="shared_working_dir is required"):
        TemporaryDirectoryParams.model_validate(
            {"variable_name": "tmp", "submit_type": "remote", "jobs": []},
        )


def test_remote_mode_jobs_get_the_variable_and_directory_is_cleaned(
    tmp_path: Path,
) -> None:
    """Jobs find the directory in the variable, and a non-empty one is deleted."""
    shared = tmp_path / "shared"
    shared.mkdir()
    record = tmp_path / "record"

    start(
        _pipeline(
            tmp_path,
            {
                "variable_name": "tmp",
                "submit_type": "remote",
                "shared_working_dir": os.fspath(shared),
                "jobs": [_record_dir(record)],
            },
        ),
    )

    used = record.read_text().strip()
    assert used.startswith(os.fspath(shared))  # the job got the variable
    assert not list(shared.iterdir())  # the directory (with its file) is gone
