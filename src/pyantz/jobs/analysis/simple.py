"""Simple operations."""

import logging
from pathlib import Path
from typing import Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, FilePath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class ColumnarOperationParameters(BaseModel):
    """Perform an operation and save the resulting dataframe in a parquet."""

    model_config = ConfigDict(frozen=True)

    source_parquet_file: FilePath

    result_parquet_file: str

    left_col: str

    right_col: str

    result_col: str

    operation: Literal[
        "+",
        "-",
        "*",
        "/",
    ]


OP_MAPPING = {
    "+": pl.Expr.add,
    "-": pl.Expr.sub,
    "/": pl.Expr.truediv,
    "*": pl.Expr.mul,
}


@add_parameters(ColumnarOperationParameters)
@no_submit_fn
def columnar_operation(params: ColumnarOperationParameters) -> bool:
    """Perform a simple operation between two columns."""
    logger = logging.getLogger(__name__)

    logger.debug("Starting columnar operation %s", params.operation)

    if not params.source_parquet_file.exists():
        logger.exception(
            "Cannot update parquet with operation, no such file: %s",
            params.source_parquet_file,
        )
        return False

    try:
        lf = pl.scan_parquet(params.source_parquet_file)
    except OSError as exc:
        logger.exception("Error while scanning, cannot complete op.", exc_info=exc)
        return False

    true_cols = lf.collect_schema().names()
    for col in (params.left_col, params.right_col):
        if col not in true_cols:
            logger.error("%s not in parquet file, exiting", col)
            return False

    operation = OP_MAPPING[params.operation]

    lf = lf.with_columns(
        operation(pl.col(params.left_col), pl.col(params.right_col)).alias(
            params.result_col
        )
    )

    try:
        lf.sink_parquet(params.result_parquet_file)
    except Exception as exc:
        logger.exception("Unable to perform operation", exc_info=exc)
        return False

    return True


class JoinParquetParams(BaseModel):
    """Parameters to join the dataframes from parquet files."""

    left_parquet: Path

    right_parquet: Path

    how: Literal["inner", "left", "right", "full", "semi", "anti", "cross"] = "inner"

    output_parquet: Path


@add_parameters(JoinParquetParams)
@no_submit_fn
def join_parquets(params: JoinParquetParams) -> bool:
    """Join two dataframes read from a parquet."""
    logger = logging.getLogger(__name__)

    logger.debug(
        "Joining parquets: %s + %s",
        params.left_parquet,
        params.right_parquet,
    )

    try:
        pl.scan_parquet(
            params.left_parquet,
        ).join(
            pl.scan_parquet(
                params.right_parquet,
            ),
            how=params.how,
        ).sink_parquet(params.output_parquet)
    except Exception as exc:
        logger.exception("Unable to join parquets!", exc_info=exc)
        return False

    return True
