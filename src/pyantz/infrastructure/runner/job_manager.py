"""Run jobs."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.config.variables import resolve_parameters

if TYPE_CHECKING:
    from pyantz.infrastructure.config import JobConfig


type SubmissionFnWithParentType = Callable[
    [
        JobWithContext,
        str | uuid.UUID | None,
    ],
    None,
]


def run_job(
    job_config: JobWithContext,
    submitter_fn: SubmissionFnWithParentType,
) -> bool:
    """Run the provided job and resolve variables in its parameters."""
    logger = logging.getLogger(__name__)
    logger.debug("Starting running %s", job_config)

    # resolve parameters
    if job_config.variables:
        parameters, _unresolved_vars = resolve_parameters(
            job_parameters=job_config.parameters,
            variables=job_config.variables,
        )
    else:
        parameters = job_config.parameters
        logger.debug("No variables, parameters: %s", parameters)

    def _wrapped_submitter(to_submit: JobConfig) -> None:
        """Submit the job.

        1. Ensures the job is wrapped in parent variable context.
            User can submit with or without context
        2. Add the parent id for the submission to correctly inherit dependencies
        """
        # first, add context if not already present
        # if not present, variables set to None
        to_submit_with_context = JobWithContext.from_config(to_submit)

        # second, inherit parent variables but override if in to_submit
        to_submit_with_context = to_submit_with_context.model_copy(
            update={
                "variables": {
                    **(job_config.variables or {}),
                    **(
                        to_submit_with_context.variables or {}
                    ),
                },
            },
        )
        logger.debug("Submitting job with parent context: %s", to_submit_with_context)

        # now, submit with parent id from caller job
        submitter_fn(to_submit_with_context, job_config.job_id)

    try:
        logger.info("Running job %s", job_config.job_id)
        result = job_config.function(parameters, _wrapped_submitter)
        logger.debug("Job (%s) returned result %s", result, job_config.job_id)
    except Exception as exc:
        logger.exception(
            "Unexpected error while running job: %s",
            job_config.job_id,
            exc_info=exc,
        )
        return False
    return result
