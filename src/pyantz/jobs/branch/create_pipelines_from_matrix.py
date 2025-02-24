"""Given a matrix of variable, create pipelines for each row of this matrix

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
from typing import Any, Callable, Generator, Mapping

import pandas as pd
from pydantic import BaseModel

from pyantz.infrastructure.config.base import *
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the copy command"""

    matrix_path: str | os.PathLike[str]
    pipeline_config_template: PipelineConfig


@submitter_job(Parameters)
def create_pipelines_from_matrix(
    parameters: ParametersType,
    submit_fn: Callable[[Config], None],
    variables: Mapping[str, PrimitiveType],
    _pipeline_config: PipelineConfig,
    logger: logging.Logger,
) -> Status:
    """Copy file or directory from parameters.soruce to parameters.destination

    ParametersType {
        source: path/to/copy/from
        destination: path/to/copy/to
    }

    Args:
        parameters (ParametersType): ParametersType for the copy function

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
    params: Parameters, variables: Mapping[str, PrimitiveType]
) -> Generator[Config, None, None]:
    """Create a generator for row of the matrix

    Args:
        params (Parameters): ParametersType describing where to get variables
            and the pipeline template

    Yields:
        Generator[Config, None, None]: A generator where each iteration yields a
            config for a row of the matrix

    Throws:
        RuntimeError: if the file type is not .parquet, .csv, or .xlsx
    """

    case_matrix: pd.DataFrame
    if os.path.splitext(params.matrix_path)[1] == ".csv":
        case_matrix = pd.read_csv(params.matrix_path)
    elif os.path.splitext(params.matrix_path)[1] == ".xlsx":
        case_matrix = pd.read_excel(params.matrix_path)
    elif os.path.splitext(params.matrix_path)[1] in (".parquet", ".parq"):
        case_matrix = pd.read_parquet(params.matrix_path)
    else:
        raise RuntimeError("Unknown file type for the case matrix provided")

    pipeline_base: dict[str, Any] = params.pipeline_config_template.model_dump()

    for idx, row in case_matrix.iterrows():
        pipeline_base["name"] = f"pipeline_{idx}"
        yield Config.model_validate(
            {
                "config": pipeline_base,
                "variables": {
                    **variables,  # keep outer scope
                    **dict(zip(row.index, row)),
                },
            }
        )
