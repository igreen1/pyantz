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

    #: Parquet file to read dataframe from for these operations
    source_parquet_file: FilePath

    #: Location to save the results after performing the operation
    result_parquet_file: str

    #: Column on the left side of the expression
    left_col: str

    #: Column on the right side of the expression
    right_col: str

    #: Column to save the results
    result_col: str

    #: Operation to be performed between the two columns
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
    """Perform a simple operation between two columns.

    :Example:

    .. testsetup::

        import os
        import polars as pl
        pl.DataFrame({
            "a": [1, 2],
            "b": [3, 4],
        }).write_parquet("test_input.parquet")


    .. testcode::

        import os

        import polars as pl

        from pyantz.jobs.analysis.simple import columnar_operation


        assert os.path.exists("test_input.parquet")
        columnar_operation({
            "source_parquet_file": "test_input.parquet",
            "result_parquet_file": "test_output.parquet",
            "left_col": "a",
            "right_col": "b",
            "result_col": "c",
            "operation": "+",
        }, lambda *_: None)

        result = pl.read_parquet("test_output.parquet")
        print(result)

    Output:

    .. testoutput::

        shape: (2, 3)
        ┌─────┬─────┬─────┐
        │ a   ┆ b   ┆ c   │
        │ --- ┆ --- ┆ --- │
        │ i64 ┆ i64 ┆ i64 │
        ╞═════╪═════╪═════╡
        │ 1   ┆ 3   ┆ 4   │
        │ 2   ┆ 4   ┆ 6   │
        └─────┴─────┴─────┘

    .. testcleanup::

        import os
        if os.path.exists("test_output.parquet"):
            os.remove("test_output.parquet")
        if os.path.exists("test_input.parquet"):
            os.remove("test_input.parquet")

    """
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
