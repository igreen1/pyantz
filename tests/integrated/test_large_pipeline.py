"""A large pipeline of jobs to be run."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from pyantz import start
from pyantz.infrastructure.config import JobConfig

if TYPE_CHECKING:
    from collections.abc import Callable

exec_path = Path(__file__).parent.parent / "assets" / "script.bash"


def set_variable(set_var: Callable[[str, Any], None], test_path: str) -> None:
    """Set variables for the test."""
    set_var("output_file", os.path.join(test_path, "my_super_cool.csv"))
    set_var("case_matrix", os.path.join(test_path, "case_matrix.parquet"))
    set_var("root_output_dir", os.path.join(test_path, "output"))

def test_large_pipeline(tmp_path: Path) -> None:

    child_template: list[dict[str, Any]] = [
        {
            "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
            "parameters": {
                "shared_variables": {"script_path": "%{output_dir}/script.bash"},
                "jobs": [
                    {
                        "function": "pyantz.jobs.files.moving.copy",
                        "job_id": "%{pipeline_id}_a",
                        "parameters": {
                            "source": os.fspath(exec_path),
                            "destination": "%{script_path}",
                        },
                    },
                    {
                        "function": "pyantz.jobs.subproc.dispatch.dispatch",
                        "depends_on": ["%{pipeline_id}_a"],
                        "parameters": {
                            "cmd": ("%{script_path}", "%{output_dir}/file.txt"),
                            "stdout_file": "%{output_dir}/stdout.txt",
                        },
                    },
                ],
            },
        },
    ]

    pipeline_config: list[dict[str, Any]] = [
        {
            "function": "pyantz.jobs.wrappers.variables.set_variables",
            "parameters": {
                "setter_job": "tests.integrated.test_large_pipeline.set_variable",
                "set_job_kwargs": {"test_path": os.fspath(tmp_path)},
                "jobs": [
                    {
                        "job_id": "matrix_creation",
                        "function": "pyantz.jobs.branching.case_matrix.create_case_matrix",
                        "parameters": {
                            "save_file": "%{case_matrix}",
                            "variables": {
                                "columnA": {
                                    "range": {
                                        "possible_values": (
                                            10,
                                            12,
                                            14,
                                        ),
                                    },
                                },
                                "file": {
                                    "range": {
                                        "possible_values": (
                                            "fileA",
                                            "fileB",
                                            "fileC",
                                        ),
                                    }
                                },
                            },
                        },
                    },
                    {
                        "job_id": "make_output_dir",
                        "depends_on": ["matrix_creation"],
                        "function": "pyantz.jobs.files.simple.mkdir",
                        "parameters": {
                            "dir_path": "%{root_output_dir}",
                        },
                    },
                    {
                        "job_id": "case matrix set",
                        "depends_on": ["make_output_dir"],
                        "function": "pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir",
                        "parameters": {
                            "case_matrix_parquet": "%{case_matrix}",
                            "output_dir": "%{root_output_dir}",
                            "pipeline_template": child_template,
                        },
                    },
                ],
            },
        },
    ]

    jobs = pipeline_config

    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()

    config: dict[str, Any] = {
        "jobs": jobs,
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
            "use_same_proc": True,
            "timeout": 1,
        },
    }
    start(config)
    breakpoint()
    raise AssertionError
