"""Run jobs.

The runners call :func:`run_job_with_details` (or :func:`run_job`) for each job
they take from their queue. It fills in the job's variables, makes them available
to the job through :data:`JobVariables`, and gives the job a submit function which
passes on its variables and its id to the jobs it submits.
"""

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
"""Function a runner provides to submit a job along with the id of its parent."""

JobVariables = ContextVar[None | Mapping[str, Any]]("JobVariables", default=None)
"""The variables of the job which is running; jobs which run other jobs (like
:func:`~pyantz.jobs.wrappers.loops.local_for_loop`) read it to pass them on."""


class JobResult(NamedTuple):
    """Outcome of running a job."""

    success: bool
    """Did the job succeed?"""

    details: str | None = None
    """For failures, why (e.g., the exception raised)."""


def run_job(
    job_config: JobWithContext,
    submitter_fn: SubmissionFnWithParentType,
) -> bool:
    """Run the provided job and resolve variables in its parameters.

    Args:
        job_config: the job to run, with its variables.
        submitter_fn: function to submit the job's jobs with, given each job and
            the id of this job.

    Returns:
        bool: True if the job succeeded.

    Raises:
        None: failures of the job are reported by returning False.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobWithContext
            from pyantz.infrastructure.runner.job_manager import run_job

            job = JobWithContext(
                function="pyantz.jobs.branching.if_else.conditionally_execute",
                parameters={
                    "left_side": "%{count}",
                    "comparator": ">",
                    "right_side": 2,
                    "if_true": {
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                    },
                },
                variables={"count": 3},
            )
            submitted = []
            print(run_job(job, lambda child, parent: submitted.append(child)))
            print(submitted[0].variables)

        .. testoutput::

            True
            {'count': 3}

    """
    return run_job_with_details(job_config, submitter_fn).success


def run_job_with_details(
    job_config: JobWithContext,
    submitter_fn: SubmissionFnWithParentType,
) -> JobResult:
    """Run the provided job, resolve its variables, and say why it failed if so.

    Jobs the job submits inherit its variables (their own take precedence) and
    are passed to ``submitter_fn`` with the id of this job as their parent.

    Args:
        job_config: the job to run, with its variables.
        submitter_fn: function to submit the job's jobs with, given each job and
            the id of this job.

    Returns:
        JobResult: whether the job succeeded and, if not, why.

    Raises:
        None: failures of the job are reported in the result.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobWithContext
            from pyantz.infrastructure.runner.job_manager import run_job_with_details

            job = JobWithContext(
                function="pyantz.jobs.files.simple.copy",
                parameters={"src": "no_such_file.txt", "dst": "copy.txt"},
            )
            result = run_job_with_details(job, lambda child, parent: None)
            print(result.success, result.details.split(":")[0])

        .. testoutput::

            False FileNotFoundError

    """
    logger = logging.getLogger(__name__)

    def _wrapped_submitter(to_submit: JobConfig) -> None:
        """Submit the job.

        1. Ensures the job is wrapped in parent variable context.
            User can submit with or without context
        2. Add the parent id for the submission to correctly inherit dependencies

        Args:
            to_submit: the job to submit.

        Returns:
            None.

        Raises:
            Exception: anything raised by ``submitter_fn``, e.g., when the job
                can't be added to the queue.

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
    """Run the provided job and resolve variables in its parameters.

    Unlike :func:`run_job`, the jobs submitted by the job are passed to
    ``wrapped_submit_fn`` as they are, without this job's variables or id; used
    by jobs which run other jobs within themselves.

    Args:
        job_config: the job to run, with its variables.
        wrapped_submit_fn: function to submit the job's jobs with.

    Returns:
        bool: True if the job succeeded.

    Raises:
        None: failures of the job are reported by returning False.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobWithContext
            from pyantz.infrastructure.runner.job_manager import (
                run_job_no_parent_wrapper,
            )

            job = JobWithContext(
                function="pyantz.jobs.testing.nop.do_nothing", parameters={}
            )
            print(run_job_no_parent_wrapper(job, lambda child: None))

        .. testoutput::

            did nothing :)
            True

    """
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

    Args:
        job_config: the job to run, with its variables.
        wrapped_submit_fn: function to submit the job's jobs with.

    Returns:
        JobResult: whether the job succeeded and, if not, why (including a
        recursive reference among its variables).

    Raises:
        None: failures of the job are reported in the result.

    """
    logger = logging.getLogger(__name__)
    logger.debug("Starting running %s", job_config)

    def _resolve_parameters() -> Mapping[str, Any]:
        """Fill in the variables in the job's parameters.

        Args:
            None.

        Returns:
            Mapping[str, Any]: the parameters with their variables filled in.

        Raises:
            ValueError: if resolving the variables finds a recursive reference.

        """
        if not job_config.variables:
            logger.debug("No variables, parameters: %s", job_config.parameters)
            return job_config.parameters
        parameters, _unresolved_vars = resolve_parameters(
            job_parameters=job_config.parameters,
            variables=job_config.variables,
        )
        return parameters

    def _validate_job() -> None:
        """Validate that the job is not virtual.

        Args:
            None.

        Returns:
            None.

        Raises:
            RuntimeError: if the job is virtual (virtual jobs never run).

        """
        if job_config.virtual:
            msg = "Virtual job being run"
            raise RuntimeError(msg)

    try:
        _validate_job()
        parameters = _resolve_parameters()
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
