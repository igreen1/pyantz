"""Default jobs for use in the configuration."""

import importlib as _importlib
from typing import TYPE_CHECKING
from typing import Any as _Any

from pyantz.infrastructure.config.base import mutable_job as mark_mutable
from pyantz.infrastructure.config.base import simple_job as mark_simple
from pyantz.infrastructure.config.base import submitter_job as mark_submitter
from pyantz.infrastructure.config.get_functions import (
    get_job_type,
)

from . import branch, file, nop, variables

if TYPE_CHECKING:
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
        params: BaseModel = mod.parameters
        return params.model_json_schema()
    return None


__all__ = [
    "branch",
    "file",
    "get_job_type",
    "mark_mutable",
    "mark_simple",
    "mark_submitter",
    "nop",
    "variables",
]
