"""For an input dataframe, filter based on a provided query"""

import logging
import os

import pandas as pd
from pydantic import BaseModel

from pyantz.infrastructure.config.base import *
from pyantz.infrastructure.core.status import Status


class FilterDataFrameParameters(BaseModel, frozen=True):
    """The parameters required for the filter dataframe command"""

    input_file: str
    query_string: str
    output_file: str | None
    captured_variables: Mapping[str, PrimitiveType] | None = None


@simple_job(FilterDataFrameParameters)
def filter_dataframe(parameters: ParametersType, logger: logging.Logger) -> Status:
    """Filter a dataframe based on a query

    ParametersType {
        input_file (str): parquet file to read and analyze
        query (str): query string to filter the dataframe
            see pandas.DataFrame.query for details
        output_file (str): path to save the filtered dataframe
    }


    Args:
        parameters (ParametersType): ParametersType for this function
        logger (logging.Logger): logger for this function

    Returns:
        Status: result of this job
    """

    if parameters is None:
        return Status.ERROR
    filter_parameters = FilterDataFrameParameters.model_validate(parameters)

    if not os.path.exists(filter_parameters.input_file):
        logger.error("Input file does not exist")
        return Status.ERROR

    data = pd.read_parquet(filter_parameters.input_file, dtype_backend="pyarrow")
    filtered_data = data.query(
        filter_parameters.query_string,
        local_dict=filter_parameters.captured_variables,
        global_dict={}
    )
    if filter_parameters.output_file is not None:
        filtered_data.to_parquet(filter_parameters.output_file)

    return Status.SUCCESS
