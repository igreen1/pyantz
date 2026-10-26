"""Parameter validation performed when a config is first loaded.

:func:`check_config` decides whether to validate a job's parameters
against its registered Pydantic model at startup time (before any job
runs).  This is distinct from runtime validation, which happens inside
:func:`~pyantz.infrastructure.config.parameters.decorators.add_parameters`.

Startup checking is disabled by default to allow template variables to be
resolved at runtime; set ``strict: true`` on a job or
``check_at_startup: true`` on its decorator to force early validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config.variables import resolve_parameters

if TYPE_CHECKING:
    from pyantz.infrastructure.config import JobConfig, JobWithContext


def check_config(
    job_config: JobConfig,
    *,
    strict: bool = False,
    check_at_startup: bool = False,
) -> bool:
    """Enforce type checked parameters on the config.

    If variables in the job config (JobWithContext), it will resolve those first.
    The parameters are only checked if ``check_at_startup`` is set or the
    function was registered with ``check_at_startup=True``; otherwise they are
    checked when the job runs.

    Args:
        job_config: the job to check.
        strict: if True, the function must be registered with
            :func:`~pyantz.infrastructure.config.add_parameters`, and parameters
            with unresolved variables must already be valid.
        check_at_startup: if True, check the parameters now even if the function
            doesn't ask for it.

    Returns:
        bool: True if the job is acceptable, False if it isn't.

    Raises:
        ValueError: if resolving the variables finds a recursive reference.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig
            from pyantz.infrastructure.config.parameters.compile_check import (
                check_config,
            )

            job = JobConfig(function="pyantz.jobs.files.simple.copy", parameters={})
            print(check_config(job))  # checked when the job runs instead
            print(check_config(job, check_at_startup=True))  # src and dst missing

        .. testoutput::

            True
            False

    """
    if not hasattr(job_config.function, "PYANTZ_CHECKED"):
        # if strict and function isn't a pyantz checked, then we can't check
        # strict mode errors if we can't check
        return not strict

    if check_at_startup or (
        hasattr(job_config.function, "PYANTZ_CHECK_AT_STARTUP")
        and job_config.function.PYANTZ_CHECK_AT_STARTUP  # pyright: ignore[reportFunctionMemberAccess]
    ):
        return _check_params(job_config, strict=strict)

    return True


def get_params(job: JobConfig) -> type[BaseModel] | None:
    """Retrieve parameters attached to the job function, if any registered.

    Args:
        job: the job whose function to look at.

    Returns:
        type[BaseModel] | None: the parameters model the function was registered
        with by :func:`~pyantz.infrastructure.config.add_parameters`, or None.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig
            from pyantz.infrastructure.config.parameters import get_params

            job = JobConfig(
                function="pyantz.jobs.files.simple.copy",
                parameters={"src": "a", "dst": "b"},
            )
            print(get_params(job).__name__)

        .. testoutput::

            CopyParams

    """
    if hasattr(job.function, "PYANTZ_VALIDATION_MODEL"):
        return cast(
            "type[BaseModel]",
            job.function.PYANTZ_VALIDATION_MODEL,  # pyright: ignore[reportFunctionMemberAccess]
        )
    return None


def _check_params(job_config: JobConfig, *, strict: bool = False) -> bool:
    """Check the parameters of the job configuration.

    Args:
        job_config: the job to check; its variables, if any, are resolved first.
        strict: if True, parameters with unresolved variables must be valid too.

    Returns:
        bool: True if the parameters are valid, or (when not strict) invalid but
        holding variables which may be set later; False otherwise, including when
        the function has no parameters model.

    Raises:
        ValueError: if resolving the variables finds a recursive reference.

    """
    if (model := get_params(job_config)) is None:
        return False

    parameters = job_config.parameters
    unresolved_variables = False
    if hasattr(job_config, "variables"):
        job_config = cast("JobWithContext", job_config)
        if job_config.variables:
            parameters, unresolved_variables = resolve_parameters(
                parameters,
                job_config.variables,
            )

    try:
        model.model_validate(parameters)
    except ValidationError:
        # if strict is False and we have unresolved variables,
        # don't error because at runtime this could work
        # if the variable is dynamically set by another job
        # strict disallows depending on dynamic variables
        return not strict and unresolved_variables
    else:
        return True
