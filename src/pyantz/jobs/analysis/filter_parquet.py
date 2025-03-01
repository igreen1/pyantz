"""Filter a parquet file based on a filters argument"""

import logging
import os

import pyarrow.parquet
from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class FilterParquetParameters(BaseModel, frozen=True):
    """Parameters for filter_parquet"""

    input_file: Annotated[
        str, BeforeValidator(lambda x: x if os.path.exists(x) else None)
    ]
    output_file: Annotated[
        str,
        BeforeValidator(lambda x: x if os.path.exists(os.path.dirname(x)) else None),
    ]
    filters: list[config_base.PrimitiveType]  # Todo: lengths % 3 = 0


@config_base.simple_job(FilterParquetParameters)
def filter_parquet(
    parameters: config_base.ParametersType, logger: logging.Logger
) -> Status:
    """Filter the parquet file down"""

    params = FilterParquetParameters.model_validate(parameters)

    if len(params.filters) % 3 != 0:
        logger.error('Filters should be a flat list of tuples. Got non-trio data %s', params.filters)
        raise ValueError("Length of filters should be a multiple of three")

    if len(params.filters) > 0:
        filters = [
            [
                (params.filters[i], params.filters[i + 1], params.filters[i + 2])
                for i in range(0, len(params.filters), 3)
            ]
        ]
    else:
        filters = None

    table = pyarrow.parquet.read_table(params.input_file, filters=filters)

    pyarrow.parquet.write_table(table, params.output_file)

    return Status.SUCCESS
