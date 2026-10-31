"""Compile virtual jobs to 'real' jobs."""

from __future__ import annotations

import graphlib
import logging
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config.abstract_job import AbstractJobConfig
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
    """Compile any virtual jobs to concrete jobs.

    The jobs are compiled from the last to the first in dependency order. A
    virtual job consumes the (compiled) jobs which depend on it, directly or not,
    and is replaced by what it compiles them into. Jobs nested in the parameters
    of a job (such as the branches of ``if_else``) are compiled too.

    Args:
        jobs: the jobs of a pipeline, virtual or not.

    Returns:
        list[RealJobConfig]: the concrete jobs.

    Raises:
        ValueError: if job ids are repeated, the jobs depend on unknown jobs or
            have a dependency cycle.
        pydantic.ValidationError: if a virtual job's parameters are invalid.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig, VirtualJobConfig
            from pyantz.infrastructure.virtual import compile_virtual

            add_x = VirtualJobConfig(
                job_id="add_x",
                function="pyantz.virtual.add_variables.AddVariables",
                parameters={"variables": {"x": 1}},
            )
            job = JobConfig(
                depends_on={"add_x"},
                function="pyantz.jobs.testing.nop.do_nothing",
                parameters={},
            )
            (wrapper,) = compile_virtual([add_x, job])
            (inner,) = wrapper.parameters["jobs"]
            print(wrapper.function.__name__, inner.depends_on)

        .. testoutput::

            run_jobs_in_context set()

    """
    _check_unique_ids(jobs)

    # uncompiled lookup tables

    virtual_job_lookup = {job.job_id: job for job in jobs if job.virtual}
    real_job_lookup = {job.job_id: job for job in jobs if not job.virtual}

    graph = {job.job_id: job.depends_on or set[str]() for job in jobs}
    try:
        compilation_order = reversed(
            list(graphlib.TopologicalSorter(graph).static_order()),
        )
    except graphlib.CycleError as exc:
        msg = f"Dependency cycle: {' -> '.join(exc.args[1])}"
        raise ValueError(msg) from exc

    logging.getLogger(__name__).debug(
        "Compiling %d job(s), %d of them virtual",
        len(jobs),
        len(virtual_job_lookup),
    )
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
        """Look up a job by id from either the real or virtual lookup tables.

        Args:
            job_id: the id of the job.

        Returns:
            AnyJobConfig: the job, as given (not compiled).

        Raises:
            ValueError: if no job has the id.

        """
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

        Args:
            job_id: the id of the job whose dependents to take.

        Returns:
            list[RealJobConfig]: the compiled jobs depending on ``job_id``,
            directly or not.

        Raises:
            None.

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

    logging.getLogger(__name__).debug(
        "Compiled %d job(s) into %d concrete job(s)", len(jobs), len(compiled_jobs)
    )
    return compiled_jobs


def _check_unique_ids(jobs: list[AnyJobConfig]) -> None:
    """Raise a ValueError if any job id is used by more than one job.

    Args:
        jobs: the jobs to check.

    Returns:
        None.

    Raises:
        ValueError: if a job id is repeated.

    """
    counts = Counter(job.job_id for job in jobs)
    duplicates = sorted(job_id for job_id, count in counts.items() if count > 1)
    if duplicates:
        msg = f"Duplicate job_id(s): {duplicates}"
        raise ValueError(msg)


def _compile_parameters(jobs: list[RealJobConfig]) -> list[RealJobConfig]:
    """Apply parameter compilation to every job in the list.

    Args:
        jobs: the concrete jobs.

    Returns:
        list[RealJobConfig]: the jobs with the jobs nested in their parameters
        compiled.

    Raises:
        ValueError: if nested jobs can't be compiled (see :func:`compile_virtual`).

    """
    return [_compile_parameters_singular(job) for job in jobs]


def _compile_parameters_singular(job: RealJobConfig) -> RealJobConfig:
    """Expand job-typed parameters within a single job config.

    Some jobs (e.g. ``if_else``, ``pipeline_expansion``) hold other jobs as
    parameters.  This function locates those nested job configs and ensures
    virtual ones are compiled too.

    Args:
        job: the concrete job.

    Returns:
        RealJobConfig: the job with its nested jobs compiled; unchanged if its
        function has no registered parameters model.

    Raises:
        ValueError: if nested jobs can't be compiled (see :func:`compile_virtual`).

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
        logging.getLogger(__name__).debug(
            "Compiling job in parameter %s of job %s", parm_job_field, job.job_id
        )
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
        logging.getLogger(__name__).debug(
            "Compiling %d job(s) in parameter %s of job %s",
            len(sub_jobs),
            multi_parm_job_field,
            job.job_id,
        )
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

    Args:
        possible_job: a job config (returned unchanged) or a value which may
            describe one.

    Returns:
        AnyJobConfig | None: the job, or None if the value isn't one.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.virtual.compile import _try_to_validate_job

            job = {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}
            print(type(_try_to_validate_job(job)).__name__)
            print(_try_to_validate_job({"not": "a job"}))

        .. testoutput::

            JobConfig
            None

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
    except (ValidationError, TypeError, ValueError):
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

    Args:
        job: the job to compile.
        dep_jobs: the compiled jobs depending on ``job``.
        virtual_ids: the ids of every virtual job of the pipeline.

    Returns:
        list[RealJobConfig]: for a concrete job, the job followed by
        ``dep_jobs``; for a virtual job, what it compiles to.

    Raises:
        pydantic.ValidationError: if a virtual job's parameters are invalid.

    """
    if not job.virtual:
        return [job, *dep_jobs]
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

    logging.getLogger(__name__).debug(
        "Compiling virtual job %s over %d dependent job(s)",
        virtual_id,
        len(cleaned_dep_jobs),
    )
    result = job.compile_virtual(cleaned_dep_jobs)
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

    Args:
        job: the concrete job.

    Returns:
        tuple[Iterable[str], Iterable[str]] | None: the names of the parameters
        holding a job and of those holding jobs, or None if the job's function
        has no registered parameters model.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig
            from pyantz.infrastructure.virtual.compile import (
                _find_joblike_parameters_with_model,
            )

            if_else = "pyantz.jobs.branching.if_else.if_else"
            job = JobConfig(function=if_else, parameters={})
            single, iterable = _find_joblike_parameters_with_model(job)
            print(sorted(single), sorted(iterable))

        .. testoutput::

            ['if_false', 'if_true'] []

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
    """Return True for non-empty iterables which aren't strings or mappings.

    Args:
        value: the value to check.

    Returns:
        bool: True if ``value`` is a non-empty iterable other than ``str``,
        ``bytes`` or a mapping.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.virtual.compile import _is_non_empty_iterable

            print([_is_non_empty_iterable(v) for v in ([1], [], "ab", {"a": 1})])

        .. testoutput::

            [True, False, False, False]

    """
    return (
        isinstance(value, Iterable)
        and not isinstance(value, (str, bytes, Mapping))
        and bool(value)  # pyright: ignore[reportUnknownArgumentType]
    )


def _classify_job_annotation(annotation: Any) -> tuple[bool, bool]:  # noqa: ANN401
    """Decide whether a type annotation holds a single job or an iterable of jobs.

    Looks through ``Annotated``, type aliases (like ``JobPipeline``), and unions.

    Args:
        annotation: the type annotation of a parameters model's field.

    Returns:
        tuple[bool, bool]: (holds a single job, holds an iterable of jobs)

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig, JobPipeline
            from pyantz.infrastructure.virtual.compile import _classify_job_annotation

            print(_classify_job_annotation(JobConfig | None))
            print(_classify_job_annotation(JobPipeline))
            print(_classify_job_annotation(list[str]))

        .. testoutput::

            (True, False)
            (False, True)
            (False, False)

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
