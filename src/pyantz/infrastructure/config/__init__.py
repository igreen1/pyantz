"""Configuration passed by the user to run a pipeline."""

from .initial import AnyRunner, InitialConfig
from .job import JobConfig, JobWithContext, SubmissionFnType
from .parameters import add_parameters, is_virtual, mark_virtual, no_submit_fn
from .runners import LocalRunnerConfig
from .virtual import VirtualJobConfig, VirtualParamModel

__all__ = [
    "AnyRunner",
    "InitialConfig",
    "JobConfig",
    "JobWithContext",
    "LocalRunnerConfig",
    "SubmissionFnType",
    "VirtualJobConfig",
    "VirtualParamModel",
    "add_parameters",
    "is_virtual",
    "mark_virtual",
    "no_submit_fn",
]
