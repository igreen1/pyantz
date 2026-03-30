"""A large pipeline of jobs to be run."""

import os
from pathlib import Path
from typing import Any

from pyantz import start

exec_path = Path(__file__).parent.parent / "assets" / "script.bash"


def test_large_pipeline(tmp_path: Path) -> None:
    """Test running a large pipeline that looks like a real script."""
    pipeline_template = [
        {
            "job_id": "a",
            "function": "pyantz.virtual.add_variables.AddVariables",
            "parameters": {
                "variables": {
                    "script_path": "%{output_dir}/script.bash",
                },
            },
        },
        {
            "job_id": "b",
            "function": "pyantz.jobs.files.moving.copy",
            "depends_on": ("a",),
            "parameters": {
                "source": os.fspath(exec_path),
                "destination": "%{script_path}",
            },
        },
        {
            "job_id": "c",
            "function": "pyantz.jobs.subproc.dispatch.dispatch",
            "depends_on": ("b",),
            "parameters": {
                "cmd": ("%{script_path}", "%{output_dir}/file.txt"),
                "stdout_file": "%{output_dir}/stdout.txt",
            },
        },
    ]

    output_dir  = tmp_path / "output"
    output_dir.mkdir()
    jobs = [
        {
            "job_id": "1",
            "function": "pyantz.virtual.add_variables.AddVariables",
            "parameters": {
                "variables": {
                    "output_file": os.fspath(tmp_path / "my_super_cool.csv"),
                    "case_matrix": os.fspath(tmp_path / "case_matrix.parquet"),
                },
            },
        },
        {
            "job_id": "2",
            "depends_on": ["1"],
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
            "job_id": "3",
            "depends_on": ("2",),
            "function": "pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir",
            "parameters": {
                "case_matrix_parquet": "%{case_matrix}",
                "output_dir": os.fspath(output_dir),
                "pipeline_template": pipeline_template,
            },
        },
    ]

    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()

    config = {
        "jobs": jobs,
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }
    start(config)
    raise ValueError

