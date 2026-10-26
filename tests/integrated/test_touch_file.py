"""Test touching a file."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Final

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

MINIMAL_CONFIG: Final[dict[str, Any]] = {
    "jobs": [
        {
            "function": "pyantz.jobs.testing.touch_file",
            "parameters": {"path": "%{FILE_PATH}"},
        }
    ],
    "submitter": {
        "type_": "local_proc",
        "use_same_proc": True,
        # "working_directory" # set in test
    },
}


def test_touch_file(tmp_path: Path) -> None:
    """Test creating a file."""
    config = deepcopy(MINIMAL_CONFIG)

    file_path = tmp_path / "some_file.txt"

    config["variables"] = {"FILE_PATH": os.fspath(file_path)}
    config["submitter"]["working_directory"] = os.fspath(tmp_path)

    start(config)  # type: ignore[arg-type]

    assert file_path.exists()
