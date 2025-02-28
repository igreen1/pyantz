"""Parallel pipelines turns one pipeline into N pipelines

Users will specify the pipelines they'd like to occur as individual
    parameters, where the name of the pipeline is the key of the
    pipeline

For automagic expansion, look at "explode_pipelines" which will
    turn one template into a user-defined number of pipelines
    with a new variable to distinguish them

This function will run any number of entirely user defined pipelines
    with the same variables as the current context

"""

import logging
from typing import Mapping

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status
from pydantic import BaseModel


class ParallelPipelinesParameters(BaseModel, frozen=True):
    """See parallel pipelines docstring"""

    pipelines: list[config_base.PipelineConfig]


@config_base.submitter_job(ParallelPipelinesParameters)
def parallel_pipelines(
    parameters: config_base.ParametersType,
    submit_fn: config_base.SubmitFunctionType,
    variables: Mapping[str, config_base.PrimitiveType],
    _pipeline_config: config_base.PipelineConfig,
    logger: logging.Logger,
    **__,
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

    if parameters is None:
        logger.error("Parallel pipeline requires parameters")
        return Status.ERROR

    params_validated = ParallelPipelinesParameters.model_validate(parameters)

    logger.debug("Submitting %d new pipelines", len(params_validated.pipelines))

    for new_pipeline in params_validated.pipelines:
        submit_fn(
            config_base.Config.model_validate({"variables": variables, "config": new_pipeline})
        )

    return Status.FINAL
