"""Decorate functions and strongly enforce parameter types."""

from __future__ import annotations

import logging
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel

from pyantz.infrastructure.config.fn_utils import serialize_function

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

    from pyantz.infrastructure.config.job import (
        JobConfig,
        JobFunctionType,
        ParametersType,
        SubmissionFnType,
    )

PYANTZ_REGISTERED_FUNCTION: Final[list[JobFunctionType]] = []

VIRTUAL_MARKER: Final[str] = "__PYANTZ_VIRTUAL__"


def no_submit_fn[T: (BaseModel | ParametersType)](
    fn: Callable[[T], bool],
) -> Callable[[T, SubmissionFnType], bool]:
    """Wrap a function that doesn't want submit function."""

    @wraps(fn)
    def _ignore_submitter(params: T, _submit_fn: SubmissionFnType) -> bool:
        """Wrap the function to allow the caller to pass submit function."""
        return fn(params)

    return _ignore_submitter


def get_registered_functions(fn_name: str | None = None) -> list[JobFunctionType]:
    """Get all the functions which have used the `add_parameters` decorator."""
    if fn_name is None:
        return PYANTZ_REGISTERED_FUNCTION
    for fn in PYANTZ_REGISTERED_FUNCTION:
        registered_name = fn.PYANTZ_NAME  # type: ignore[attr-defined]   # ty:ignore[unresolved-attribute]
        if registered_name.endswith(fn_name):
            return [fn]
    return []


def trace_fn[**P, T](fn: Callable[P, T]) -> Callable[P, T]:
    """Log when a function starts and finishes."""
    logger = logging.getLogger(fn.__name__ if hasattr(fn, "__name__") else __name__)

    @wraps(fn)
    def _log_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        """Run the function, debug logging start/end."""
        logger.debug("Starting function: %s", str(fn))
        try:
            result = fn(*args, **kwargs)
        except:
            logger.debug("Exception in function: %s", str(fn))
            raise
        else:
            logger.debug("Finished function %s", str(fn))
        return result

    return _log_wrapper


def add_parameters[T: BaseModel](
    param_cls: type[T],
    *,
    check_at_startup: bool = False,
) -> Callable[[Callable[[T, SubmissionFnType], bool]], JobFunctionType]:
    """Use the provided pydantic model to type check the parameters.

    Also registers the functions in a global static function list for the API

    At runtime, it will cast the parameters to the provided parameter class and
    pass that pydantic model to the wrapped function. Useful to enforce
    strict typing in a function.

    Args:
        param_cls: basemodel to use to validate
        check_at_startup: if True, will check the parameters class at startup.
            this disallows variables as those won't be set yet. Instead, prefer
            setting this value in the configuration as part of the inital params.s

    """

    def _decorate_fn_with_params(
        fn: Callable[[T, SubmissionFnType], bool],
    ) -> JobFunctionType:
        """Wrap the function in a caster to cast params to the provided params model."""

        @wraps(fn)
        @trace_fn
        def _fn_with_checker(
            untyped_params: ParametersType, submit_fn: SubmissionFnType
        ) -> bool:
            """Check the parameters against the parameter class at runtime."""
            typed_params = param_cls.model_validate(untyped_params)
            return fn(typed_params, submit_fn)

        # add special variables so that we can check if a function has been marked
        _fn_with_checker.PYANTZ_CHECKED = True  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        _fn_with_checker.PYANTZ_CHECK_AT_STARTUP = check_at_startup  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        _fn_with_checker.PYANTZ_VALIDATION_MODEL = param_cls  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        _fn_with_checker.PYANTZ_NAME = serialize_function(_fn_with_checker)  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]

        PYANTZ_REGISTERED_FUNCTION.append(_fn_with_checker)

        return _fn_with_checker

    return _decorate_fn_with_params


def update_deps[T: BaseModel](
    fn: Callable[[T, list[JobConfig]], list[JobConfig]],
) -> Callable[[T, list[JobConfig]], list[JobConfig]]:
    """Wrap a compilation function in a wrapper.

    This will "scramble" the ids of all the jobs to reduce conflicts of
    multiple ids as they're wrapped into virtual jobs. While other jobs
    **should** handle this, this will make life easier.
    """

    def scramble_deps(job_params: T, deps: list[JobConfig]) -> list[JobConfig]:
        """Scramble dependency ids while maintaining dependencies."""
        old_ids_to_new_ids = {job.job_id: str(uuid.uuid4()) for job in deps}

        deps = [
            job.model_copy(
                update={
                    "job_id": old_ids_to_new_ids[job.job_id],
                }
            )
            for job in deps
        ]

        return fn(job_params, deps)

    return scramble_deps
