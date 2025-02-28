"""Call a user provided function and set the value of a variable to the return"""

import logging
from typing import Callable, Mapping

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See change variable docs"""

    left_hand_side: str
    args: list[config_base.PrimitiveType] | None
    right_hand_side: Annotated[
        Callable[..., config_base.PrimitiveType],
        BeforeValidator(config_base.get_function_by_name),
    ]


@config_base.mutable_job(Parameters)
def set_variable_from_function(
    parameters: config_base.ParametersType,
    variables: Mapping[str, config_base.PrimitiveType],
    logger: logging.Logger,
) -> tuple[Status, Mapping[str, config_base.PrimitiveType]]:
    """Change a variable to a new value based on a function return

    ChangeVariableParameters {
        left_hand_side (str): name of the variable to change (left of equal sign)
        right_hand_side (str): resolvable path to a specific function,
            including all the modules to import
            for example, if you'd call `from cool.fun.module import my_func` then you'd write
            "function": "cool.fun.module.my_func"
        args: list of args that will be * expanded into the function
    }

    Args:
        parameters (ParametersType): see above
        submit_fn (SubmitFunctionType): function to submit the pipeline to for execution
        variables (Mapping[str, PrimitiveType]): variables from the outer context
        logger (logging.Logger): logger to assist with debugging


    Returns:
        Status: SUCCESS if jobs successfully submitted; ERROR otherwise
    """

    params_parsed = Parameters.model_validate(parameters)

    result = params_parsed.right_hand_side(
        *(params_parsed.args if params_parsed.args is not None else [])
    )
    logger.debug("Changing variable %s to %s", params_parsed.left_hand_side, result)

    new_vars = {**variables, params_parsed.left_hand_side: result}
    return Status.SUCCESS, new_vars
