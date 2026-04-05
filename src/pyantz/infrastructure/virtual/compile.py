"""Compile virtual jobs to 'real' jobs."""

import graphlib
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, TypeAliasType, cast, get_args, get_origin

from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config.abtrast_job import AbstractJobConfig
from pyantz.infrastructure.config.parameters.decorators import get_parameters
from pyantz.infrastructure.config.pipeline import JobPipeline

if TYPE_CHECKING:
    from pyantz.infrastructure.config import (
        JobConfig as RealJobConfig,
    )
    from pyantz.infrastructure.config import (
        VirtualJobConfig,
    )

    type AnyJobConfig = RealJobConfig | VirtualJobConfig


def compile_virtual(jobs: list[AnyJobConfig]) -> list[RealJobConfig]:
    """Compile any virtual jobs to concrete jobs."""
    # uncompiled lookup tables

    virtual_job_lookup = {
        job.job_id: cast("VirtualJobConfig", job) for job in jobs if job.virtual
    }
    real_job_lookup = {
        job.job_id: cast("RealJobConfig", job) for job in jobs if not job.virtual
    }

    if not virtual_job_lookup:
        return _compile_parameters([*real_job_lookup.values()])

    def get_uncompiled_job_config(job_id: str) -> AnyJobConfig:
        """Get the job definition from its id."""
        lookup_val = real_job_lookup.get(job_id, virtual_job_lookup.get(job_id))
        if lookup_val is None:
            raise ValueError
        return lookup_val

    graph = {job.job_id: job.depends_on or set[str]() for job in jobs}
    compilation_order = reversed(list(graphlib.TopologicalSorter(graph).static_order()))
    compiled_jobs: list[RealJobConfig] = []

    def get_and_consume_dependencies(job_id: str) -> list[RealJobConfig]:
        """Get jobs and `consume` them by removing them from our compiled scope."""
        nonlocal compiled_jobs
        direct_deps = [
            job for job in compiled_jobs if job_id in (job.depends_on or set())
        ]

        if not direct_deps:
            return []

        # remove direct deps from compiled job scope ("consume" them)
        compiled_jobs = [job for job in compiled_jobs if job not in direct_deps]

        # get indirect dependencies
        indirect_deps = [
            indirect_dep
            for direct_dep in direct_deps
            for indirect_dep in get_and_consume_dependencies(direct_dep.job_id)
        ]

        return [*direct_deps, *indirect_deps]

    for node_to_compile in compilation_order:
        node_def = get_uncompiled_job_config(node_to_compile)
        node_deps = get_and_consume_dependencies(node_to_compile)
        compile_results = _compile_singular(node_def, node_deps)
        compile_results = _compile_parameters(compile_results)
        compiled_jobs.extend(compile_results)

    return compiled_jobs


def _compile_parameters(jobs: list[RealJobConfig]) -> list[RealJobConfig]:
    """Compile the parameters for each job if they are joblike."""
    return [_compile_parameters_singular(job) for job in jobs]


def _compile_parameters_singular(job: RealJobConfig) -> RealJobConfig:
    """Compile the parameters of one job if they are job-like."""
    joblike_parms = _find_joblike_parameters_with_model(job)
    if joblike_parms is None:
        return job
    singular_job_params, iterable_job_params = joblike_parms

    for parm_job_field in singular_job_params:
        sub_job = job.parameters[parm_job_field]
        sub_job_validated: AnyJobConfig | None = _try_to_validate_job(sub_job)
        if sub_job_validated is None:
            continue  # cannot help this parameter out
        job = job.model_copy(
            update={
                "parameters": {
                    **job.parameters,
                    parm_job_field: _compile_singular(sub_job_validated, [])[0],
                },
            },
        )
    for multi_parm_job_field in iterable_job_params:
        sub_jobs = job.parameters[multi_parm_job_field]
        sub_jobs = type(sub_jobs)([_try_to_validate_job(j) for j in sub_jobs])
        job = job.model_copy(
            update={
                "parameters": {
                    **job.parameters,
                    multi_parm_job_field: compile_virtual(sub_jobs),
                },
            },
        )

    return job


def _try_to_validate_job(
    possible_job: Mapping[str, Any] | AnyJobConfig,
) -> AnyJobConfig | None:
    """Try to validate the job if possible, otherwise return None."""
    # import locally to avoid circular imports
    from pyantz.infrastructure.config import (  # noqa: PLC0415
        JobConfig as _RealJobConfig,
    )
    from pyantz.infrastructure.config import (  # noqa: PLC0415
        VirtualJobConfig as _VirtualJobConfig,
    )
    from pyantz.infrastructure.config.job import make_job  # noqa: PLC0415

    if isinstance(possible_job, (_RealJobConfig, _VirtualJobConfig)):
        return possible_job

    try:
        return make_job(possible_job)
    except ValidationError:
        return None


def _compile_singular(
    job: AnyJobConfig, dep_jobs: list[RealJobConfig]
) -> list[RealJobConfig]:
    """Compile the given job.

    Virtual jobs will "consume" this dependencies (they will likely wrap them).
    """
    if not job.virtual:
        return [cast("RealJobConfig", job), *dep_jobs]
    virtual_id = job.job_id
    dep_jobs = [
        real_job.model_copy(
            update={
                "depends_on": {
                    id_ for id_ in (real_job.depends_on or set()) if id_ != virtual_id
                }
            }
        )
        for real_job in dep_jobs
    ]
    result = cast("VirtualJobConfig", job).compile_virtual(dep_jobs)
    return [
        real_job.model_copy(
            update={
                "depends_on": {
                    id_ for id_ in (real_job.depends_on or set()) if id_ != virtual_id
                }
            }
        )
        for real_job in result
    ]


def _find_joblike_parameters_with_model(  # noqa: C901
    job: RealJobConfig,
) -> tuple[Iterable[str], Iterable[str]] | None:
    """Find parameters which appear to be a job.

    Returns a tuple of single jobs and iterable job parameters.
    If not registered, none is returned to signal that this job may
    have job config parameters, but they aren't registered so we can't tell.
    """
    single_job_fields: set[str] = set()
    iterable_job_fields: set[str] = set()
    if isinstance(job.parameters, BaseModel):
        # if parameters have been turned into instance, check types directly
        for field, value in job.parameters.model_dump().items():
            if isinstance(value, AbstractJobConfig):
                single_job_fields.add(field)
            if isinstance(value, Iterable) and all(
                isinstance(subval, AbstractJobConfig)
                for subval in value  # pyright: ignore[reportUnknownVariableType]
            ):
                iterable_job_fields.add(field)
        return single_job_fields, iterable_job_fields

    # if parameters are still a mapping, must check against their parameter "end state"
    # ie., check if the job function has a pyantz parameter connected
    # then check the *class* of the parameter model for the eventual types to be cast
    param_model = get_parameters(job.function)
    if param_model is None:
        return None

    for field, field_type in param_model.model_fields.items():
        type_ = field_type.annotation
        if type_ is None or not isinstance(type_, (type, TypeAliasType)):  # pyright: ignore[reportUnnecessaryIsInstance]
            continue

        if isinstance(type_, TypeAliasType):  # pyright: ignore[reportUnnecessaryIsInstance]
            if type_ is JobPipeline:
                iterable_job_fields.add(field)
            continue
        if issubclass(type_, (AbstractJobConfig,)):
            single_job_fields.add(field)
        if (
            get_origin(type_) is not None
            and isinstance(get_origin(type_), type)
            and issubclass(get_origin(type_), Iterable)  # type: ignore  # noqa: PGH003
            and any(
                issubclass(type_arg, AbstractJobConfig) for type_arg in get_args(type_)
            )
        ):
            iterable_job_fields.add(field)

    return (
        single_job_fields,
        iterable_job_fields,
    )
