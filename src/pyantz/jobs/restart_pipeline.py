"""Restarts the parent pipeline"""

import logging
import operator
from typing import Any, Callable, Literal, Mapping

from pydantic import BaseModel

from pyantz.infrastructure.config.base import *
from pyantz.infrastructure.core.status import Status

comparators: dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


class Parameters(BaseModel, frozen=True):
    """Provides optional configuration of the restart pipeline job"""

    comparator: Literal["<", ">", "<=", ">=", "==", "!="] | None = None
    left: PrimitiveType | None = None
    right: PrimitiveType | None = None


@submitter_job(Parameters)
def restart_pipeline(
    parameters: ParametersType,
    submit_fn: SubmitFunctionType,
    variables: Mapping[str, PrimitiveType],
    pipeline_config: PipelineConfig,
    logger: logging.Logger,
) -> Status:
    """Create a series of parallel pipelines based on user input

    Args:
        parameters (ParametersType): mapping of string names of pipelines to pipeline configurations
        submit_fn (SubmitFunctionType): function to submit the pipeline to for execution
        variables (Mapping[str, PrimitiveType]): variables from the outer context
        logger (logging.Logger): logger to assist with debugging

    Returns:
        Status: SUCCESS if jobs successfully submitted; ERROR otherwise
    """

    if parameters != {}:
        params_parsed = Parameters.model_validate(parameters)
        if (
            params_parsed.comparator is None
            or params_parsed.left is None
            or params_parsed.right is None
        ):
            raise RuntimeError("Invalid parameters for restart pipeline")
        result = comparators[params_parsed.comparator](
            params_parsed.left, params_parsed.right
        )
        if not result:
            return (
                Status.FINAL
            )  # final even if doesn't submit because it **could** submit

    logger.debug("Restarting pipeline %s", pipeline_config.id)
    new_pipeline = pipeline_config.model_dump()
    new_pipeline["curr_stage"] = 0

    submit_fn(Config.model_validate({"variables": variables, "config": new_pipeline}))
    return Status.FINAL
