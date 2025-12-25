"""Test touching a file."""

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Final

from pyantz import start

MINIMAL_CONFIG: Final[dict[str, Any]] = {
    "jobs": [
        {
            "function": "pyantz.jobs.common.touch_file.touch_file",
            "parameters": {"path": "%{FILE_PATH}"},
        }
    ],
    "submitter": {
        "type_": "local_proc",
        # "working_directory" # set in test
    },
}


def test_touch_file(tmp_path: Path) -> None:
    """Test creating a file."""
    config = deepcopy(MINIMAL_CONFIG)

    file_path = tmp_path / "some_file.txt"

    config["variables"] = {"FILE_PATH": os.fspath(file_path)}
    config["submitter"]["working_directory"] = os.fspath(tmp_path)

    start(config) # type: ignore[arg-type]

    assert file_path.exists()
