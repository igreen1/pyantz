"""A pipeline is a set of tasks to perform in series."""

import logging
from collections.abc import Callable, Mapping

from pyantz.infrastructure.config.base import (
    Config,
    JobConfig,
    MutableJobConfig,
    PipelineConfig,
    PrimitiveType,
    SubmitterJobConfig,
)
from pyantz.infrastructure.core.job import run_job
from pyantz.infrastructure.core.mutable_job import run_mutable_job
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.submitter_job import run_submitter_job


def run_pipeline(
    config: PipelineConfig,
    variables: Mapping[str, PrimitiveType],
    submit_fn: Callable[[Config], None],
    logger: logging.Logger,
) -> Status:
    """Run the provided pipeline.

    Args:
        config (PipelineConfig): configuration of the pipeline to run
        variables (Mapping[str, PrimitiveType]): variables of the current scope
        submit_fn (Callable[[Config], None]):
            function to submit a next config to the runners
        logger (logging.Logger):
            logger of the current context


    Returns:
        Status: the status of the pipeline after executing the next job

    """
    logger.debug("Starting pipeline %s", config.id)

    if config.curr_stage < len(config.stages):
        # run the job
        curr_job = config.stages[config.curr_stage]

        ret_status, variables = _run_child_job(curr_job, config, variables, submit_fn, logger)

        # handle pipeline cleanup/termination
        if ret_status == Status.ERROR:
            logger.warning("Error in stage %d of pipeline %s", config.curr_stage, config.id)
            _restart(
                config, variables=variables, submit_fn=submit_fn, logger=logger
            )  # optionally restart if setup for that
        elif ret_status == Status.FINAL:
            # no need to do anthing, this pipeline is done
            if config.curr_stage + 1 < len(config.stages):
                logger.error(
                    "Pipeline has unconsumed jobs but the status is final. "
                    "Subsequent jobs WILL NOT EXECUTE"
                )
                return Status.ERROR
        elif ret_status == Status.SUCCESS:
            logger.debug("Success in pipeline %s", config.id)
            _success(config, variables=variables, submit_fn=submit_fn, logger=logger)
        else:
            logger.critical("Job failed to update status, still %s", ret_status)
            return Status.ERROR
        return ret_status

    return Status.ERROR


def _run_child_job(
    curr_job: JobConfig | MutableJobConfig | SubmitterJobConfig,
    pipeline_config: PipelineConfig,
    variables: Mapping[str, PrimitiveType],
    submit_fn: Callable[[Config], None],
    logger: logging.Logger,
) -> tuple[Status, Mapping[str, PrimitiveType]]:
    """Run the child job of a pipeline.

    Args:
        curr_job (JobConfig | MutableJobConfig | SubmitterJobConfig):
            the current job of this stage of the pipeline to run
        pipeline_config (PipelineConfig): configuration of the pipeline to run
        variables (Mapping[str, PrimitiveType]): variables of the current scope
        submit_fn (Callable[[Config], None]):
            function to submit a next config to the runners
        logger (logging.Logger):
            logger of the current context


    Returns:
        tuple[Status, Mapping[str, PrimitiveType]]:
            - Status of the child type returned
            - Updated variables (only changes for mutable types)

    """
    final_flag: bool = False

    logger.debug("Calling run_job %s", curr_job.id)
    if isinstance(curr_job, JobConfig):
        ret_status = run_job(
            curr_job,
            variables,
            logger,
        )
        if ret_status == Status.FINAL:
            logger.critical("Non submitter job returned final!")
            return Status.ERROR, variables
    elif isinstance(curr_job, SubmitterJobConfig):

        def submit_fn_flagged(config: Config) -> None:
            nonlocal final_flag
            final_flag = True
            return submit_fn(config)

        ret_status = run_submitter_job(
            curr_job,
            variables,
            submit_fn_flagged,
            pipeline_config,
            logger,
        )
    elif isinstance(curr_job, MutableJobConfig):  # pyright: ignore[reportUnnecessaryIsInstance]
        ret_status, new_vars = run_mutable_job(curr_job, variables, logger)
        if ret_status == Status.SUCCESS:
            variables = new_vars
    else:
        logger.critical("Unknown job type")
        return Status.ERROR, variables

    if final_flag and ret_status != Status.FINAL:
        logger.critical("Final Flag set but status is not final. Got %s", ret_status)
        return Status.ERROR, variables
    if not final_flag and ret_status == Status.FINAL:
        logger.error("Final flag is set but the final flag was not set. This is not normal")
    return ret_status, variables


def _success(
    config: PipelineConfig,
    variables: Mapping[str, PrimitiveType],
    submit_fn: Callable[[Config], None],
    logger: logging.Logger,
) -> None:
    """Resubmit this pipeline setup for the next job after a success."""
    logger.debug("Success in pipeline")
    next_config = config.model_dump()
    next_config["curr_stage"] += 1
    if next_config["curr_stage"] < len(next_config["stages"]):
        next_pipeline_config = PipelineConfig.model_validate(next_config)
        logger.debug("Submittig next pipeline stage: %d", next_pipeline_config.curr_stage)
        submit_fn(Config.model_validate({"variables": variables, "config": next_pipeline_config}))
    else:
        logger.debug("Pipeline %s completed successfully, exiting this execution line", config.id)


def _restart(
    config: PipelineConfig,
    variables: Mapping[str, PrimitiveType],
    submit_fn: Callable[[Config], None],
    logger: logging.Logger,
) -> None:
    """Restart the config provided by updating and submit to submitter."""
    if config.max_allowed_restarts == -1 or config.curr_restarts < config.max_allowed_restarts:
        logger.debug("Restarting pipeline after failure")
        new_config = config.model_dump()
        new_config["curr_restarts"] += 1
        new_config["curr_stage"] = 0
        new_config["status"] = Status.READY

        new_pipeline_config = PipelineConfig.model_validate(new_config)
        new_config_cls = Config(config=new_pipeline_config, variables=variables)
        logger.debug("Submitting restarted pipeline with id %s", new_config_cls.config.id)
        submit_fn(new_config_cls)
    else:
        logger.debug("Not restarting pipeline; max restarts exceeded")
