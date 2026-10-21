"""Test the local pipeline wrapper."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

RUN_PIPELINE = "pyantz.jobs.wrappers.local.run_pipeline"
TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _config(tmp_path: Path, parameters: dict[str, Any]) -> dict[str, Any]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return {
        "jobs": [{"function": RUN_PIPELINE, "parameters": parameters}],
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
        },
    }


def _touch(path: Path) -> dict[str, Any]:
    return {"function": TOUCH, "parameters": {"path": os.fspath(path)}}


def test_runs_without_named_pipes(tmp_path: Path) -> None:
    """`inter_job_named_pipes` is not needed."""
    first, second = tmp_path / "first", tmp_path / "second"

    start(_config(tmp_path, {"jobs": [_touch(first), _touch(second)]}))

    assert first.exists()
    assert second.exists()


def test_still_accepts_named_pipes(tmp_path: Path) -> None:
    """Configurations which still pass the old parameter keep working."""
    first = tmp_path / "first"

    start(
        _config(
            tmp_path,
            {"jobs": [_touch(first)], "inter_job_named_pipes": ["a", "b"]},
        ),
    )

    assert first.exists()


def test_stops_at_the_first_failing_job(tmp_path: Path) -> None:
    """Jobs after a failure are not run."""
    existing = tmp_path / "existing"
    existing.touch()
    failing = {
        "function": TOUCH,
        "parameters": {"path": os.fspath(existing), "exist_ok": False},
    }
    never = tmp_path / "never"

    start(_config(tmp_path, {"jobs": [failing, _touch(never)]}))

    assert not never.exists()
