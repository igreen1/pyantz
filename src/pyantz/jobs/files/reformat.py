"""Reformate between tabular datasets."""

import logging

import polars as pl
from pydantic import BaseModel, ConfigDict, FilePath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class FromCsvToParquetParameters(BaseModel):
    """Load a csv and dump it into a parquet."""

    model_config = ConfigDict(frozen=True)

    csv_file: FilePath

    parquet_file: FilePath


@add_parameters(FromCsvToParquetParameters)
@no_submit_fn
def csv_to_parquet(params: FromCsvToParquetParameters) -> bool:
    """Use polars to load a csv and dump it into a parquet."""
    logger = logging.getLogger(__name__)

    logger.debug("From %s -> %s", params.csv_file, params.parquet_file)

    if not params.csv_file.exists():
        logger.error("Cannot load csv - doesn't exist: %s", params.csv_file)
        return False

    try:
        pl.scan_csv(
            params.csv_file,
            low_memory=True,
        ).sink_parquet(
            params.parquet_file,
        )
    except Exception as exc:
        logger.exception("Error in CSV->PARQUET", exc_info=exc)
        return False
    else:
        return True
