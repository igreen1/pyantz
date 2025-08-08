"""Given a matrix of variable, create pipelines for each row of this matrix.

For example, consider someone trying to copy 3 files and uniquely rename them

That user could create a case matrix, in this case as a .csv, as below

file_dst,file_name
path1,my_file_1
path2,cool_file_2,
path3,nice_file

This will create three pipelines and set the **variables** for each
    such that for the first pipeline "file_dst" variable is "path1"

**This will overwrite variables**
"""

import logging
import os
import pathlib
from collections.abc import Callable, Generator, Mapping
from typing import Any

import polars as pl
from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command."""

    matrix_path: str | os.PathLike[str]
    pipeline_config_template: config_base.PipelineConfig


@config_base.submitter_job(Parameters)
def create_pipelines_from_matrix(
    parameters: config_base.ParametersType,
    submit_fn: Callable[[config_base.Config], None],
    variables: Mapping[str, config_base.PrimitiveType],
    _pipeline_config: config_base.PipelineConfig,
    logger: logging.Logger,
) -> Status:
    """Copy file or directory from parameters.soruce to parameters.destination.

    ParametersType {
        source: path/to/copy/from
        destination: path/to/copy/to
    }

    Args:
        parameters (ParametersType): matrix to epxlode the pipeline
        submit_fn (SubmitFunctionType): function to submit the pipeline to for execution
        variables (Mapping[str, PrimitiveType]): variables from the outer context
        logger (logging.Logger): logger to assist with debugging

    Returns:
        Status: result of the job

    """
    if parameters is None:
        return Status.ERROR
    pipeline_params = Parameters.model_validate(parameters)

    for new_config in generate_configs(pipeline_params, variables=variables):
        logger.debug("Submitting new pipeline: %s", new_config.config.id)
        submit_fn(new_config)

    return Status.FINAL


def generate_configs(
    params: Parameters, variables: Mapping[str, config_base.PrimitiveType]
) -> Generator[config_base.Config, None, None]:
    """Create a generator for row of the matrix.

    Args:
        params (Parameters): ParametersType describing where to get variables
            and the pipeline template
        variables (Mapping[str, PrimitiveType]): variables to be passed to children configs

    Yields:
        Generator[Config, None, None]: A generator where each iteration yields a
            config for a row of the matrix

    Throws:
        RuntimeError: if the file type is not .parquet, .csv, or .xlsx

    """
    case_matrix: pl.DataFrame
    matrix_path = pathlib.Path(params.matrix_path)
    if matrix_path.suffix == ".csv":
        case_matrix = pl.read_csv(os.fspath(params.matrix_path))
    elif matrix_path.suffix == ".xlsx":
        case_matrix = pl.read_excel(os.fspath(params.matrix_path))
    elif matrix_path.suffix in (".parquet", ".parq"):
        case_matrix = pl.read_parquet(os.fspath(params.matrix_path))
    else:
        msg = "Unknown file type for the case matrix provided"
        raise RuntimeError(msg)

    pipeline_base: dict[str, Any] = params.pipeline_config_template.model_dump()

    case_matrix_names: list[str] = case_matrix.columns

    for idx, row in enumerate(case_matrix.iter_rows()):
        pipeline_base["name"] = f"pipeline_{idx}"
        yield config_base.Config.model_validate(
            {
                "config": pipeline_base,
                "variables": {
                    **variables,  # keep outer scope
                    **dict(zip(case_matrix_names, row, strict=False)),
                },
            }
        )
