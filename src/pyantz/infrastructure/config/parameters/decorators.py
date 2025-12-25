"""Decorate functions and strongly enforce parameter types."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyantz.infrastructure.config.job import (
        JobFunctionType,
        ParametersType,
        SubmissionFnType,
    )


def add_parameters[T: BaseModel](
    param_cls: type[T],
    *,
    check_at_startup: bool = False,
) -> Callable[[Callable[[T, SubmissionFnType], bool]], JobFunctionType]:
    """Use the provided pydantic model to type check the parameters.

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
        def _fn_with_checker(
            untyped_params: ParametersType, submit_fn: SubmissionFnType
        ) -> bool:
            """Check the parameters against the parameter class at runtime."""
            typed_params = param_cls.model_validate(untyped_params)
            return fn(typed_params, submit_fn)

        # add special variables so that we can check if a function has been marked
        _fn_with_checker.PYANTZ_CHECKED = True  # type: ignore[attr-defined]
        _fn_with_checker.PYANTZ_CHECK_AT_STARTUP = check_at_startup  # type: ignore[attr-defined]
        _fn_with_checker.PYANTZ_VALIDATION_MODEL = param_cls  # type: ignore[attr-defined]

        return _fn_with_checker

    return _decorate_fn_with_params
