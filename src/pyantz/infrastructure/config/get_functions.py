import importlib
from typing import Any, Callable

from pydantic import BaseModel

_PYANTZ_JOB_TYPE_FIELD: str = "__pyantz_job_type__"
_PYANTZ_PARAMS_MODEL_FIELD: str = "__pyantz_param_model__"


def set_params_model(
    fn: Callable[..., Any], params_model: type[BaseModel] | None
) -> Callable[..., Any]:
    """Sets the parameters model field"""
    setattr(fn, _PYANTZ_PARAMS_MODEL_FIELD, params_model)
    return fn


def set_job_type(fn: Callable[..., Any], job_type: str) -> Callable[..., Any]:
    """Set the job type field"""
    setattr(fn, _PYANTZ_JOB_TYPE_FIELD, job_type)
    return fn


def get_params_model(fn: Callable[..., Any]) -> type[BaseModel] | None:
    """For the provided callable, if it has a params model field,
    return that field for type checking on instatiation of the job
    """
    if hasattr(fn, _PYANTZ_PARAMS_MODEL_FIELD):
        return getattr(fn, _PYANTZ_PARAMS_MODEL_FIELD)
    return None


def get_job_type(fn: Callable[..., Any]) -> str | None:
    """For a provided callable, return what type of job it is

    This API is guaranteed to be stable; our implementation of how
        to mark functions is not. SO **USE THIS** to check

    :param fn: any function which may or may not be marked
    :type fn: Callable[..., Any]
    :return: if the function is marked, return the mark type; else None
    :rtype: str | None
    """
    if hasattr(fn, _PYANTZ_JOB_TYPE_FIELD):
        return getattr(fn, _PYANTZ_JOB_TYPE_FIELD)
    return None


def get_function_by_name_strongly_typed(
    func_type_name: str | tuple[str, ...], strict: bool | None = None
) -> Callable[[Any], Callable[..., Any] | None]:
    """Returns a function Calls get_function_by_name and checks that the function type is correct

    Uses strict rules for internal functions; otherwise uses non-strict
        can be overriden with the strict argument
    If strict is True,
        requires that the function is wrapped in the correct wrapper from job_decorators.py
    if strict is false,
        if the function is not wrapped in any of those wrappers, will skip checking

    Args:
        func_type_name: the name of the wrapper in job_decorators
        strict: overrides the default behavior if provided, see notes above
    """
    # strict for PyAntz jobs because we should at least be consistent!
    if strict is None:
        if isinstance(func_type_name, str):
            strict = func_type_name.startswith("pyantz")
        else:
            strict = all(name.startswith('pyantz') for name in func_type_name)

    def typed_get_function_by_name(
        func_name_or_any: Any,
    ) -> Callable[..., Any] | None:
        func_handle = get_function_by_name(func_name_or_any)
        if func_handle is None:
            return func_handle
        job_type = get_job_type(func_handle)
        if job_type is None and strict:
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


def get_function_by_name(func_name_or_any: Any) -> Callable[..., Any] | None:
    """Links to the function described by config

    Args:
        config (JobConfig): configuration of the job to link

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

    return func
