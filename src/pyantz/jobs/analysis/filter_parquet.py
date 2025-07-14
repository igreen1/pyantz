"""Filter a parquet file based on a filters argument"""

import logging
import operator
import os
from typing import Any, Callable, Literal, TypeAlias

import polars as pl
from pydantic import BaseModel, BeforeValidator, FilePath, field_validator
from typing_extensions import Annotated

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status

FilterType: TypeAlias = list[
    list[
        tuple[
            str,
            Literal["==", "=", "!=", ">", ">=", "<", "<="],
            int | float | bool | str,
        ]
    ]
]


class FilterParquetParameters(BaseModel, frozen=True):
    """Parameters for filter_parquet"""

    input_file: str
    output_file: str
    left: str
    op: Literal["==", "=", "~=", "!=", ">", ">=", "<", "<="]
    right: str | int | float | bool


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


class FilterParquetParametersAfter(BaseModel, frozen=True):
    """Parameters for filter_parquet"""

    input_file: FilePath
    output_file: Annotated[
        str,
        BeforeValidator(lambda x: x if os.path.exists(os.path.dirname(x)) else None),
    ]
    left: str | int | float | bool
    op: Callable[..., bool]
    right: str | int | float | bool

    @field_validator("op", mode="before")
    @classmethod
    def _op_transform(cls, value: Any) -> Any:
        """Transfor operator if its a string"""
        if isinstance(value, str):
            return _operator_mapping.get(value, value)
        return value


@config_base.simple_job(FilterParquetParameters)
def filter_parquet(
    parameters: config_base.ParametersType, logger: logging.Logger
) -> Status:
    """Filter the parquet file down"""

    params = FilterParquetParametersAfter.model_validate(parameters)

    lazy_frame = pl.scan_parquet(params.input_file)

    columns: list[str] = lazy_frame.collect_schema().names()

    lhs = (
        pl.col(params.left)
        if isinstance(params.left, str) and params.left in columns
        else params.left
    )
    rhs = (
        pl.col(params.right)
        if isinstance(params.right, str) and params.right in columns
        else params.right
    )

    pl.scan_parquet(params.input_file).filter(params.op(lhs, rhs)).sink_parquet(
        params.output_file
    )

    return Status.SUCCESS
