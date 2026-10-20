"""Configuration of a single job to be run."""

from collections.abc import Callable, Mapping
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    BeforeValidator,
    ConfigDict,
    WithJsonSchema,
    field_serializer,
    model_validator,
)

from .abstract_job import AbstractJobConfig
from .fn_utils import (
    import_function_by_name,
    import_module_item_by_name,
    serialize_function,
)
from .parameters import is_virtual
from .parameters.compile_check import check_config
from .variables import resolve_var_any
from .virtual import VirtualJobConfig

type SubmissionFnType = Callable[[JobConfig], None]  # pylint: disable=E0601
"""Function a "user" function receives to submit jobs."""

type ParametersType = Mapping[str, Any]
"""Jobs are given parameters by the user."""

type JobFunctionType = Callable[[ParametersType, SubmissionFnType], bool]
"""Function that performs the job expected."""


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
        if not check_config(
            self,
            strict=self.strict,
            check_at_startup=self.strict,
        ):
            msg = "Bad function definition"
            raise ValueError(msg)
        return self

    @field_serializer("function")
    def serialize_job_function(self, fn: JobFunctionType) -> str:
        """Serialize the function."""
        return serialize_function(fn)


class JobWithContext(JobConfig):
    """Job to be run along with its variables in scope."""

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _update_ids_in_hyper_parameters(cls, data: Any) -> Any:  # noqa: ANN401
        """Update ids in the "hyper params" (like id, name, depends_on).

        This happens before validation, so the resolved values are validated
        like any value given directly.
        """
        if not isinstance(data, Mapping):
            return data
        data = cast("Mapping[str, Any]", data)
        variables = data.get("variables")
        if not variables:
            return data

        updates: dict[str, Any] = {}
        for field in ("job_id", "name", "depends_on"):
            if field not in data:
                continue
            original_field = data[field]
            new_field, _ = resolve_var_any(original_field, variables=variables)
            if new_field != original_field:
                updates[field] = new_field

        return {**data, **updates} if updates else data

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
        # no dump round-trip: the function is passed as the callable it already is,
        # instead of being serialized to a name and imported again
        config = config_possibly_without_context
        return JobWithContext.model_validate(
            {
                **{field: getattr(config, field) for field in JobConfig.model_fields},
                "variables": getattr(config, "variables", None),
            },
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
        msg = f"Job config must be a mapping, got {type(config).__name__}"
        raise TypeError(msg)
    config = cast("Mapping[str, Any]", config)
    if "function" not in config:
        msg = "Job config is missing required key 'function'"
        raise ValueError(msg)
    if "virtual" in config:
        use_virtual = bool(config["virtual"])
    else:
        use_virtual = is_virtual(import_module_item_by_name(config["function"]))

    if use_virtual:
        return VirtualJobConfig.model_validate(config)
    return JobConfig.model_validate(config)
