"""Configuration of a single job to be run."""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    field_serializer,
    model_validator,
)

from .parameters.compile_check import check_config

"""Jobs can use the passed function to create children jobs.
Args:
    job (JobWithContext): the job to submit to be run
"""
type SubmissionFnType = Callable[[JobConfig], None]
"""Jobs are given paramters by the user."""
type ParametersType = Mapping[str, Any]

"""Jobs accept parameters to be completed, as filled in by the user
They return True if they were successful; False otherwise.
"""
type JobFunctionType = Callable[[ParametersType, SubmissionFnType], bool]


def _import_function_by_name(fn_path: Any) -> JobFunctionType:  # noqa: ANN401
    """Import a function by its name."""
    if not isinstance(fn_path, str):
        return fn_path

    name_components = fn_path.split(".")
    mod_name = ".".join(name_components[:-1])
    fn_name = name_components[-1]

    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


def str_uuid4() -> str:
    """Return uuid4 as a string."""
    return str(uuid.uuid4())

class JobConfig(BaseModel):
    """A job to be run."""

    # unique identifier for this job
    # auto generated if the user doesn't specify
    job_id: str = Field(default_factory=str_uuid4)

    # the jobs upon which this one depends before it can be run
    depends_on: set[uuid.UUID | str] | None = None

    # human readable name for this job
    name: str | None = None

    # function to actually run for this job
    function: Annotated[JobFunctionType, BeforeValidator(_import_function_by_name)]

    # parameters to pass to the job while it's running
    parameters: Mapping[str, Any]

    # when error recovering a job should hold how many times its been
    # retried so the runner can decide whether to try to restart it
    num_attempted_runs: int = 0

    # strict means no variables allowed, must use typed functions
    strict: bool = False

    @model_validator(mode="after")
    def validate_fn(self) -> Self:
        """Check the parameters for the function."""
        if not check_config(self, strict=self.strict, check_at_startup=True):
            raise ValueError
        return self

    @field_serializer("function")
    def serialize_function(self, fn: JobFunctionType) -> str:
        """Serialize the fucntion."""
        mod_name: str = fn.__module__ if hasattr(fn, "__module__") else "anonymous"
        fn_name: str = str(fn.__name__) if hasattr(fn, "__name__") else "some_fn"
        return mod_name + "." + fn_name


class JobWithContext(JobConfig):
    """Job to be run along with its variables in scope."""

    variables: Mapping[str, Any] | None = None

    @classmethod
    def from_config(
        cls,
        config_possibly_without_context: JobConfig,
    ) -> JobWithContext:
        """Create a JobWithContext from another job config.

        The other job config may be the parent class or could be an instance
        of this class.

        Args:
            config_possibly_without_context (JobConfig): some configuration

        Returns:
            JobWithContext: job as defined, with default variables if not present

        """
        return JobWithContext.model_validate(
            config_possibly_without_context.model_dump(),
        )
