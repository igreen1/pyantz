"""
This is the base level of the configuration for the core components
"""

from __future__ import annotations

import importlib
import logging
import uuid
from typing import Any, Callable, Literal, Mapping, TypeAlias, Union

from pyantz.infrastructure.core.status import Status
from pydantic import BaseModel, BeforeValidator, Field, field_serializer
from typing_extensions import Annotated, Unpack

from .local_submitter import LocalSubmitterConfig

VALID_DECORATORS: set[str] = {"mutable_job", "submitter_job", "simple_job"}

PrimitiveType: TypeAlias = str | int | float | bool
AntzConfig: TypeAlias = Union["Config", "PipelineConfig", "JobConfig"]
ParametersType: TypeAlias = (
    Mapping[str, PrimitiveType | list[PrimitiveType] | AntzConfig] | None
)
SubmitFunctionType: TypeAlias = Callable[["Config"], None]
JobFunctionType: TypeAlias = Callable[
    ["ParametersType", logging.Logger, Unpack[Any]],
    Status,
]
SubmitterJobFunctionType: TypeAlias = Callable[
    [
        "ParametersType",
        SubmitFunctionType,
        Mapping[str, PrimitiveType],
        "PipelineConfig",
        logging.Logger,
    ],
    Status,
]
MutableJobFunctionType: TypeAlias = Callable[
    ["ParametersType", Mapping[str, PrimitiveType], logging.Logger, Unpack[Any]],
    tuple[
        Status,
        Mapping[str, PrimitiveType],
    ],
]


def get_function_by_name_strongly_typed(
    func_type_name: str,
) -> Callable[[Any], Callable[..., Any] | None]:
    """Returns a function Calls get_function_by_name and checks that the function type is correct

    Uses strict rules for internal functions; otherwise uses non-strict
    If strict is True,
        requires that the function is wrapped in the correct wrapper from job_decorators.py
    if strict is false,
        if the function is not wrapped in any of those wrappers, will skip checking

    Args:
        func_type_name: the name of the wrapper in job_decorators
    """

    strict: bool = func_type_name.startswith("pyantzjobs")

    if strict:

        def strict_get_function_by_name(
            func_name_or_any: Any,
        ) -> Callable[..., Any] | None:
            func_handle = get_function_by_name(func_name_or_any)
            if func_handle is None:
                return func_handle
            print(func_handle.__qualname__)
            if func_handle.__qualname__.split(".")[0] != func_type_name:
                return None
            return func_handle

        return strict_get_function_by_name

    def get_function_by_name_typed(func_name_or_any: Any) -> Callable[..., Any] | None:
        func_handle = get_function_by_name(func_name_or_any)
        if func_handle is None:
            return func_handle
        if func_handle.__qualname__.split(".")[0] != func_type_name:
            if func_handle.__qualname__.split(".")[0] not in VALID_DECORATORS:
                return func_handle  # doesn't have any of the valid wrappers
            return None
        return func_handle

    return get_function_by_name_typed


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


class MutableJobConfig(BaseModel, frozen=True):
    """Configuration of a submitter job, with different function param types
    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution

    However, they must ALWAYS BE FINAL
    """

    type: Literal["mutable_job"]
    name: str = "some job"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)
    function: Annotated[
        MutableJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("mutable_job")),
    ]
    parameters: ParametersType

    @field_serializer("function")
    def serialize_function(self, func: MutableJobFunctionType, _info):
        """To serialize function, store the import path to the func
        instead of its handle as a str
        """
        return func.__module__ + "." + func.__name__


class SubmitterJobConfig(BaseModel, frozen=True):
    """Configuration of a submitter job, with different function param types
    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution

    However, they must ALWAYS BE FINAL
    """

    type: Literal["submitter_job"]
    name: str = "some job"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)
    function: Annotated[
        SubmitterJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("submitter_job")),
    ]
    parameters: ParametersType

    @field_serializer("function")
    def serialize_function(self, func: SubmitterJobFunctionType, _info):
        """To serialize function, store the import path to the func
        instead of its handle as a str
        """
        return func.__module__ + "." + func.__name__


class JobConfig(BaseModel, frozen=True):
    """Configuration of a job"""

    type: Literal["job"]
    name: str = "some job"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)
    function: Annotated[
        JobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("simple_job")),
    ]
    parameters: ParametersType

    @field_serializer("function")
    def serialize_function(self, func: JobFunctionType, _info):
        """To serialize function, store the import path to the func
        instead of its handle as a str
        """
        return func.__module__ + "." + func.__name__


class PipelineConfig(BaseModel, frozen=True):
    """Configuration of a pipeline, which is a series of jobs or sub-pipelines"""

    type: Literal["pipeline"]
    name: str = "pipeline"
    curr_stage: int = 0
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)
    status: int = Status.READY
    max_allowed_restarts: int = 0
    curr_restarts: int = 0
    stages: list[JobConfig | SubmitterJobConfig | MutableJobConfig]


class LoggingConfig(BaseModel, frozen=True):
    """The configuration of logging"""

    type: Literal["off", "file", "console", "remote"] = (
        "console"  # default to logging to screen
    )
    level: int = logging.CRITICAL  # default to only logging on crashes
    directory: str | None = "./log"


class Config(BaseModel, frozen=True):
    """The global configuration to submit to runner"""

    variables: Mapping[str, PrimitiveType]
    config: PipelineConfig


class InitialConfig(BaseModel, frozen=True):
    """The configuration of both the jobs and the submitters"""

    analysis_config: Config
    submitter_config: LocalSubmitterConfig = Field(discriminator="type")
    logging_config: LoggingConfig = LoggingConfig()
