"""Default jobs for use in the configuration"""

import importlib as _importlib
from typing import Any as _Any

from pyantz.infrastructure.config.base import VALID_DECORATORS, get_function_by_name


def get_job_parameter_schema(job_full_name: str) -> dict[str, _Any] | None:
    """Get the required parameters for an antz job

    Args:
        job_full_name (str): full name of the module and function
            eg. antz.jobs.copy.copy
    Returns:
        dict[str, str]: {parameter_name -> type_name}
    """

    if not isinstance(job_full_name, str):
        return None

    name: str = job_full_name

    components = name.split(".")
    mod_name = ".".join(components[:-1])

    try:
        mod = _importlib.import_module(mod_name)
    except ModuleNotFoundError as _:
        return None

    if hasattr(mod, "Parameters"):
        return getattr(mod, "Parameters").schema_json()
    return None


def get_job_type(job_full_name: str) -> str | None:
    """Get the type of job (Mutable, submitter, simple)"""
    func_handle = get_function_by_name(job_full_name)
    if func_handle is None:
        return func_handle

    if func_handle.__qualname__.split(".")[0] in VALID_DECORATORS:
        return func_handle.__qualname__.split(".")[0]
    return None


__all__ = [
    "assert_variable",
    "change_variable",
    "compare",
    "copy",
    "create_pipelines_from_matrix",
    "delete",
    "explode_pipeline",
    "if_then",
    "nop",
    "parallel_pipelines",
    "restart_pipeline",
    "run_script",
    "set_variable_from_function",
]
