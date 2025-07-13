"""Assign an environment variable"""

import logging
import os

from pydantic import BaseModel

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See change variable docs"""

    environmental_variables: dict[str, str]


@config_base.simple_job(Parameters)
def assign_environment_variable(
    parameters: config_base.ParametersType,
    logger: logging.Logger, # pylint: disable=unused-argument
) -> Status:
    """Change a variable to a new value based on a function return

    ChangeVariableParameters {
        environmental_variables: {
            "variable_name": "variable_value"
        }
    }

    Args:
        parameters (ParametersType): see above
        logger (logging.Logger): logger to assist with debugging


    Returns:
        Status: SUCCESS if jobs successfully submitted; ERROR otherwise
    """

    params_parsed = Parameters.model_validate(parameters)

    for var_name, var_values in params_parsed.environmental_variables.items():
        os.environ[var_name] = var_values
    return Status.SUCCESS
