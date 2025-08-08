"""Functions to dynamically import and tag functions from a configuration."""

import importlib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

_PYANTZ_JOB_TYPE_FIELD: str = "__pyantz_job_type__"
_PYANTZ_PARAMS_MODEL_FIELD: str = "__pyantz_param_model__"


def set_params_model(
    fn: Callable[..., Any], params_model: type[BaseModel] | None
) -> Callable[..., Any]:
    """Set the parameters model field."""
    setattr(fn, _PYANTZ_PARAMS_MODEL_FIELD, params_model)
    return fn


def set_job_type(fn: Callable[..., Any], job_type: str) -> Callable[..., Any]:
    """Set the job type field."""
    setattr(fn, _PYANTZ_JOB_TYPE_FIELD, job_type)
    return fn


def get_params_model(fn: Callable[..., Any]) -> type[BaseModel] | None:
    """Return params model field if a job was annotated with one."""
    if hasattr(fn, _PYANTZ_PARAMS_MODEL_FIELD):
        params_model = getattr(fn, _PYANTZ_PARAMS_MODEL_FIELD)
        if not issubclass(params_model, BaseModel):
            return None
        # if statement above handles this type check
        # but mypy doesn't properly "see" that
        return params_model  # type: ignore[no-any-return]
    return None


def get_job_type(fn: Callable[..., Any] | None) -> str | None:
    """Return type of job for a provided callable, if it is properly marked.

    This API is guaranteed to be stable; our implementation of how
        to mark functions is not. SO **USE THIS** to check

    :param fn: any function which may or may not be marked
    :type fn: Callable[..., Any]
    :return: if the function is marked, return the mark type; else None
    :rtype: str | None

    """
    if fn is None:
        return fn
    if hasattr(fn, _PYANTZ_JOB_TYPE_FIELD):
        job_type: Any = getattr(fn, _PYANTZ_JOB_TYPE_FIELD)
        if not isinstance(job_type, str):
            return None
        return job_type
    return None


def get_function_by_name_strongly_typed(
    func_type_name: str | tuple[str, ...], *, strict: bool | None = None
) -> Callable[[Any], Callable[..., Any] | None]:
    """Return a function by callong `get_function_by_name` and checking types.

    Uses strict rules for internal functions; otherwise uses non-strict
        can be overriden with the strict argument
    If strict is True,
        requires that the function is wrapped in the correct wrapper from job_decorators.py
    if strict is false,
        if the function is not wrapped in any of those wrappers, will skip checking

    Args:
        func_type_name: the name of the wrapper in job_decorators
        strict: overrides the default behavior if provided, see notes above

    Returns (Callable[[Any], Callable[..., Any] | None]):
        Callabel for a provided function of the correct type

    """
    # allow "any" function because prior to pydantic validation we can't guarantee anything
    # so this function really should allow anything and handle the edge cases
    def typed_get_function_by_name(
        func_name_or_any: Any,  # noqa: ANN401
    ) -> Callable[..., Any] | None:
        is_strict = strict
        # always force strict with pyantz library
        if not is_strict and isinstance(func_name_or_any, str):
            is_strict = func_name_or_any.startswith("pyantz")
        func_handle = get_function_by_name(func_name_or_any)
        job_type = get_job_type(func_handle)
        if job_type is None and is_strict:
            return None
        if job_type is None:
            return func_handle
        if isinstance(func_type_name, str):
            if job_type != func_type_name:
                return None
            return func_handle
        if job_type in func_type_name:
            return func_handle
        return None

    return typed_get_function_by_name


def get_function_by_name(func_name_or_any: Any) -> Callable[..., Any] | None:  # noqa: ANN401
    """Link to the function described by config.

    Args:
        func_name_or_any (Any): name of the function or

    Returns:
        Callable[[ParametersType, Callable[[PipelineConfig], None]], Status] } None:
            a function that takes parameters and a
            submitter callable and returns a status after executing
            Returns None if it is unable to find the correct function

    """
    if not isinstance(func_name_or_any, str):
        return None

    name: str = func_name_or_any

    components = name.split(".")
    func_name = components[-1]
    mod_name = ".".join(components[:-1])

    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError as _:
        return None

    if not hasattr(mod, func_name):
        return None

    func = getattr(mod, func_name)

    if not callable(func):
        return None

    # ignore type, mypy not properly accounting for "if not callable" above
    return func  # type: ignore[no-any-return]
