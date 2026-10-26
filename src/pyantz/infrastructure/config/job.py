"""Configuration of a single job to be run.

Example of :class:`JobConfig`:

    .. testcode::

        from pyantz.infrastructure.config import JobConfig

        job = JobConfig.model_validate(
            {
                "name": "say hi",
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
                "max_retries": 2,
            }
        )
        print(job.function.__name__, job.max_retries, job.dependency_type)

    .. testoutput::

        do_nothing 2 afterok
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    BeforeValidator,
    ConfigDict,
    Field,
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

    name: str | None = None
    """Human readable name for this job."""

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
    """Function to actually run for this job, given by its full import path."""

    num_attempted_runs: int = 0
    """How many times the job has been run, so the runner can decide whether to
    try it again."""

    timeout_seconds: float | None = Field(default=None, gt=0)
    """If set, the local runner stops the job (and marks it as failed) after it
    has been running this many seconds. The job then runs in its own process."""

    max_retries: int = Field(default=0, ge=0)
    """How many times a failed job is run again before it is given up on. Retried
    jobs run again from the start, so jobs which submit other jobs should not be
    retried (the children would be submitted twice)."""

    dependency_type: Literal["afterok", "afterany", "afternotok"] = "afterok"
    """How this job waits for the jobs it depends on (SLURM runner only; the
    local runner always waits for success): ``afterok`` runs it if they
    succeeded, ``afterany`` after they finished either way (e.g., cleanup jobs),
    ``afternotok`` only if one failed."""

    virtual: Literal[False] = False
    """Denotes that this a concrete job; makes introspection easier/faster at
    runtime."""

    @model_validator(mode="after")
    def validate_fn(self) -> Self:
        """Check the parameters for the function.

        See :func:`~pyantz.infrastructure.config.parameters.compile_check.check_config`
        for when the parameters are checked.

        Args:
            None.

        Returns:
            Self: the validated job.

        Raises:
            ValueError: if the parameters are checked and don't fit the function's
                parameters model, or the job is strict and its function isn't
                registered.

        Example:
            .. testcode::

                from pydantic import ValidationError

                from pyantz.infrastructure.config import JobConfig

                try:
                    JobConfig(
                        function="pyantz.jobs.files.simple.copy",
                        parameters={"src": "a.txt"},  # dst is missing
                        strict=True,
                    )
                except ValidationError:
                    print("bad parameters")

            .. testoutput::

                bad parameters

        """
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
        """Serialize the function.

        Args:
            fn: the job's function.

        Returns:
            str: the function's full import path.

        Raises:
            ValueError: if the function can't be imported by name, e.g., a lambda.

        Example:
            .. testcode::

                from pyantz.infrastructure.config import JobConfig

                job = JobConfig(
                    function="pyantz.jobs.testing.nop.do_nothing", parameters={}
                )
                print(job.model_dump()["function"])

            .. testoutput::

                pyantz.jobs.testing.nop.do_nothing

        """
        return serialize_function(fn)


class JobWithContext(JobConfig):
    """Job to be run along with its variables in scope."""

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, Any] | None = None
    """The variables in scope of the job, used to fill in ``%{name}`` references
    in its parameters (and in its ``job_id``, ``name`` and ``depends_on``)."""

    @model_validator(mode="before")
    @classmethod
    def _update_ids_in_hyper_parameters(cls, data: Any) -> Any:  # noqa: ANN401
        """Update ids in the "hyper params" (like id, name, depends_on).

        This happens before validation, so the resolved values are validated
        like any value given directly.

        Args:
            data: the raw data being validated.

        Returns:
            Any: the data with variables resolved in ``job_id``, ``name`` and
            ``depends_on``; anything which isn't a mapping is returned unchanged.

        Raises:
            ValueError: if a variable refers to itself (directly or not).

        Example:
            .. testcode::

                from pyantz.infrastructure.config import JobWithContext

                job = JobWithContext.model_validate(
                    {
                        "name": "fit_%{model}",
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                        "variables": {"model": "linear"},
                    }
                )
                print(job.name)

            .. testoutput::

                fit_linear

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
        config_possibly_without_context: JobConfig | VirtualJobConfig,
    ) -> JobWithContext:
        """Create a JobWithContext from another job config.

        The other job config may be the parent class or could be an instance
        of this class.

        Args:
            config_possibly_without_context (JobConfig): some configuration

        Returns:
            JobWithContext: job as defined, with default variables if not present

        Raises:
            pydantic.ValidationError: if the configuration isn't a valid job.

        Example:
            .. testcode::

                from pyantz.infrastructure.config import JobConfig, JobWithContext

                job = JobConfig(
                    function="pyantz.jobs.testing.nop.do_nothing", parameters={}
                )
                with_context = JobWithContext.from_config(job)
                print(with_context.job_id == job.job_id, with_context.variables)

            .. testoutput::

                True None

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
        """Create a JobWithContext inheriting parent variables.

        Args:
            parent_context: the variables of the parent; this job's own variables
                take precedence over them.

        Returns:
            JobWithContext: a copy of this job with the combined variables.

        Raises:
            None.

        Example:
            .. testcode::

                from pyantz.infrastructure.config import JobWithContext

                job = JobWithContext(
                    function="pyantz.jobs.testing.nop.do_nothing",
                    parameters={},
                    variables={"a": "mine"},
                )
                print(job.inherit_context({"a": "parent", "b": "parent"}).variables)

            .. testoutput::

                {'a': 'mine', 'b': 'parent'}

        """
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
    """Make a job based on a user provided configuration.

    The job is virtual if its ``virtual`` key says so or, without one, if its
    ``function`` is marked with
    :func:`~pyantz.infrastructure.config.mark_virtual`.

    Args:
        config: a job configuration (returned unchanged) or a mapping describing
            one.

    Returns:
        JobConfig | VirtualJobConfig: the validated job.

    Raises:
        TypeError: if ``config`` isn't a mapping or job configuration.
        ValueError: if ``config`` has no ``function``, or it can't be imported.
        pydantic.ValidationError: if ``config`` isn't a valid job.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.job import make_job

            job = make_job(
                {
                    "function": "pyantz.virtual.add_variables.AddVariables",
                    "parameters": {"variables": {}},
                }
            )
            print(type(job).__name__)

        .. testoutput::

            VirtualJobConfig

    """
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
