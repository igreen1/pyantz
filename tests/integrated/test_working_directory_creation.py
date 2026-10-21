"""Test the local runner creates its working directory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path


def _config(work: Path, touched: Path) -> dict[str, Any]:
    return {
        "jobs": [
            {
                "function": "pyantz.jobs.testing.touch_file.touch_file",
                "parameters": {"path": os.fspath(touched)},
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
        },
    }


def test_nested_missing_working_directory_is_created(tmp_path: Path) -> None:
    """Missing parents of the working directory are created too."""
    work = tmp_path / "a" / "b"
    touched = tmp_path / "done.txt"

    start(_config(work, touched))

    assert work.is_dir()
    assert touched.exists()


def test_existing_working_directory_is_reused(tmp_path: Path) -> None:
    """An existing working directory is not an error."""
    work = tmp_path / "work"
    work.mkdir()
    touched = tmp_path / "done.txt"

    start(_config(work, touched))

    assert touched.exists()
