"""Filter a parquet file based on a filters argument"""

import logging
import os
from typing import Literal, TypeAlias

import pyarrow.parquet
from pydantic import BaseModel, BeforeValidator
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

    input_file: Annotated[
        str, BeforeValidator(lambda x: x if os.path.exists(x) else None)
    ]
    output_file: Annotated[
        str,
        BeforeValidator(lambda x: x if os.path.exists(os.path.dirname(x)) else None),
    ]
    left: str
    op: Literal["==", "=", "!=", ">", ">=", "<", "<="]
    right: str | int | float | bool


@config_base.simple_job(FilterParquetParameters)
def filter_parquet(
    parameters: config_base.ParametersType, logger: logging.Logger
) -> Status:
    """Filter the parquet file down"""

    params = FilterParquetParameters.model_validate(parameters)

    filters = [[(params.left, params.op, params.right)]]

    logger.debug("Reading %s with filters %s", params.input_file, filters)

    # adding type ignore because the liskov logic here is wrong
    table = pyarrow.parquet.read_table(params.input_file, filters=filters)  # type: ignore

    pyarrow.parquet.write_table(table, params.output_file)

    return Status.SUCCESS
