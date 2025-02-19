"""If then allows a user to insert an arbitrary function that returns a boolean

If that function returns True, then take path 1
If that function returns False, then take path 2
"""

import logging
from typing import Callable, Mapping

from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated

from pyantz.infrastructure.config.base import (
    Config,
    ParametersType,
    PipelineConfig,
    PrimitiveType,
    SubmitFunctionType,
    get_function_by_name,
    submitter_job,
)
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See if then docstring"""

    function: Annotated[Callable[..., bool], BeforeValidator(get_function_by_name)]
    args: list[PrimitiveType] | None
    if_true: PipelineConfig
    if_false: PipelineConfig


@submitter_job
def if_then(
    parameters: ParametersType,
    submit_fn: SubmitFunctionType,
    variables: Mapping[str, PrimitiveType],
    _pipeline_config: PipelineConfig,
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
            Config.model_validate(
                {"variables": variables, "config": params_parsed.if_true}
            )
        )
    else:
        logger.debug("Function evaluated to false")
        submit_fn(
            Config.model_validate(
                {"variables": variables, "config": params_parsed.if_false}
            )
        )

    return Status.FINAL
