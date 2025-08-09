"""Project a dataframe (aka select certain columns from it)."""

import logging
import pathlib
from collections.abc import Sequence

import polars as pl
from pydantic import BaseModel, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """Parameters for filter_parquet."""

    input_file: str
    output_file: str
    columns: Sequence[str]


class _RuntimeParameters(BaseModel, frozen=True):
    """Check that input file exists.

    Cannot be done at compile as the file may be created as a side effect.
    """

    input_file: FilePath
    output_file: str
    columns: Sequence[str]


@config_base.simple_job(Parameters)
def filter_parquet(
    parameters: config_base.ParametersType,
    logger: logging.Logger,  # pylint: disable=unused-argument
) -> Status:
    """Filter the parquet file down."""
    params = _RuntimeParameters.model_validate(parameters)

    input_file_path = pathlib.Path(params.input_file)

    if not input_file_path.exists():
        logger.error("No such file: %s", params.input_file)
        return Status.ERROR
    if not input_file_path.parent.exists():
        logger.error("No directory to place file in %s", input_file_path.parent)

    pl.scan_parquet(params.input_file).select(  # pyright: ignore[reportUnknownMemberType]
        *[pl.col(col) for col in params.columns]
    ).sink_parquet(params.output_file)

    return Status.SUCCESS
