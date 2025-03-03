"""Given a template pipeline, create N new pipelines from that template
with a new variables PIPELINE_ID set to a counter


"""

import logging
from collections.abc import Mapping

from pydantic import BaseModel, PositiveInt

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """See explode pipeline docs"""

    num_pipelines: PositiveInt
    pipeline_config_template: config_base.PipelineConfig


@config_base.submitter_job(Parameters)
def explode_pipeline(
    parameters: config_base.ParametersType,
    submit_fn: config_base.SubmitFunctionType,
    variables: Mapping[str, config_base.PrimitiveType],
    _pipeline_config: config_base.PipelineConfig,
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

    params_parsed = Parameters.model_validate(parameters)

    logger.debug("Exploding pipelines into %d pipelines", params_parsed.num_pipelines)

    for i in range(params_parsed.num_pipelines):
        submit_fn(
            config_base.Config.model_validate(
                {
                    "variables": {**variables, "PIPELINE_ID": i},
                    "config": params_parsed.pipeline_config_template,
                }
            )
        )

    return Status.FINAL
