"""Configuration of a single job to be run."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    BeforeValidator,
    ConfigDict,
    WithJsonSchema,
    field_serializer,
    model_validator,
)

from .abtrast_job import AbstractJobConfig
from .fn_utils import (
    import_function_by_name,
    import_module_item_by_name,
    serialize_function,
)
from .parameters import is_virtual
from .parameters.compile_check import check_config
from .variables import resolve_var_any
from .virtual import VirtualJobConfig

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


class JobConfig(AbstractJobConfig):
    """A job to be run."""

    model_config = ConfigDict(frozen=True)

    # human readable name for this job
    name: str | None = None

    # function to actually run for this job
    function: Annotated[
        JobFunctionType,
        BeforeValidator(import_function_by_name),
        WithJsonSchema(
            {
                "type": "string",
                "format": "base64",
            }
        ),
    ]

    # when error recovering a job should hold how many times its been
    # retried so the runner can decide whether to try to restart it
    num_attempted_runs: int = 0

    # denotes that this a concrete job
    # makes introspection easier/faster at runtime.
    virtual: Literal[False] = False

    @model_validator(mode="after")
    def validate_fn(self) -> Self:
        """Check the parameters for the function."""
        if not check_config(self, strict=self.strict, check_at_startup=True):
            msg = "Bad function definition"
            raise ValueError(msg)
        return self

    @field_serializer("function")
    def serialize_job_function(self, fn: JobFunctionType) -> str:
        """Serialize the fucntion."""
        return serialize_function(fn)


class JobWithContext(JobConfig):
    """Job to be run along with its variables in scope."""

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, Any] | None = None

    @model_validator(mode="after")
    def _update_ids_in_hyper_parameters(self) -> Self:
        """Update ids in the "hyper params" (like id, depends_on)."""
        try:
            if not self.variables:
                return self
            updates: dict[str, Any] = {}

            for field in ("job_id", "depends_on", "function"):
                original_field = getattr(self, field)
                new_field, _ = resolve_var_any(original_field, variables=self.variables)
                if new_field != original_field:
                    updates[field] = new_field

            if updates:
                return self.model_copy(update=updates)
        except ValueError as exc:
            msg = "Error modifying hyper-params with variables"
            raise ValueError(msg) from exc
        return self

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

    def inherit_context(self, parent_context: Mapping[str, Any]) -> JobWithContext:
        """Create a JobWithContext inheriting parent variables."""
        return self.model_copy(
            update={
                "variables": {
                    **parent_context,
                    **(self.variables or {}),
                }
            }
        )


def make_job(
    config: Any,  # noqa: ANN401
) -> JobConfig | VirtualJobConfig:
    """Make a job based on a user provided configuration."""
    if isinstance(config, (AbstractJobConfig)):
        return config  # type: ignore[return-value] # pyright: ignore[reportReturnType]
    if not isinstance(config, Mapping):
        raise TypeError
    config = cast("Mapping[str, Any]", config)
    if "function" not in config:
        raise ValueError
    use_virtual = cast(
        "bool",
        config.get(
            "virtual",
            is_virtual(
                import_module_item_by_name(
                    config["function"],
                ),
            ),
        ),
    )

    if use_virtual:
        return VirtualJobConfig.model_validate(config)
    return JobConfig.model_validate(config)
