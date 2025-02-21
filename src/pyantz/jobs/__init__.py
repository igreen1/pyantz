"""Default jobs for use in the configuration"""

import importlib as _importlib
from typing import Any as _Any

from pyantz.infrastructure.config.base import (
    get_job_type,
)
from pyantz.infrastructure.config.base import mutable_job as mark_mutable
from pyantz.infrastructure.config.base import simple_job as mark_simple
from pyantz.infrastructure.config.base import submitter_job as mark_submitter


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


__all__ = [
    "branch",
    "file",
    "variables",
    "nop",
    "get_job_type",
    "mark_mutable",
    "mark_simple",
    "mark_submitter",
]
