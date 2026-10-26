"""Run jobs."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, NamedTuple

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.config.variables import resolve_parameters

if TYPE_CHECKING:
    from pyantz.infrastructure.config import JobConfig, SubmissionFnType

type SubmissionFnWithParentType = Callable[
    [
        JobWithContext,
        str | uuid.UUID | None,
    ],
    None,
]

JobVariables = ContextVar[None | Mapping[str, Any]]("JobVariables", default=None)


class JobResult(NamedTuple):
    """Outcome of running a job."""

    # did the job succeed?
    success: bool

    # for failures, why (e.g., the exception raised)
    details: str | None = None


def run_job(
    job_config: JobWithContext,
    submitter_fn: SubmissionFnWithParentType,
) -> bool:
    """Run the provided job and resolve variables in its parameters."""
    return run_job_with_details(job_config, submitter_fn).success


def run_job_with_details(
    job_config: JobWithContext,
    submitter_fn: SubmissionFnWithParentType,
) -> JobResult:
    """Run the provided job, resolve its variables, and say why it failed if so."""
    logger = logging.getLogger(__name__)

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
                    **(to_submit_with_context.variables or {}),
                },
            },
        )
        logger.debug("Submitting job with parent context: %s", to_submit_with_context)

        # now, submit with parent id from caller job
        submitter_fn(to_submit_with_context, job_config.job_id)

    return _run_job_no_parent_wrapper_with_details(
        job_config=job_config,
        wrapped_submit_fn=_wrapped_submitter,
    )


def run_job_no_parent_wrapper(
    job_config: JobWithContext,
    wrapped_submit_fn: SubmissionFnType,
) -> bool:
    """Run the provided job and resolve variables in its parameters."""
    return _run_job_no_parent_wrapper_with_details(
        job_config,
        wrapped_submit_fn,
    ).success


def _run_job_no_parent_wrapper_with_details(
    job_config: JobWithContext,
    wrapped_submit_fn: SubmissionFnType,
) -> JobResult:
    """Run the provided job and resolve variables in its parameters.

    A job function reports failure by returning False or by raising an exception.
    Returning None (as plain python functions often do) counts as success, and any
    other non-bool result is judged by its truthiness; both log a warning.
    """
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

    def _validate_job() -> None:
        """Validate that the job is not virtual."""
        if job_config.virtual:
            msg = "Virtual job being run"
            raise RuntimeError(msg)

    try:
        _validate_job()
        logger.info("Running job %s", job_config.job_id)
        token = JobVariables.set(job_config.variables)
        try:
            result = job_config.function(parameters, wrapped_submit_fn)
        finally:
            JobVariables.reset(token)
        logger.debug("Job (%s) returned result %s", job_config.job_id, result)
    except Exception as exc:
        logger.exception(
            "Unexpected error while running job: %s",
            job_config.job_id,
            exc_info=exc,
        )
        return JobResult(success=False, details=f"{type(exc).__name__}: {exc}")
    if result is None:
        logger.warning(
            "Job %s returned None instead of a bool; treating it as success",
            job_config.job_id,
        )
        return JobResult(success=True)
    if not isinstance(result, bool):
        logger.warning(
            "Job %s returned %r instead of a bool; using its truthiness",
            job_config.job_id,
            result,
        )
    if not result:
        return JobResult(success=False, details="Job returned a falsy result")
    return JobResult(success=True)
