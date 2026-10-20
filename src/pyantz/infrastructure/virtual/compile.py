"""Compile virtual jobs to 'real' jobs."""

import graphlib
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeAliasType,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config.abtrast_job import AbstractJobConfig
from pyantz.infrastructure.config.parameters.decorators import get_parameters

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
    _check_unique_ids(jobs)

    # uncompiled lookup tables

    virtual_job_lookup = {
        job.job_id: cast("VirtualJobConfig", job) for job in jobs if job.virtual
    }
    real_job_lookup = {
        job.job_id: cast("RealJobConfig", job) for job in jobs if not job.virtual
    }

    graph = {job.job_id: job.depends_on or set[str]() for job in jobs}
    try:
        compilation_order = reversed(
            list(graphlib.TopologicalSorter(graph).static_order()),
        )
    except graphlib.CycleError as exc:
        msg = f"Dependency cycle: {' -> '.join(exc.args[1])}"
        raise ValueError(msg) from exc

    if not virtual_job_lookup:
        return _compile_parameters([*real_job_lookup.values()])

    unknown_dependencies = {
        job.job_id: sorted(job.depends_on - graph.keys())
        for job in jobs
        if job.depends_on and job.depends_on - graph.keys()
    }
    if unknown_dependencies:
        msg = f"Jobs depend on unknown job ids (job -> missing): {unknown_dependencies}"
        raise ValueError(msg)

    def get_uncompiled_job_config(job_id: str) -> AnyJobConfig:
        """Look up a job by id from either the real or virtual lookup tables."""
        lookup_val = real_job_lookup.get(job_id, virtual_job_lookup.get(job_id))
        if lookup_val is None:
            msg = f"No job with id {job_id!r}"
            raise ValueError(msg)
        return lookup_val

    compiled_jobs: list[RealJobConfig] = []

    def get_and_consume_dependencies(job_id: str) -> list[RealJobConfig]:
        """Return jobs that depend on *job_id* and remove them from compiled_jobs.

        "Consuming" a dependency prevents it from being returned again by a
        later iteration, which would duplicate it in the final list.
        """
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
        compile_results = _compile_singular(
            node_def,
            node_deps,
            virtual_ids=virtual_job_lookup.keys(),
        )
        compile_results = _compile_parameters(compile_results)
        compiled_jobs.extend(compile_results)

    return compiled_jobs


def _check_unique_ids(jobs: list[AnyJobConfig]) -> None:
    """Raise a ValueError if any job id is used by more than one job."""
    counts = Counter(job.job_id for job in jobs)
    duplicates = sorted(job_id for job_id, count in counts.items() if count > 1)
    if duplicates:
        msg = f"Duplicate job_id(s): {duplicates}"
        raise ValueError(msg)


def _compile_parameters(jobs: list[RealJobConfig]) -> list[RealJobConfig]:
    """Apply parameter compilation to every job in the list."""
    return [_compile_parameters_singular(job) for job in jobs]


def _compile_parameters_singular(job: RealJobConfig) -> RealJobConfig:
    """Expand job-typed parameters within a single job config.

    Some jobs (e.g. ``if_else``, ``pipeline_expansion``) hold other jobs as
    parameters.  This function locates those nested job configs and ensures
    virtual ones are compiled too.
    """
    joblike_parms = _find_joblike_parameters_with_model(job)
    if joblike_parms is None:
        return job
    singular_job_params, iterable_job_params = joblike_parms

    for parm_job_field in singular_job_params:
        sub_job = job.parameters.get(parm_job_field)
        if sub_job is None:
            continue  # optional job parameter that wasn't provided
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
        sub_jobs = job.parameters.get(multi_parm_job_field)
        if sub_jobs is None:
            continue  # optional job parameter that wasn't provided
        validated_sub_jobs = [_try_to_validate_job(j) for j in sub_jobs]
        if any(sub_job is None for sub_job in validated_sub_jobs):
            continue  # not all jobs, so cannot help this parameter out
        sub_jobs = type(sub_jobs)(validated_sub_jobs)
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
    """Attempt to parse *possible_job* as a job config; return ``None`` on failure.

    Used when scanning nested parameters: if validation fails the parameter
    is not a job dict and should be left alone.
    """
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
    except ValidationError, TypeError, ValueError:
        return None


def _compile_singular(
    job: AnyJobConfig,
    dep_jobs: list[RealJobConfig],
    virtual_ids: Collection[str] = (),
) -> list[RealJobConfig]:
    """Compile the given job.

    Virtual jobs will "consume" this dependencies (they will likely wrap them).

    The wrapped jobs no longer see other virtual jobs (those never exist at runtime),
    so dependencies on other virtual jobs are moved onto the compiled result. The
    other virtual job then wraps the compiled result when it is compiled, which
    nests the jobs so they receive the effects of every virtual job they depended on.
    """
    if not job.virtual:
        return [cast("RealJobConfig", job), *dep_jobs]
    virtual_id = job.job_id
    other_virtual_ids = set(virtual_ids) - {virtual_id}

    hoisted_dependencies: set[str] = set()
    cleaned_dep_jobs: list[RealJobConfig] = []
    for real_job in dep_jobs:
        original_deps = real_job.depends_on or set()
        hoisted_dependencies |= original_deps & other_virtual_ids
        cleaned_dep_jobs.append(
            real_job.model_copy(
                update={
                    "depends_on": original_deps - other_virtual_ids - {virtual_id},
                },
            ),
        )

    result = cast("VirtualJobConfig", job).compile_virtual(cleaned_dep_jobs)
    return [
        real_job.model_copy(
            update={
                "depends_on": {
                    id_ for id_ in (real_job.depends_on or set()) if id_ != virtual_id
                }
                | hoisted_dependencies,
            },
        )
        for real_job in result
    ]


def _find_joblike_parameters_with_model(
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
        # if parameters have been turned into instance, check the values directly
        for field in type(job.parameters).model_fields:
            value = getattr(job.parameters, field)
            if isinstance(value, AbstractJobConfig):
                single_job_fields.add(field)
            elif _is_non_empty_iterable(value) and all(
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
        is_single, is_iterable = _classify_job_annotation(field_type.annotation)
        if is_single:
            single_job_fields.add(field)
        if is_iterable:
            iterable_job_fields.add(field)

    return (
        single_job_fields,
        iterable_job_fields,
    )


def _is_non_empty_iterable(value: object) -> bool:
    """Return True for non-empty iterables which aren't strings or mappings."""
    return (
        isinstance(value, Iterable)
        and not isinstance(value, (str, bytes, Mapping))
        and bool(value)  # pyright: ignore[reportUnknownArgumentType]
    )


def _classify_job_annotation(annotation: Any) -> tuple[bool, bool]:  # noqa: ANN401
    """Decide whether a type annotation holds a single job or an iterable of jobs.

    Looks through ``Annotated``, type aliases (like ``JobPipeline``), and unions.

    Returns:
        tuple[bool, bool]: (holds a single job, holds an iterable of jobs)

    """
    if isinstance(annotation, TypeAliasType):
        return _classify_job_annotation(annotation.__value__)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return _classify_job_annotation(args[0])
    if origin is Union or origin is UnionType:
        classified = [_classify_job_annotation(arg) for arg in args]
        return (
            any(single for single, _ in classified),
            any(iterable for _, iterable in classified),
        )
    if origin is None:
        is_job = isinstance(annotation, type) and issubclass(
            annotation, AbstractJobConfig
        )
        return is_job, False
    if (
        isinstance(origin, type)
        and issubclass(origin, Iterable)
        and not issubclass(origin, (str, bytes, Mapping))
    ):
        return False, any(
            _classify_job_annotation(arg)[0] for arg in args if arg is not Ellipsis
        )
    return False, False
