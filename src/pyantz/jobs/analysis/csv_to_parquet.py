"""Convert a CSV file to a parquet file."""

import logging
import pathlib

import polars as pl
from pydantic import BaseModel, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """Parameters of files to convert."""

    input_file: str
    output_file: str


class _RuntimeParameters(BaseModel, frozen=True):
    """At runtime, check of input existence."""

    input_file: FilePath
    output_file: str


@config_base.simple_job(Parameters)
def csv_to_parquet(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Convert the input csv to a parquet file.

    Args:
        parameters (ParametersType): input and output files
        logger (logging.Logger): logger instance

    Returns (Status):
        resulting status of this job

    """
    params = _RuntimeParameters.model_validate(parameters)

    input_file = pathlib.Path(params.input_file)
    output_file = pathlib.Path(params.output_file)

    try:
        pl.scan_csv(input_file).sink_parquet(output_file)
    except (TypeError, ValueError) as exc:
        logger.exception("Unexpected error converting csv", exc_info=exc)
        return Status.ERROR

    return Status.SUCCESS if output_file.exists() else Status.ERROR
