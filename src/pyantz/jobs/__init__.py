"""Default jobs for use in the configuration."""

from __future__ import annotations

import importlib as _importlib
import inspect
import pkgutil
from typing import TYPE_CHECKING
from typing import Any as _Any

from pyantz.infrastructure.config.base import mutable_job as mark_mutable
from pyantz.infrastructure.config.base import simple_job as mark_simple
from pyantz.infrastructure.config.base import submitter_job as mark_submitter
from pyantz.infrastructure.config.get_functions import get_job_type

from . import analysis, branch, dispatch, file, nop, restart_pipeline, variables

if TYPE_CHECKING:
    from types import ModuleType

    from pydantic import BaseModel


def get_job_parameter_schema(job_full_name: str) -> dict[str, _Any] | None:
    """Get the required parameters for an antz job.

    Args:
        job_full_name (str): full name of the module and function
            eg. antz.jobs.copy.copy
    Returns:
        str: JSON of {parameter_name -> type_name}

    """
    if not isinstance(job_full_name, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        return None

    name: str = job_full_name

    components = name.split(".")
    mod_name = ".".join(components[:-1])

    try:
        mod = _importlib.import_module(mod_name)
    except ModuleNotFoundError as _:
        return None

    if hasattr(mod, "Parameters"):
        params: BaseModel = mod.Parameters
        return params.model_json_schema()
    return None


def get_all_jobs() -> list[str]:
    """Find all the jobs in the pyantz package."""
    return _find_functions_in_package_by_name("pyantz.jobs")


def _find_functions_in_package_by_name(package_name: str) -> list[str]:
    """Find all functions within a specified Python package.

    Args:
        package_name (str): The name of the package to inspect.

    Returns:
        list: A list of function objects found within the package.

    """
    try:
        # Import the package
        package = __import__(package_name, fromlist=[""])
    except ImportError:
        return []
    return _find_functions_in_package(package=package)


def _find_functions_in_package(package: ModuleType) -> list[str]:
    functions: list[str] = []
    # Iterate through modules within the package
    for _importer, modname, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        try:
            module_or_pkg = __import__(modname, fromlist=[""])
            # Find functions within the current module
            if ispkg:
                functions.extend(_find_functions_in_package(module_or_pkg))
            for name, obj in inspect.getmembers(module_or_pkg):
                if (
                    inspect.isfunction(obj)
                    and obj.__module__.startswith("pyantz")
                    and get_job_type(obj) is not None
                ):
                    functions.append(modname + "." + name)
        except ImportError:
            continue
    return functions


__all__ = [
    "analysis",
    "branch",
    "dispatch",
    "file",
    "get_job_parameter_schema",
    "get_job_type",
    "mark_mutable",
    "mark_simple",
    "mark_submitter",
    "nop",
    "restart_pipeline",
    "variables",
]
