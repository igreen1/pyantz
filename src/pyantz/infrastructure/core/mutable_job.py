"""Mutable jobs allow the function to edit the variables of the outer scope."""

# pylint: disable=duplicate-code

import logging
from collections.abc import Mapping
from copy import deepcopy

from pyantz.infrastructure.config.base import MutableJobConfig, PrimitiveType
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.variables import resolve_variables


def run_mutable_job(
    config: MutableJobConfig,
    variables: Mapping[str, PrimitiveType],
    logger: logging.Logger,
) -> tuple[Status, Mapping[str, PrimitiveType]]:
    """Run a job, which is the smallest atomic task of antz."""
    status: Status
    func_handle = config.function
    logger.debug("Running job %s, with func handle: %s", config.id, str(func_handle))

    params = resolve_variables(config.parameters, variables)
    logger.debug("Running function with parameters %s", str(params))

    try:
        ret_status, ret_vars = func_handle(params, deepcopy(variables), logger)
        if isinstance(ret_status, Status):  # pyright: ignore[reportUnnecessaryIsInstance]
            status = ret_status
        else:
            logger.warning("Return of function was not an ANTZ status, this is an automatic error")
            status = Status.ERROR  # bad return type is an error
    except Exception as exc:  # pylint: disable=broad-exception-caught # noqa: BLE001
        logger.warning("Unexpected error", exc_info=exc)
        return Status.ERROR, variables
    logger.debug("Finished job %s with status %s", config.id, str(status))

    if status == Status.ERROR:
        return status, variables
    return status, ret_vars
