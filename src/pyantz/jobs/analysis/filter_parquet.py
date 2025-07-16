"""Filter a parquet file based on a filters argument"""

import logging
import operator

from typing import Callable, Literal, TypeAlias
from functools import reduce
import operator

import polars as pl
from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status

FilterType: TypeAlias = list[
    list[
        tuple[
            int | float | bool | str,
            Literal["==", "=", "!=", ">", ">=", "<", "<="],
            int | float | bool | str,
        ]
    ]
]

FilterTypeAfter: TypeAlias = list[
    list[
        tuple[
            int | float | bool | str | pl.Expr,
            Callable[..., bool],
            int | float | bool | str | pl.Expr,
        ]
    ]
]


class FilterParquetParameters(BaseModel, frozen=True):
    """Parameters for filter_parquet"""

    input_file: str
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


@config_base.simple_job(FilterParquetParameters)
def filter_parquet(
    parameters: config_base.ParametersType,
    logger: logging.Logger,  # pylint: disable=unused-argument
) -> Status:
    """Filter the parquet file down"""

    params = FilterParquetParameters.model_validate(parameters)

    lazy_frame = pl.scan_parquet(params.input_file)
    columns: list[str] = lazy_frame.collect_schema().names()

    def get_as_col_if_possible[T](col_name: T) -> T | pl.Expr:
        return (
            pl.col(col_name)
            if isinstance(col_name, str) and col_name in columns
            else col_name
        )

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
        lazy_frame.filter(filters).sink_parquet(
            params.output_file
        )
    except Exception as exc:
        logger.error('Unable to filter: ', exc_info=exc)
        return Status.ERROR
    return Status.SUCCESS
