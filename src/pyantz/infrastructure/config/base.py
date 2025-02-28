"""
This is the base level of the configuration for the core components
"""

from __future__ import annotations

import importlib
import logging
import uuid
from typing import Any, Callable, Literal, Mapping, TypeAlias, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
    validate_call,
)
from typing_extensions import Annotated

from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.variables import is_variable

from .local_submitter import LocalSubmitterConfig

PrimitiveType: TypeAlias = str | int | float | bool
AntzConfig: TypeAlias = Union["Config", "PipelineConfig", "JobConfig"]
ParametersType: TypeAlias = (
    Mapping[str, PrimitiveType | list[PrimitiveType] | AntzConfig] | None
)
SubmitFunctionType: TypeAlias = Callable[["Config"], None]
JobFunctionType: TypeAlias = Callable[
    ["ParametersType", logging.Logger],
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
    ["ParametersType", Mapping[str, PrimitiveType], logging.Logger],
    tuple[
        Status,
        Mapping[str, PrimitiveType],
    ],
]

_PYANTZ_JOB_TYPE_FIELD: str = "__pyantz_job_type__"
_PYANTZ_PARAMS_MODEL_FIELD: str = "__pyantz_param_model__"


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
    func_type_name: str, strict: bool | None = None
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
        strict = func_type_name.startswith("pyantz")

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
        if job_type != func_type_name:
            return None
        return func_handle

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


class _AbstractJobConfig(BaseModel, frozen=True):
    """holds common functions for the various job configs"""

    function: Callable[..., Any]
    parameters: ParametersType
    name: str = "some job"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)

    @field_serializer("function")
    def serialize_function(self, func: JobFunctionType, info):
        """To serialize function, store the import path to the func
        instead of its handle as a str
        """
        if hasattr(func, "__wrapped__"):
            print("WRAPPED", func)
            return self.serialize_function(func.__wrapped__, info)
        return func.__module__ + "." + func.__name__

    @model_validator(mode="after")
    def check_parameters_match(self: "_AbstractJobConfig") -> "_AbstractJobConfig":
        """Checks that the config parameters match the expected parameters for the function"""

        if not hasattr(self.function, _PYANTZ_PARAMS_MODEL_FIELD):
            return self

        # check if we must validate in the first place
        params_model = getattr(self.function, _PYANTZ_PARAMS_MODEL_FIELD)
        if params_model is None:
            return self
        if not isinstance(params_model, type) or not issubclass(
            params_model, BaseModel
        ):
            raise ValueError(
                f"Invalid parameters mode for function {self.function.__name__}"
            )

        # If the parameters are None or not a mapping, error in validation
        if self.parameters is None:
            raise ValueError(
                f"Parameters cannot be None for function {self.function.__name__}"
            )
        if not isinstance(self.parameters, Mapping):
            raise ValueError(
                f"Parameters must be a mapping for function {self.function.__name__}"
            )

        if any(isinstance(field, BaseModel) for field in self.parameters.values()):
            # cannot check jobs or pipelines
            return self
        if any(
            is_variable(field)
            for field in self.parameters.values()
            if isinstance(field, PrimitiveType)
        ):
            return self
        if not params_model.model_validate(self.parameters):
            raise ValueError(
                f"Parameters do not match expected parameters for function {self.function.__name__}"
            )
        return self


class MutableJobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a submitter job, with different function param types
    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution

    However, they must ALWAYS BE FINAL
    """

    type: Literal["mutable_job"]
    function: Annotated[
        MutableJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("mutable")),
    ]


class SubmitterJobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a submitter job, with different function param types
    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution

    However, they must ALWAYS BE FINAL
    """

    type: Literal["submitter_job"]
    function: Annotated[
        SubmitterJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("submitter")),
    ]


class JobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a job"""

    type: Literal["job"] | Literal["simple_job"]
    function: Annotated[
        JobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("simple")),
    ]


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


def mutable_job(params_model: type[BaseModel] | None) -> Callable[
    [
        Callable[
            ["ParametersType", Mapping[str, PrimitiveType], logging.Logger],
            tuple[Status, Mapping[str, PrimitiveType]],
        ]
    ],
    MutableJobFunctionType,
]:
    """Wrap a mutable job and add its parameters model to its definition to allow
    the configuration parser to validate the parameters
    """

    def mark_mutable_job(
        fn: Callable[
            ["ParametersType", Mapping[str, PrimitiveType], logging.Logger],
            tuple[Status, Mapping[str, PrimitiveType]],
        ],
    ) -> MutableJobFunctionType:
        """Wrap a mutable job to
        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model
        """

        @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
        def _mutable_job(
            params: ParametersType,
            variables: Mapping[str, PrimitiveType],
            logger: logging.Logger,
        ) -> tuple[Status, Mapping[str, PrimitiveType]]:
            return fn(params, variables, logger)

        setattr(_mutable_job, _PYANTZ_JOB_TYPE_FIELD, "mutable")
        setattr(_mutable_job, _PYANTZ_PARAMS_MODEL_FIELD, params_model)
        setattr(_mutable_job, "__wrapped__", fn)
        return _mutable_job

    return mark_mutable_job


def submitter_job(
    params_model: type[BaseModel] | None,
) -> Callable[[SubmitterJobFunctionType], SubmitterJobFunctionType]:
    """Wrap a submitter job and add its parameters model to its definition to allow
    the configuration parser to validate the parameters
    """

    def mark_submitter_job(fn: SubmitterJobFunctionType) -> SubmitterJobFunctionType:
        """Wrap a submitter job to
        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model
        """

        @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
        def _submitter_job(
            params: ParametersType,
            submitter: SubmitFunctionType,
            variables: Mapping[str, PrimitiveType],
            pipeline_config: PipelineConfig,
            logger: logging.Logger,
        ) -> Status:
            return fn(params, submitter, variables, pipeline_config, logger)

        setattr(_submitter_job, _PYANTZ_JOB_TYPE_FIELD, "submitter")
        setattr(_submitter_job, _PYANTZ_PARAMS_MODEL_FIELD, params_model)
        setattr(_submitter_job, "__wrapped__", fn)
        return _submitter_job

    return mark_submitter_job


def simple_job(
    params_model: type[BaseModel] | None,
) -> Callable[[Callable[[ParametersType, logging.Logger], Status]], JobFunctionType]:
    """Wrap a simple job and add its parameters model to its definition to allow
    the configuration parser to validate the parameters
    """

    def mark_simple_job(
        fn: Callable[[ParametersType, logging.Logger], Status],
    ) -> JobFunctionType:
        """Wrap a simple job to
        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model
        """

        @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
        def _simple_job(
            params: ParametersType,
            logger: logging.Logger,
        ) -> Status:
            return fn(params, logger)

        setattr(_simple_job, _PYANTZ_JOB_TYPE_FIELD, "simple")
        setattr(_simple_job, _PYANTZ_PARAMS_MODEL_FIELD, params_model)
        setattr(_simple_job, "__wrapped__", fn)
        return _simple_job

    return mark_simple_job


__all__ = [
    "simple_job",
    "submitter_job",
    "mutable_job",
    "InitialConfig",
    "Config",
    "LoggingConfig",
    "PipelineConfig",
    "JobConfig",
    "SubmitterJobConfig",
    "MutableJobConfig",
    "ParametersType",
    "PrimitiveType",
    "get_function_by_name",
    "get_function_by_name_strongly_typed",
    "SubmitFunctionType",
    "MutableJobFunctionType",
    "JobFunctionType",
]
