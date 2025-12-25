"""Test jobs with dependencies fail properly."""

import os
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


def test_pipeline_successful(tmp_path: Path) -> None:
    """Test successfully running dependent jobs."""
    config: dict[str, Any] = {
        "jobs": [
            {
                "job_id": "job1",
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{FILE_PATH}"
                },
            },
            {
                "job_id": "job2",
                "depends_on": ["job1"],
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{TMP_DIR}/another_file.txt"
                }
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": tmp_path,
        },
        "variables": {
            "FILE_PATH": os.fspath(tmp_path / "my_path.txt"),
            "TMP_DIR": os.fspath(tmp_path)
        },
    }

    start(config)

    assert (tmp_path / "another_file.txt").exists()

def test_pipeline_failure(tmp_path: Path) -> None:
    """Test successfully running dependent jobs."""
    config: dict[str, Any] = {
        "jobs": [
            {
                "job_id": "job1",
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{FILE_PATH}",
                    "exist_ok": False, # used to induce failure
                },
            },
            {
                "job_id": "job2",
                "depends_on": ["job1"],
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{TMP_DIR}/another_file.txt"
                }
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": tmp_path,
        },
        "variables": {
            "FILE_PATH": os.fspath(tmp_path / "my_path.txt"),
            "TMP_DIR": os.fspath(tmp_path)
        },
    }

    (tmp_path / "my_path.txt").touch()

    start(config)

    assert not (tmp_path / "another_file.txt").exists()


def test_pipeline_failure_no_deps(tmp_path: Path) -> None:
    """Test successfully running dependent jobs."""
    config: dict[str, Any] = {
        "jobs": [
            {
                "job_id": "job1",
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{FILE_PATH}",
                    "exist_ok": False, # used to induce failure
                },
            },
            {
                "job_id": "job2",
                "function": "pyantz.jobs.common.touch_file.touch_file",
                "parameters": {
                    "path": "%{TMP_DIR}/another_file.txt"
                }
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": tmp_path,
        },
        "variables": {
            "FILE_PATH": os.fspath(tmp_path / "my_path.txt"),
            "TMP_DIR": os.fspath(tmp_path)
        },
    }

    (tmp_path / "my_path.txt").touch()

    start(config)

    assert (tmp_path / "another_file.txt").exists()

