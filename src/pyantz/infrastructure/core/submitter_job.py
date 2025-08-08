"""Submitter jobs are "final" jobs which will submit a new pipeline.

Unlike simple jobs, Submitter jobs have access to the outer scope, including
    variables and the parent pipeline configuration.

These types of jobs are much more powerful, allowing for the modification of the parent
    (eg., resetting the current stage) or dynamic variable updating

But, of course, they introduce all kinds of problems. For example, static checking
    to remove errors may not be possible if Submitter jobs are present.

Where possible, **avoid** Submitter jobs. Earlier versions removed them due to
    the danger posed by mutability

Submitter jobs have a few very important rules
-> Submitter jobs must ALSO be the very last job in a pipeline
"""

# pylint: disable=duplicate-code
import logging
from collections.abc import Callable, Mapping

from pyantz.infrastructure.config.base import (
    Config,
    PipelineConfig,
    PrimitiveType,
    SubmitterJobConfig,
)
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.variables import resolve_variables


def run_submitter_job(
    config: SubmitterJobConfig,
    variables: Mapping[str, PrimitiveType],
    submit_fn: Callable[[Config], None],
    pipeline_config: PipelineConfig,
    logger: logging.Logger,
) -> Status:
    """Run a job, which is the smallest atomic task of antz."""
    status: Status
    func_handle = config.function
    logger.debug("Running job %s, with func handle: %s", config.id, str(func_handle))

    params = resolve_variables(config.parameters, variables)
    logger.debug("Running function with parameters %s", str(params))

    try:
        ret = func_handle(params, submit_fn, variables, pipeline_config, logger)
        if isinstance(ret, Status):  # pyright: ignore[reportUnnecessaryIsInstance]
            status = ret
        else:
            logger.warning("Return of function was not an ANTZ status, this is an automatic error")
            status = Status.ERROR  # bad return type is an error
    except Exception as exc:  # pylint: disable=broad-exception-caught # noqa: BLE001
        logger.warning("Unexpected error", exc_info=exc)
        status = Status.ERROR
    logger.debug("Finished job %s with status %s", config.id, str(status))
    if status == Status.SUCCESS:
        logger.debug("Submitter success turned into FINAL. ALl Submitter jobs are FINAL")
        return Status.FINAL  # reroute success to final for all Submitter jobs
    return status
