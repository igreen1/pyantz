"""Simple columnar operations on Parquet data files.

:func:`columnar_operation` applies an arithmetic operation between two
columns and stores the result in a new column.

:func:`join_parquets` performs a Polars join between two Parquet files and
writes the output to a third file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Self

import polars as pl
from pydantic import BaseModel, ConfigDict, model_validator

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class ColumnarOperationParameters(BaseModel):
    """Perform an operation and save the resulting dataframe in a parquet."""

    model_config = ConfigDict(frozen=True)

    source_parquet_file: Path
    """Parquet file to read dataframe from for these operations."""

    result_parquet_file: str
    """Location to save the results after performing the operation."""

    left_col: str
    """Column on the left side of the expression."""

    right_col: str
    """Column on the right side of the expression."""

    result_col: str
    """Column to save the results."""

    operation: Literal[
        "+",
        "-",
        "*",
        "/",
    ]
    """Operation to be performed between the two columns."""


OP_MAPPING = {
    "+": pl.Expr.add,
    "-": pl.Expr.sub,
    "/": pl.Expr.truediv,
    "*": pl.Expr.mul,
}
"""Polars expression method for each operation of :func:`columnar_operation`."""


@add_parameters(ColumnarOperationParameters)
@no_submit_fn
def columnar_operation(params: ColumnarOperationParameters) -> bool:
    """Perform a simple operation between two columns.

    The source parquet is read lazily, the result of ``left_col <operation>
    right_col`` is added as ``result_col``, and the dataframe with the new column
    is written to ``result_parquet_file``.

    Args:
        params: the job's parameters, validated as
            :class:`ColumnarOperationParameters`.

    Parameters:
        source_parquet_file (Path): parquet file to read the dataframe from.
        result_parquet_file (str): parquet file to write the result to.
        left_col (str): column on the left side of the expression.
        right_col (str): column on the right side of the expression.
        result_col (str): column to save the results in.
        operation (str): ``+``, ``-``, ``*`` or ``/``.

    Returns:
        bool: True if the result was written, False if the source doesn't exist,
        lacks a column, or can't be read or written.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: analysis-columnar

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

            import polars as pl
            pl.DataFrame({
                "a": [1, 2],
                "b": [3, 4],
            }).write_parquet("test_input.parquet")

        .. testcode:: analysis-columnar

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

        .. testoutput:: analysis-columnar

            shape: (2, 3)
            ┌─────┬─────┬─────┐
            │ a   ┆ b   ┆ c   │
            │ --- ┆ --- ┆ --- │
            │ i64 ┆ i64 ┆ i64 │
            ╞═════╪═════╪═════╡
            │ 1   ┆ 3   ┆ 4   │
            │ 2   ┆ 4   ┆ 6   │
            └─────┴─────┴─────┘

        .. testcleanup:: analysis-columnar

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)

    logger.debug("Starting columnar operation %s", params.operation)

    if not params.source_parquet_file.exists():
        logger.error(
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

    model_config = ConfigDict(frozen=True)

    left_parquet: Path
    """Parquet with tabular data to join, on the left of the join operation."""

    right_parquet: Path
    """Parquet with tabular data to join, on the right of the join operation."""

    how: Literal["inner", "left", "right", "full", "semi", "anti", "cross"] = "inner"
    """Supported styles of joins (see polars docs for details)."""

    output_parquet: Path
    """Parquet file to save the results, cannot be the same as left/right."""

    on_: str
    """Column name to join on."""

    @model_validator(mode="after")
    def check_file_paths(self) -> Self:
        """Check that output is not the same as the input file.

        Args:
            None.

        Returns:
            Self: the validated parameters.

        Raises:
            ValueError: if the output parquet is the left or right parquet.

        """
        msg = "Input cannot be the same as output files."
        if self.output_parquet.resolve() == self.left_parquet.resolve():
            raise ValueError(msg)
        if self.output_parquet.resolve() == self.right_parquet.resolve():
            raise ValueError(msg)
        return self


@add_parameters(JoinParquetParams)
@no_submit_fn
def join_parquets(params: JoinParquetParams) -> bool:
    """Join two dataframes read from a parquet.

    The parquets are read lazily and the joined dataframe is streamed into the
    output parquet. A join doesn't keep the order of the rows.

    Args:
        params: the job's parameters, validated as :class:`JoinParquetParams`.

    Parameters:
        left_parquet (Path): parquet on the left of the join.
        right_parquet (Path): parquet on the right of the join.
        how (str): style of join, one of ``inner``, ``left``, ``right``,
            ``full``, ``semi``, ``anti`` or ``cross`` (see polars' docs). Defaults
            to ``inner``.
        output_parquet (Path): parquet to save the result to; it can't be the left
            or right parquet.
        on_ (str): name of the column to join on.

    Returns:
        bool: True if the result was written, False if the join fails (for
        example, a parquet or column doesn't exist).

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: analysis-join

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

            import polars as pl
            pl.DataFrame(
                {
                    "idx": [1, 2, 3, 4, 5],
                    "a": [10, 11, 12, 13, 14],
                }
            ).write_parquet("left.parquet")
            pl.DataFrame(
                {
                    "idx": [1, 4],
                    "b": ["hello", "world"],
                }
            ).write_parquet("right.parquet")

        .. testcode:: analysis-join

            from pyantz import start
            config = {
                "jobs": [
                    {
                        "function": "pyantz.jobs.analysis.simple.join_parquets",
                        "parameters": {
                            "left_parquet": "left.parquet",
                            "right_parquet": "right.parquet",
                            "how": "inner",
                            "output_parquet": "output.parquet",
                            "on_": "idx",
                        },
                    }
                ],
                "submitter": {
                    "type_": "local_proc",
                    "working_directory": ".",
                },
            }
            start(config)

            # a join doesn't keep the order of the rows
            result = pl.read_parquet("output.parquet").sort("idx")
            print(result)

        .. testoutput:: analysis-join

            shape: (2, 3)
            ┌─────┬─────┬───────┐
            │ idx ┆ a   ┆ b     │
            │ --- ┆ --- ┆ ---   │
            │ i64 ┆ i64 ┆ str   │
            ╞═════╪═════╪═══════╡
            │ 1   ┆ 10  ┆ hello │
            │ 4   ┆ 13  ┆ world │
            └─────┴─────┴───────┘

        .. testcleanup:: analysis-join

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
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
            on=params.on_,
        ).sink_parquet(params.output_parquet)
    except Exception as exc:
        logger.exception("Unable to join parquets!", exc_info=exc)
        return False

    return True
