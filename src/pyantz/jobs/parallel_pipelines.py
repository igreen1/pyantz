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
from typing import Mapping, TypeAlias

from pyantz.infrastructure.config.base import (
    Config,
    ParametersType,
    PipelineConfig,
    PrimitiveType,
    SubmitFunctionType,
)
from pyantz.infrastructure.config.job_decorators import submitter_job
from pyantz.infrastructure.core.status import Status

ParallelPipelinesParametersType: TypeAlias = list[PipelineConfig]


@submitter_job
def parallel_pipelines(
    parameters: ParametersType,
    submit_fn: SubmitFunctionType,
    variables: Mapping[str, PrimitiveType],
    _pipeline_config: PipelineConfig,
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

    params_validated = [
        PipelineConfig.model_validate({"name": key, **value.model_dump()})
        for key, value in parameters.items()
        if isinstance(value, PipelineConfig)
    ]

    if len(params_validated) != len(parameters):
        logger.error(
            "One of the passed parameters in parallel pipelines is not a pipeline config"
        )
        return Status.ERROR

    logger.debug("Submitting %d new pipelines", len(params_validated))

    for new_pipeline in params_validated:
        submit_fn(
            Config.model_validate({"variables": variables, "config": new_pipeline})
        )

    return Status.FINAL
