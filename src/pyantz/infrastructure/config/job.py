"""Configuration of a single job to be run."""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable, Mapping
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, field_serializer

"""Jobs can use the passed function to create children jobs."""
type SubmissionFnType = Callable[[JobConfig], None]
"""Jobs are given paramters by the user."""
type ParametersType = Mapping[str, Any]

"""Jobs accept parameters to be completed, as filled in by the user
They return True if they were successful; False otherwise.
"""
type JobFunctionType = Callable[[ParametersType, SubmissionFnType], bool]


def _import_function_by_name(fn_path: Any) -> JobFunctionType: # noqa: ANN401
    """Import a function by its name."""
    if not isinstance(fn_path, str):
        return fn_path

    name_components = fn_path.split(".")
    mod_name = ".".join(name_components[:-1])
    fn_name = name_components[-1]

    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


class JobConfig(BaseModel):
    """A job to be run."""

    # unique identifier for this job
    # auto generated if the user doesn't specify
    job_id: uuid.UUID | str = Field(default_factory=uuid.uuid4)

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

    @field_serializer("function")
    def serialize_function(self, fn: JobFunctionType) -> str:
        """Serialize the fucntion."""
        mod_name = fn.__module__ if hasattr(fn, "__module__") else "anonymous"
        fn_name = fn.__name__ if hasattr(fn, "__name__") else "some_fn"
        return mod_name + "." + fn_name
