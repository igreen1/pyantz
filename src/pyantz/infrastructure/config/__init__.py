"""Configuration passed by the user to run a pipeline."""

from __future__ import annotations

from .fn_utils import import_module_item_by_name
from .initial import AnyRunner, InitialConfig
from .job import JobConfig, JobWithContext, SubmissionFnType
from .parameters import (
    add_parameters,
    is_virtual,
    mark_virtual,
    no_submit_fn,
    update_deps,
)
from .pipeline import JobPipeline
from .runners import LocalRunnerConfig
from .virtual import VirtualJobConfig, VirtualParamModel

__all__ = [
    "AnyRunner",
    "InitialConfig",
    "JobConfig",
    "JobPipeline",
    "JobWithContext",
    "LocalRunnerConfig",
    "SubmissionFnType",
    "VirtualJobConfig",
    "VirtualParamModel",
    "add_parameters",
    "import_module_item_by_name",
    "is_virtual",
    "mark_virtual",
    "no_submit_fn",
    "update_deps",
]
