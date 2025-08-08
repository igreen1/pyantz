"""Base level of the configuration for the core components."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    FieldSerializationInfo,
    JsonValue,
    field_serializer,
    model_validator,
    validate_call,
)

from pyantz.infrastructure.config.get_functions import (
    get_function_by_name_strongly_typed,
    get_params_model,
    set_job_type,
    set_params_model,
)
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.variables import is_variable

if TYPE_CHECKING:
    from .submitters.local_submitter import LocalSubmitterConfig
    from .submitters.slurm_submitter import SlurmBasicSubmitter

type PrimitiveType = str | int | float | bool | None
type AntzConfig = "Config | PipelineConfig | JobConfig | SubmitterJobConfig | MutableJobConfig"
type ParametersType = Mapping[str, AntzConfig | list[AntzConfig] | JsonValue] | None
type SubmitFunctionType = Callable[["Config"], None]
type JobFunctionType = Callable[
    ["ParametersType", logging.Logger],
    Status,
]
type SubmitterJobFunctionType = Callable[
    [
        "ParametersType",
        SubmitFunctionType,
        Mapping[str, PrimitiveType],
        "PipelineConfig",
        logging.Logger,
    ],
    Status,
]
type MutableJobFunctionType = Callable[
    ["ParametersType", Mapping[str, PrimitiveType], logging.Logger],
    tuple[
        Status,
        Mapping[str, PrimitiveType],
    ],
]


class WrappedSubmitterJobFunctionType(Protocol):
    """Submitter jobs are often wrapped by functools.wraps; this hints at that type."""

    __module__: str
    __name__: str
    __wrapped__: SubmitterJobFunctionType

    def __call__(
        self,
        parameters: ParametersType,
        submit_fn: SubmitFunctionType,
        variables: Mapping[str, PrimitiveType],
        pipeline_config: "PipelineConfig",  # noqa: UP037
        logger: logging.Logger,
    ) -> Status: ...


class WrappedMutableJobFunctionType(Protocol):
    """Mutable jobs are often wrapped by functools.wraps; this hints at that type."""

    __module__: str
    __name__: str
    __wrapped__: MutableJobFunctionType

    def __call__(
        self,
        parameters: ParametersType,
        variables: Mapping[str, PrimitiveType],
        logger: logging.Logger,
    ) -> tuple[Status, Mapping[str, PrimitiveType]]: ...


class WrappedJobFunctionType(Protocol):
    """Jobs are often wrapped by functools.wraps; this hints at that type."""

    __module__: str
    __name__: str
    __wrapped__: JobFunctionType

    def __call__(self, parameters: ParametersType, logger: logging.Logger) -> Status: ...


class _AbstractJobConfig(BaseModel, frozen=True):
    """holds common functions for the various job configs."""

    function: Callable[..., Any]
    parameters: ParametersType
    name: str = "some job"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)

    @field_serializer("function")
    def serialize_function(
        self, func: JobFunctionType | WrappedJobFunctionType, info: FieldSerializationInfo
    ) -> str:
        """Serialize to the import required for the function."""
        if hasattr(func, "__wrapped__"):
            wrapped_func: JobFunctionType = func.__wrapped__  # pyright: ignore[reportFunctionMemberAccess] # pylint: disable=line-too-long
            return self.serialize_function(wrapped_func, info)
        return func.__module__ + "." + func.__name__

    @model_validator(mode="after")
    def check_parameters_match(self: _AbstractJobConfig) -> _AbstractJobConfig:
        """Check that the config parameters match the expected parameters for the function."""
        params_model = get_params_model(self.function)
        if params_model is None:
            return self

        if params_model is None:  #  pyright: ignore[reportUnnecessaryComparison]
            return self
        if not isinstance(params_model, type) or not issubclass(params_model, BaseModel):  #  pyright: ignore[reportUnnecessaryIsInstance] # pylint: disable=line-too-long
            msg = f"Invalid parameters mode for function {self.function.__name__}"
            raise TypeError(msg)

        # If the parameters are None or not a mapping, error in validation
        if self.parameters is None:
            msg = f"Parameters cannot be None for function {self.function.__name__}"
            raise ValueError(msg)
        if not isinstance(self.parameters, Mapping):  #  pyright: ignore[reportUnnecessaryIsInstance] # pylint: disable=line-too-long
            msg = f"Parameters must be a mapping for function {self.function.__name__}"
            raise TypeError(msg)

        if any(isinstance(field, BaseModel) for field in self.parameters.values()):
            # cannot check jobs or pipelines
            return self

        # do not check fields with variables in them - variables unknown at "compilation"
        if any(is_variable(field) for field in self.parameters.values()):
            return self
        if not params_model.model_validate(self.parameters):
            msg = (
                f"Parameters do not match expected parameters for function {self.function.__name__}"
            )
            raise ValueError(msg)
        return self


class MutableJobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a submitter job, with different function param types.

    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution.
    """

    type: Literal["mutable_job"]
    function: Annotated[
        MutableJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("mutable")),
    ]


class SubmitterJobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a submitter job, with different function param types.

    These jobs gain access to the submit function and can submit
        entirely new pipelines of execution.
    """

    type: Literal["submitter_job"]
    function: Annotated[
        SubmitterJobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("submitter")),
    ]


class JobConfig(_AbstractJobConfig, frozen=True):
    """Configuration of a job."""

    type: Literal["job", "simple_job"]
    function: Annotated[
        JobFunctionType,
        BeforeValidator(get_function_by_name_strongly_typed("simple")),
    ]


class PipelineConfig(BaseModel, frozen=True):
    """Configuration of a pipeline, which is a series of jobs or sub-pipelines."""

    type: Literal["pipeline"]
    name: str = "pipeline"
    curr_stage: int = 0
    id: uuid.UUID = Field(default_factory=uuid.uuid4, validate_default=True)
    status: int = Status.READY
    max_allowed_restarts: int = 0
    curr_restarts: int = 0
    stages: list[
        Annotated[
            MutableJobConfig | SubmitterJobConfig | JobConfig,
            Field(discriminator="type"),
        ]
    ]


class LoggingConfig(BaseModel, frozen=True):
    """The configuration of logging."""

    type: Literal["off", "file", "console", "remote"] = "console"  # default to logging to screen
    level: int = logging.CRITICAL  # default to only logging on crashes
    directory: str | None = "./log"


class Config(BaseModel, frozen=True):
    """The global configuration to submit to runner."""

    variables: Mapping[str, PrimitiveType]
    config: PipelineConfig


class InitialConfig(BaseModel, frozen=True):
    """The configuration of both the jobs and the submitters."""

    analysis_config: Config
    submitter_config: LocalSubmitterConfig | SlurmBasicSubmitter = Field(discriminator="type")
    logging_config: LoggingConfig = LoggingConfig()


def mutable_job(
    params_model: type[BaseModel] | None,
) -> Callable[
    [
        Callable[
            [ParametersType, Mapping[str, PrimitiveType], logging.Logger],
            tuple[Status, Mapping[str, PrimitiveType]],
        ]
    ],
    WrappedMutableJobFunctionType,
]:
    """Wrap a mutable job and add its parameters model to its definition."""

    def mark_mutable_job(
        fn: Callable[
            [ParametersType, Mapping[str, PrimitiveType], logging.Logger],
            tuple[Status, Mapping[str, PrimitiveType]],
        ],
    ) -> WrappedMutableJobFunctionType:
        """Wrap a mutable job.

        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model.
        """

        @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
        def _mutable_job(
            params: ParametersType,
            variables: Mapping[str, PrimitiveType],
            logger: logging.Logger,
        ) -> tuple[Status, Mapping[str, PrimitiveType]]:
            return fn(params, variables, logger)

        set_job_type(_mutable_job, "mutable")
        set_params_model(_mutable_job, params_model)
        # pyright doesn't properly understand we're foricibly setting an attribute
        _mutable_job.__wrapped__ = fn  # type: ignore [attr-defined] # pyright: ignore[reportFunctionMemberAccess] # pylint: disable=line-too-long
        return _mutable_job  # type: ignore [return-value] # pyright: ignore[reportReturnType] # pylint: disable=line-too-long

    return mark_mutable_job


def submitter_job(
    params_model: type[BaseModel] | None,
) -> Callable[[SubmitterJobFunctionType], WrappedSubmitterJobFunctionType]:
    """Wrap a submitter job and add its parameters model to its definition."""

    def mark_submitter_job(fn: SubmitterJobFunctionType) -> WrappedSubmitterJobFunctionType:
        """Wrap a submitter job .

        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model.
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

        set_job_type(_submitter_job, "submitter")
        set_params_model(_submitter_job, params_model)
        # pyright doesn't properly understand we're foricibly setting an attribute
        _submitter_job.__wrapped__ = fn  # type: ignore [attr-defined] # pyright: ignore[reportFunctionMemberAccess] # pylint: disable=line-too-long
        return _submitter_job  # type: ignore [return-value] # pyright: ignore[reportReturnType] # pylint: disable=line-too-long

    return mark_submitter_job


def simple_job(
    params_model: type[BaseModel] | None,
) -> Callable[[Callable[[ParametersType, logging.Logger], Status]], WrappedJobFunctionType]:
    """Wrap a simple job and add its parameters model to its definition."""

    def mark_simple_job(
        fn: Callable[[ParametersType, logging.Logger], Status],
    ) -> WrappedJobFunctionType:
        """Wrap a simple job.

        1. Allow it to accept variable args if a user incorrectly marks job
        2. Allow for type checking in the pydantic model.
        """

        @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
        def _simple_job(
            params: ParametersType,
            logger: logging.Logger,
        ) -> Status:
            return fn(params, logger)

        set_job_type(_simple_job, "simple")
        set_params_model(_simple_job, params_model)
        # pyright doesn't properly understand we're foricibly setting an attribute
        _simple_job.__wrapped__ = fn  # type: ignore [attr-defined] # pyright: ignore[reportFunctionMemberAccess] # pylint: disable=line-too-long
        return _simple_job  # type: ignore [return-value] # pyright: ignore[reportReturnType] # pylint: disable=line-too-long

    return mark_simple_job


__all__ = [
    "Config",
    "InitialConfig",
    "JobConfig",
    "JobFunctionType",
    "LoggingConfig",
    "MutableJobConfig",
    "MutableJobFunctionType",
    "ParametersType",
    "PipelineConfig",
    "PrimitiveType",
    "SubmitFunctionType",
    "SubmitterJobConfig",
    "mutable_job",
    "simple_job",
    "submitter_job",
]
