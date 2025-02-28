"""If then allows a user to insert an arbitrary function that returns a boolean

If that function returns True, then take path 1
If that function returns False, then take path 2
"""

import logging
from typing import Callable, Mapping

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See if then docstring"""

    function: Annotated[
        Callable[..., bool], BeforeValidator(config_base.get_function_by_name)
    ]
    args: list[config_base.PrimitiveType] | None
    if_true: config_base.PipelineConfig
    if_false: config_base.PipelineConfig


@config_base.submitter_job(Parameters)
def if_then(
    parameters: config_base.ParametersType,
    submit_fn: config_base.SubmitFunctionType,
    variables: Mapping[str, config_base.PrimitiveType],
    _pipeline_config: config_base.PipelineConfig,
    logger: logging.Logger,
) -> Status:
    """Branch execution based on the boolean output of a user-defined function

    ParametersType {
        function (str): resolvable path to a specific function, including all the modules to import
            for example, if you'd call `from cool.fun.module import my_func` then you'd write
            "function": "cool.fun.module.my_func"
        args: list of args that will be * expanded into the function
        if_true: pipeline to execute if the function returns True
        if_false: pipeline to execute if the function returns False
    }

    Args:
        parameters (ParametersType): see above
        submit_fn (SubmitFunctionType): function to submit the pipeline to for execution
        variables (Mapping[str, PrimitiveType]): variables from the outer context
        logger (logging.Logger): logger to assist with debugging

    Returns:
        Status: SUCCESS if job completed successfully
    """

    params_parsed = Parameters.model_validate(parameters)
    if params_parsed.function(
        *(params_parsed.args if params_parsed.args is not None else [])
    ):
        logger.debug("Function evaluated to true")
        submit_fn(
            config_base.Config.model_validate(
                {"variables": variables, "config": params_parsed.if_true}
            )
        )
    else:
        logger.debug("Function evaluated to false")
        submit_fn(
            config_base.Config.model_validate(
                {"variables": variables, "config": params_parsed.if_false}
            )
        )

    return Status.FINAL
