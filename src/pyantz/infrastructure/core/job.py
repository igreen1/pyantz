"""A job is the basic unit of execution in this module

Each job performs one user-assigned task and returns its state.
"""

# pylint: disable=duplicate-code

import logging
from typing import Mapping

from pyantz.infrastructure.config.base import JobConfig, PrimitiveType
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.variables import resolve_variables


def run_job(
    config: JobConfig,
    variables: Mapping[str, PrimitiveType],
    logger: logging.Logger,
) -> Status:
    """Run a job, which is the smallest atomic task of antz"""
    status: Status
    func_handle = config.function
    logger.debug("Running job %s, with func handle: %s", config.id, str(func_handle))

    params = resolve_variables(config.parameters, variables)
    logger.debug("Running function with parameters %s", str(params))

    try:
        ret = func_handle(params, logger)
        if isinstance(ret, Status):
            status = ret
        else:
            logger.warning(
                "Return of function was not an ANTZ status, this is an automatic error"
            )
            status = Status.ERROR  # bad return type is an error
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Unexpected error", exc_info=exc)
        status = Status.ERROR
    logger.debug("Finished job %s with status %s", config.id, str(status))
    return status
