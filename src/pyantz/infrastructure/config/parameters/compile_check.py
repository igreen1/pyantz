"""Perform the check at 'compile_time` aka when the config is loaded."""

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
    """
    if not hasattr(job_config.function, "PYANTZ_CHECKED"):
        # if strict and function isn't a pyantz checked, then we can't check
        # strict mode errors if we can't check
        return not strict

    if check_at_startup or (
        hasattr(job_config.function, "PYANTZ_CHECK_AT_STARTUP")
        and job_config.function.PYANTZ_CHECK_AT_STARTUP  # pyright: ignore[reportFunctionMemberAccess]
    ):
        return _check_params(job_config)

    return True


def get_params(job: JobConfig) -> type[BaseModel] | None:
    """Retrieve parameters attached to the job function, if any registered."""
    if hasattr(job.function, "PYANTZ_VALIDATION_MODEL"):
        return cast(
            "type[BaseModel]",
            job.function.PYANTZ_VALIDATION_MODEL,  # pyright: ignore[reportFunctionMemberAccess]
        )
    return None

def _check_params(job_config: JobConfig, *, strict: bool = False) -> bool:
    """Check the parameters of the job configuration."""
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
