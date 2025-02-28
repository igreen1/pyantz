"""Asserts that a variable is of a certain value"""

import logging

from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See assert_variable docstring"""

    given_val: config_base.PrimitiveType
    expected_value: config_base.PrimitiveType


@config_base.simple_job(Parameters)
def assert_value(
    parameters: config_base.ParametersType, logger: logging.Logger
) -> Status:
    """Return ERROR if the variable doesn't match expectations

    Parameters {
        var_to_check (str): name of the variable to check
        expected_value (PrimitiveType): expected value of the variable
    }

    Args:
        parameters (ParametersType): see above
        submit_fn (SubmitFunctionType): function to submit the pipeline to for execution
        variables (Mapping[str, PrimitiveType]): variables from the outer context
        logger (logging.Logger): logger to assist with debugging

    Returns:
        Status: SUCCESS if the variable matches expected value; ERROR otherwise
    """

    params_parsed = Parameters.model_validate(parameters)

    if params_parsed.given_val == params_parsed.expected_value:
        logger.debug("Assert resulted in true")
        return Status.SUCCESS
    logger.debug("Assert resulted in false")
    return Status.ERROR
