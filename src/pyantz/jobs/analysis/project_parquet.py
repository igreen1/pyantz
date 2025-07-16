"""Project a dataframe (aka select certain columns from it)"""

from collections.abc import Sequence
import os
import logging

import polars as pl
from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class ProjectParquetParameters(BaseModel, frozen=True):
    """Parameters for filter_parquet"""

    input_file: str
    output_file: str
    columns: Sequence[str]


@config_base.simple_job(ProjectParquetParameters)
def filter_parquet(
    parameters: config_base.ParametersType,
    logger: logging.Logger,  # pylint: disable=unused-argument
) -> Status:
    """Filter the parquet file down"""

    params = ProjectParquetParameters.model_validate(parameters)

    if not os.path.exists(params.input_file):
        logger.error("No such file: %s", params.input_file)
        return Status.ERROR
    if not os.path.exists(dir_name := os.path.dirname(params.output_file)):
        logger.error("No directory to place file in %s", dir_name)

    pl.scan_parquet(params.input_file).select(
        *[pl.col(col) for col in params.columns]
    ).sink_parquet(params.output_file)

    return Status.SUCCESS
