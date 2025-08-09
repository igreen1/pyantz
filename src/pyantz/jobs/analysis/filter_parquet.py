"""Filter a parquet file based on a filters argument."""

import logging
import operator
import pathlib
from collections.abc import Callable
from functools import reduce
from typing import Literal

import polars as pl
from pydantic import BaseModel, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status

type FilterType = list[
    list[
        tuple[
            int | float | bool | str,
            Literal["==", "=", "!=", ">", ">=", "<", "<="],
            int | float | bool | str,
        ]
    ]
]


class Parameters(BaseModel, frozen=True):
    """Parameters for filter_parquet."""

    input_file: str
    output_file: str
    filters: list[list[list[str | bool | int | float]]]


class _RuntimeParameters(BaseModel, frozen=True):
    """Cant create json with tuples, but important for type checking internally."""

    input_file: FilePath
    output_file: str
    filters: FilterType


_operator_mapping: dict[str, Callable[..., bool]] = {
    "==": operator.eq,
    "=": operator.eq,
    "!=": operator.ne,
    "~=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    "<=": operator.le,
    ">=": operator.ge,
}


@config_base.simple_job(Parameters)
def filter_parquet(
    parameters: config_base.ParametersType,
    logger: logging.Logger,  # pylint: disable=unused-argument
) -> Status:
    """Filter the parquet file down."""
    params = _RuntimeParameters.model_validate(parameters)

    input_file_path = pathlib.Path(params.input_file)
    lazy_frame: pl.LazyFrame = pl.scan_parquet(input_file_path)  # pyright: ignore[reportUnknownMemberType] # pylint: disable=line-too-long
    columns: list[str] = lazy_frame.collect_schema().names()

    def get_as_col_if_possible[T](col_name: T) -> T | pl.Expr:
        return pl.col(col_name) if isinstance(col_name, str) and col_name in columns else col_name

    filters: bool | pl.Expr = reduce(
        operator.or_,
        [
            reduce(
                operator.and_,
                [
                    _operator_mapping[op](
                        get_as_col_if_possible(lhs),
                        get_as_col_if_possible(rhs),
                    )
                    for lhs, op, rhs in or_predicate
                ],
            )
            for or_predicate in params.filters
        ],
    )

    try:
        lazy_frame.filter(filters).sink_parquet(params.output_file)  # pyright: ignore[reportUnknownMemberType] # pylint: disable=line-too-long
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Unable to filter: ", exc_info=exc)
        return Status.ERROR
    return Status.SUCCESS
