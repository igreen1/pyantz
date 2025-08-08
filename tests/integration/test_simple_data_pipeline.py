"""Run a script, parse its output, and provide some simple analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl
from polars.testing import assert_frame_equal

import pyantz.run
from pyantz.infrastructure.config.base import InitialConfig
from pyantz.infrastructure.core.status import Status

if TYPE_CHECKING:
    import pytest

NUMBER_ROWS: int = 10
BASIC_DATA: list[tuple[int, float, int]] = list(
    zip(
        range(NUMBER_ROWS),
        [i * 0.1 for i in range(NUMBER_ROWS)],
        [i + 100 for i in range(NUMBER_ROWS)],
        strict=True,
    )
)
BASIC_SCRIPT: str = f"""#!/bin/bash

echo "Running my cool script!"
echo "col1,col2,col3,pipeline_id,parent_var"
{"\n".join([f"echo {val1},{val2},{val3},${{1}},${{SOME_VAR}}" for val1, val2, val3 in BASIC_DATA])}
"""


def parse_input_file(parameters: dict[str, str], *_: Any) -> Status:  # noqa: ANN401
    """Parse the output of our special script above."""
    file_path = parameters["input_file"]
    output_file = parameters["output_file"]
    pl.scan_csv(file_path, skip_lines=1).sink_csv(output_file)
    return Status.SUCCESS


def test_integrated_analysis_pipeline(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test a sample analysis pipeline."""
    tmpdir = tmp_path_factory.mktemp("analysis_pipeline_folder")
    script_path = tmpdir / "runner.sh"
    with script_path.open("w", encoding="utf-8") as fh:
        fh.write(BASIC_SCRIPT)

    script_path.chmod(0o777)

    subpipeline_stages = [
        {
            "type": "mutable_job",
            "function": "pyantz.jobs.variables.change_many_variables.change_many_variables",
            "parameters": {
                "variable_statements": {
                    "base_dir": str(tmpdir),
                }
            },
        },
        {
            "type": "mutable_job",
            "function": "pyantz.jobs.variables.change_many_variables.change_many_variables",
            "parameters": {
                "variable_statements": {
                    "run_dir": "%{base_dir}/%{PIPELINE_ID}",
                }
            },
        },
        {
            "type": "mutable_job",
            "function": "pyantz.jobs.variables.change_many_variables.change_many_variables",
            "parameters": {
                "variable_statements": {
                    "script_path": "%{base_dir}/runner.sh",
                    "script_output_file": "%{run_dir}/output.txt",
                    "script_err_file": "%{run_dir}/err.txt",
                    "working_dir": "%{run_dir}",
                    "parsed_output_file": "%{run_dir}/parsed.csv",
                    "parsed_as_parquet_file": "%{run_dir}/parsed.parquet",
                    "filtered_output_file": "%{run_dir}/filtered.parquet",
                },
            },
        },
        {
            "type": "job",
            "function": "pyantz.jobs.file.make_dirs.make_dirs",
            "parameters": {"path": "%{run_dir}"},
        },
        {
            "type": "job",
            "function": "pyantz.jobs.dispatch.run_script.run_script",
            "parameters": {
                "script_path": "%{script_path}",
                "script_args": ["%{PIPELINE_ID}"],
                "stdout_save_file": "%{script_output_file}",
                "stderr_save_file": "%{script_err_file}",
                "current_working_dir": "%{working_dir}",
            },
        },
        {
            "type": "job",
            "function": "tests.integration.test_simple_data_pipeline.parse_input_file",
            "parameters": {
                "input_file": "%{script_output_file}",
                "output_file": "%{parsed_output_file}",
            },
        },
        {
            "type": "job",
            "function": "pyantz.jobs.analysis.csv_to_parquet.csv_to_parquet",
            "parameters": {
                "input_file": "%{parsed_output_file}",
                "output_file": "%{parsed_as_parquet_file}",
            },
        },
    ]

    pipeline_config = {
        "variables": {
            "some_var": 1,
        },
        "config": {
            "type": "pipeline",
            "stages": [
                {
                    "type": "job",
                    "function": "pyantz.jobs.variables.assign_environment_variable.assign_environment_variable",  # pylint: disable=line-too-long # noqa: E501
                    "parameters": {"environmental_variables": {"SOME_VAR": "%{some_var}"}},
                },
                {
                    "type": "submitter_job",
                    "function": "pyantz.jobs.branch.explode_pipeline.explode_pipeline",
                    "parameters": {
                        "num_pipelines": 2,
                        "pipeline_config_template": {
                            "type": "pipeline",
                            "stages": subpipeline_stages,
                        },
                    },
                },
            ],
        },
    }

    overall_config = {"analysis_config": pipeline_config, "submitter_config": {"type": "local"}}

    config = InitialConfig.model_validate(overall_config)
    pyantz.run.run(config)

    # check that our output is as expected
    expected_parent_output = pl.DataFrame(
        BASIC_DATA,
        schema=["col1", "col2", "col3"],
        orient="row",
    )
    for pipeline_id in (0, 1):
        expected = expected_parent_output.with_columns(
            pipeline_id=pl.lit(pipeline_id), parent_var=pl.lit(1)
        )
        run_dir = tmpdir / str(pipeline_id)
        assert run_dir.exists()
        csv = run_dir / "parsed.csv"
        assert csv.exists()
        assert_frame_equal(
            expected,
            pl.read_csv(csv),
            check_dtypes=False,
        )
        parq = run_dir / "parsed.parquet"
        assert parq.exists()
        assert_frame_equal(
            expected,
            pl.read_parquet(parq),
            check_dtypes=False,
        )
