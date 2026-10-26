"""Jobs for running a pipeline over a grid of parameter combinations.

:func:`create_case_matrix` produces a Parquet case-matrix file from a set
of :class:`VariableDefinition` ranges, then :func:`pipeline_expansion`
reads that file and submits one copy of a ``pipeline_template`` per row,
with each row's columns injected as variables.

:func:`pipeline_expansion_with_output_dir` is a convenience wrapper that
also creates per-run output directories and injects ``output_dir`` and
``pipeline_id`` variables.
"""

from __future__ import annotations

import itertools
import math
import os
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, cast

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pyantz.infrastructure.config import (
    JobConfig,
    JobPipeline,
    JobWithContext,
    SubmissionFnType,
    add_parameters,
    no_submit_fn,
)
from pyantz.infrastructure.config.abstract_job import AbstractJobConfig
from pyantz.infrastructure.runner.job_manager import JobVariables

if TYPE_CHECKING:
    from collections.abc import Generator

FLOAT_DECIMALS = 12
"""Values of float ranges are rounded to this many places to hide float noise."""


class CaseMatrixExpansionParams(BaseModel):
    """Parameters to create many pipelines from a case matrix."""

    model_config = ConfigDict(frozen=True)

    case_matrix_parquet: Path
    """Parquet file of the case matrix: one row per pipeline, one column per
    variable."""

    cols_to_exclude: tuple[str, ...] | None = None
    """If provided, these columns will not be read by the job; useful for large
    columns which are only there for human readability."""

    pipeline_template: JobPipeline
    """The jobs to copy for each row of the case matrix."""


class ContinuousRange[S: int | float](BaseModel):
    """Range of values like numpy arange: ``min_value`` up to, excluding, the max."""

    model_config = ConfigDict(frozen=True)

    min_value: S
    """First value of the range."""

    max_value: S
    """End of the range, which is not included."""

    step: S
    """Difference between consecutive values; it must be greater than 0."""

    @model_validator(mode="after")
    def _check_step_is_positive(self) -> Self:
        """Ensure that the range makes progress, instead of looping forever.

        Args:
            None.

        Returns:
            Self: the validated range.

        Raises:
            ValueError: if ``step`` isn't greater than 0.

        """
        if self.step <= 0:  # type: ignore[operator]
            msg = f"step must be greater than 0, got {self.step}"
            raise ValueError(msg)
        return self

    def get_values(self) -> Generator[S]:
        """Generate values from this range.

        Each value is computed as ``min_value + i * step`` (rather than by repeatedly
        adding the step) so floating point errors don't build up.

        Args:
            None.

        Yields:
            S: each value from ``min_value`` up to, excluding, ``max_value``; float
            values are rounded to :data:`FLOAT_DECIMALS` places.

        Returns:
            Generator[S]: the values of the range.

        Raises:
            None.

        Example:
            .. testcode::

                from pyantz.jobs.branching.case_matrix import ContinuousRange

                ints = ContinuousRange(min_value=0, max_value=10, step=3)
                floats = ContinuousRange(min_value=0.0, max_value=0.3, step=0.1)
                print(list(ints.get_values()), list(floats.get_values()))

            .. testoutput::

                [0, 3, 6, 9] [0.0, 0.1, 0.2]

        """
        # the epsilon stops 0.7/0.1-style rounding noise from including the max
        count = math.ceil((self.max_value - self.min_value) / self.step - 1e-9)  # type: ignore[operator]  # ty: ignore[unsupported-operator]
        for index in range(max(count, 0)):
            value = self.min_value + index * self.step  # type: ignore[operator]  # ty: ignore[unsupported-operator]
            yield round(value, FLOAT_DECIMALS) if isinstance(value, float) else value  # type: ignore[misc]  # ty: ignore[invalid-yield]


class DiscreteRange[S](BaseModel):
    """Range of values defined by the user."""

    model_config = ConfigDict(frozen=True)

    possible_values: list[S]
    """The values, used in the order given, with repeated values removed."""

    @field_validator("possible_values", mode="after")
    @classmethod
    def _remove_repeats(cls, values: list[S]) -> list[S]:
        """Drop repeated values keeping the first of each (works for unhashable).

        Args:
            values: the values given by the user.

        Returns:
            list[S]: the values without repeats, in their original order.

        Raises:
            None.

        """
        unique: list[S] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique

    def get_values(self) -> Generator[S]:
        """Generate values from the user defined range.

        Args:
            None.

        Yields:
            S: each of ``possible_values``, in order.

        Returns:
            Generator[S]: the values of the range.

        Raises:
            None.

        Example:
            .. testcode::

                from pyantz.jobs.branching.case_matrix import DiscreteRange

                values = DiscreteRange(possible_values=["b", "a", "b"]).get_values()
                print(list(values))

            .. testoutput::

                ['b', 'a']

        """
        yield from self.possible_values


class VariableDefinition(BaseModel):
    """Defines how to create a range of values for the case matrix."""

    range: ContinuousRange[Any] | DiscreteRange[Any]
    """The values of the variable: a :class:`ContinuousRange` (``min_value``,
    ``max_value``, ``step``) or a :class:`DiscreteRange` (``possible_values``)."""


class CaseMatrixCreator(BaseModel):
    """Parameters to create a case matrix from a set of variables.

    Produces the cartesian products (aka all possible permutations) of the variables
    to create an expansive dense case matrix.
    """

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, VariableDefinition] = Field(min_length=1)
    """The variables, by name; each becomes a column of the case matrix."""

    save_file: str
    """Parquet file to save the case matrix to."""


class CaseMatrixRunSetup(CaseMatrixExpansionParams):
    """Create a case matrix and provide each sub-pipeline with an output directory."""

    output_dir: str
    """Root path for all the output directories."""


@add_parameters(CaseMatrixRunSetup)
def pipeline_expansion_with_output_dir(
    params: CaseMatrixRunSetup,
    submit_fn: SubmissionFnType,
) -> bool:
    """Add variables `output_dir` and `pipeline_id` for each child pipeline.

    Like :func:`pipeline_expansion`, but each pipeline also gets its own output
    directory ``<output_dir>/run_<pipeline_id>``, created before its jobs are
    submitted and given to them in the ``output_dir`` variable. When this job runs
    inside another expanded pipeline, the ids of the enclosing pipelines are kept
    as ``parent_pipeline_id``, ``parent_parent_pipeline_id`` and so on.

    Args:
        params: the job's parameters, validated as :class:`CaseMatrixRunSetup`.
        submit_fn: function to submit the jobs of the pipelines with.

    Parameters:
        case_matrix_parquet (Path): parquet file of the case matrix.
        cols_to_exclude (tuple[str, ...] | None): columns not to read. Defaults
            to None.
        pipeline_template (JobPipeline): the jobs to copy for each row.
        output_dir (str): root directory of the pipelines' output directories.

    Returns:
        bool: True once every pipeline is submitted.

    Raises:
        OSError: if an output directory can't be created.
        polars.exceptions.PolarsError: if the case matrix can't be read, e.g., it
            doesn't exist.

    Example:
        .. testsetup:: branching-expansion-dirs

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: branching-expansion-dirs

            import os

            import polars as pl

            from pyantz.jobs.branching.case_matrix import (
                pipeline_expansion_with_output_dir,
            )

            pl.DataFrame({"speed": [1, 2]}).write_parquet("cases.parquet")
            submitted = []
            pipeline_expansion_with_output_dir(
                {
                    "case_matrix_parquet": "cases.parquet",
                    "output_dir": "results",
                    "pipeline_template": [
                        {
                            "function": "pyantz.jobs.testing.nop.do_nothing",
                            "parameters": {},
                        },
                    ],
                },
                submitted.append,
            )
            print(sorted(os.listdir("results")))
            print([job.variables["output_dir"] for job in submitted])

        .. testoutput:: branching-expansion-dirs

            ['run_0', 'run_1']
            ['results/run_%{pipeline_id}', 'results/run_%{pipeline_id}']

        .. testcleanup:: branching-expansion-dirs

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    output_dir = Path(params.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # if a pipeline runs in a pipeline running in a pipeline
    # we want it to have pipeline_id, its parent pipeline id, and its "grand parent" id
    # to do this, we look at our current context
    # if, in our current context, we are in a pipeline
    # we create variables like "parent_pipeline_id"
    # rather than "grandparent", we just keep prepending parent for simplicity
    # so great-grand-parent pipeline id = parent_parent_parent_pipeline_id
    parent_variables = JobVariables.get()
    if parent_variables:
        parent_pipelines = {
            var: value
            for var, value in parent_variables.items()
            if var.endswith("pipeline_id")
        }
    else:
        parent_pipelines = {}
    new_variables = {
        "parent_" + pipeline_id_name: pipeline_id_val
        for pipeline_id_name, pipeline_id_val in parent_pipelines.items()
    }

    def output_dir_submit(child_job: JobConfig) -> None:
        """Wrap submit_fn to inject output_dir into each child job.

        Args:
            child_job: a job of a cloned pipeline, holding its ``pipeline_id``.

        Returns:
            None.

        Raises:
            OSError: if the pipeline's output directory can't be created.

        """
        if hasattr(child_job, "variables") and "pipeline_id" in child_job.variables:  # type: ignore  # noqa: PGH003
            pipeline_id: int = child_job.variables["pipeline_id"]  # type: ignore  # noqa: PGH003
            run_dir = output_dir / f"run_{pipeline_id}"
            run_dir.mkdir(parents=True, exist_ok=True)

        wrapped_job = JobWithContext.from_config(child_job).inherit_context(
            {
                # the job's own variables (like its pipeline_id) still take priority
                **new_variables,
                "output_dir": os.fspath(output_dir / "run_%{pipeline_id}"),
            }
        )
        submit_fn(wrapped_job)

    pipeline_params = CaseMatrixExpansionParams(
        case_matrix_parquet=params.case_matrix_parquet,
        cols_to_exclude=params.cols_to_exclude,
        pipeline_template=params.pipeline_template,
    )

    return pipeline_expansion(pipeline_params.model_dump(), output_dir_submit)


@add_parameters(CaseMatrixCreator)
@no_submit_fn
def create_case_matrix(
    params: CaseMatrixCreator,
) -> bool:
    """Create a case matrix as a cartesian product of the variables.

    The case matrix has a column for each variable and a row for each combination
    of their values. The first variable changes slowest.

    Args:
        params: the job's parameters, validated as :class:`CaseMatrixCreator`.

    Parameters:
        variables (Mapping[str, VariableDefinition]): the variables, by name,
            each with a ``range``: either ``min_value``, ``max_value`` and
            ``step`` or ``possible_values``.
        save_file (str): parquet file to save the case matrix to.

    Returns:
        bool: True once the case matrix is saved.

    Raises:
        polars.exceptions.PolarsError: if the parquet can't be written.
        OSError: if the parquet's directory doesn't exist.

    Example:
        .. testsetup:: branching-create-matrix

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: branching-create-matrix

            import polars as pl

            from pyantz.jobs.branching.case_matrix import create_case_matrix

            create_case_matrix(
                {
                    "variables": {
                        "size": {"range": {"possible_values": ["small", "large"]}},
                        "speed": {
                            "range": {"min_value": 1, "max_value": 4, "step": 1},
                        },
                    },
                    "save_file": "cases.parquet",
                },
                lambda job: None,
            )
            for row in pl.read_parquet("cases.parquet").rows():
                print(row)

        .. testoutput:: branching-create-matrix

            ('small', 1)
            ('small', 2)
            ('small', 3)
            ('large', 1)
            ('large', 2)
            ('large', 3)

        .. testcleanup:: branching-create-matrix

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    variables: list[pl.LazyFrame] = [
        pl.DataFrame({variable_name: list(var_def.range.get_values())}).lazy()
        for variable_name, var_def in params.variables.items()
    ]
    left = variables[0]
    for right in variables[1:]:
        left = left.join(
            right,
            how="cross",
            maintain_order="left_right",
        )

    left.sink_parquet(params.save_file)

    return True


@add_parameters(CaseMatrixExpansionParams)
def pipeline_expansion(
    params: CaseMatrixExpansionParams,
    submit_fn: SubmissionFnType,
) -> bool:
    """Submit a set of pipelines based on the case matrix.

    For each row of the case matrix, a copy of ``pipeline_template`` is submitted
    with the row's columns as variables, plus ``pipeline_id`` (0, 1, ...). The
    copies' jobs get new ids. If the template's jobs don't depend on each other,
    each copy runs its jobs in the order given.

    Args:
        params: the job's parameters, validated as
            :class:`CaseMatrixExpansionParams`.
        submit_fn: function to submit the jobs of the pipelines with.

    Parameters:
        case_matrix_parquet (Path): parquet file of the case matrix.
        cols_to_exclude (tuple[str, ...] | None): columns not to read. Defaults
            to None.
        pipeline_template (JobPipeline): the jobs to copy for each row.

    Returns:
        bool: True once every pipeline is submitted.

    Raises:
        polars.exceptions.PolarsError: if the case matrix can't be read, e.g., it
            doesn't exist or lacks an excluded column.

    Example:
        .. testsetup:: branching-expansion

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: branching-expansion

            import polars as pl

            from pyantz.jobs.branching.case_matrix import pipeline_expansion

            pl.DataFrame({"speed": [1, 2]}).write_parquet("cases.parquet")
            submitted = []
            pipeline_expansion(
                {
                    "case_matrix_parquet": "cases.parquet",
                    "pipeline_template": [
                        {
                            "function": "pyantz.jobs.testing.nop.do_nothing",
                            "parameters": {"out": "speed_%{speed}.txt"},
                        },
                    ],
                },
                submitted.append,
            )
            for job in submitted:
                print(job.variables)

        .. testoutput:: branching-expansion

            {'speed': 1, 'pipeline_id': 0}
            {'speed': 2, 'pipeline_id': 1}

        .. testcleanup:: branching-expansion

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    case_matrix = pl.scan_parquet(
        params.case_matrix_parquet,
    )

    if params.cols_to_exclude:
        case_matrix = case_matrix.select(pl.exclude(*params.cols_to_exclude))

    pipeline_submit_factory = _pipeline_factory_factory(
        # virtual jobs are compiled away before a job runs
        cast("list[JobConfig]", params.pipeline_template)
    )
    for sub_matrix in case_matrix.collect_batches():
        for row_entry in sub_matrix.iter_rows(named=True):
            pipeline_submitter = pipeline_submit_factory(row_entry)
            pipeline_submitter(submit_fn)

    return True


type PipelineSubmitter = Callable[[SubmissionFnType], None]
"""Function which accepts a submit function and submits a pipeline."""


def _nested_jobs(value: Any) -> list[Any]:  # noqa: ANN401
    """Find the job configs (objects or raw dicts) inside *value*, at any depth.

    A raw dict counts as a job if it has a ``function`` key.

    Args:
        value: the value to search, such as a job's parameters.

    Returns:
        list[Any]: the jobs found, each followed by the jobs nested in it.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.jobs.branching.case_matrix import _nested_jobs

            branch = {"function": "x.y.z", "job_id": "inner", "parameters": {}}
            found = _nested_jobs({"if_true": branch, "others": [1, "two"]})
            print([job["job_id"] for job in found])

        .. testoutput::

            ['inner']

    """
    if isinstance(value, AbstractJobConfig):
        return [value, *_nested_jobs(value.parameters)]
    if isinstance(value, Mapping):
        found: list[Any] = [value] if "function" in value else []
        for item in value.values():
            found.extend(_nested_jobs(item))
        return found
    if isinstance(value, (list, tuple)):
        return [job for item in value for job in _nested_jobs(item)]
    return []


def _rewrite_ids(value: Any, id_map: Mapping[str, str]) -> Any:  # noqa: ANN401
    """Replace job ids and the dependencies on them, in the jobs nested in *value*.

    Args:
        value: the value to rewrite, such as a job's parameters.
        id_map: old job ids mapped to their new ids; ids not in it are kept.

    Returns:
        Any: a copy of ``value`` with the ids replaced.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.jobs.branching.case_matrix import _rewrite_ids

            jobs = [
                {"function": "x.y.z", "job_id": "a", "parameters": {}},
                {"function": "x.y.z", "depends_on": ["a"], "parameters": {}},
            ]
            for job in _rewrite_ids(jobs, {"a": "new"}):
                print(job.get("job_id"), job.get("depends_on"))

        .. testoutput::

            new None
            None ['new']

    """
    if isinstance(value, AbstractJobConfig):
        return value.model_copy(
            update={
                "job_id": id_map.get(value.job_id, value.job_id),
                "depends_on": (
                    None
                    if value.depends_on is None
                    else {id_map.get(dep, dep) for dep in value.depends_on}
                ),
                "parameters": _rewrite_ids(value.parameters, id_map),
            },
        )
    if isinstance(value, Mapping):
        result = {key: _rewrite_ids(item, id_map) for key, item in value.items()}
        if "function" in result:
            old_id = result.get("job_id")
            if isinstance(old_id, str):
                result["job_id"] = id_map.get(old_id, old_id)
            if isinstance(result.get("depends_on"), (list, tuple, set)):
                result["depends_on"] = [
                    id_map.get(dep, dep) for dep in result["depends_on"]
                ]
        return result
    if isinstance(value, (list, tuple)):
        return type(value)(_rewrite_ids(item, id_map) for item in value)
    return value


def _regenerate_nested_ids(parameters: Any) -> Any:  # noqa: ANN401
    """Give every job nested in *parameters* a new id, keeping their dependencies.

    Jobs in a template are cloned for every row, so nested jobs with fixed ids would
    collide in the queue. Dependencies between the nested jobs follow their new ids.
    Ids written as templates (containing ``%{``) are left alone as variables make
    them unique per clone.

    Args:
        parameters: the parameters of a job of the template.

    Returns:
        Any: the parameters with new ids (``parameters`` itself if it has no
        nested jobs with fixed ids).

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.jobs.branching.case_matrix import _regenerate_nested_ids

            params = {"if_true": {"function": "x.y.z", "job_id": "a", "parameters": {}}}
            print(_regenerate_nested_ids(params)["if_true"]["job_id"] != "a")

        .. testoutput::

            True

    """
    old_ids = {
        nested.job_id if isinstance(nested, AbstractJobConfig) else nested.get("job_id")
        for nested in _nested_jobs(parameters)
    }
    id_map = {
        old_id: str(uuid.uuid4())
        for old_id in old_ids
        if isinstance(old_id, str) and "%{" not in old_id
    }
    return _rewrite_ids(parameters, id_map) if id_map else parameters


def _pipeline_factory_factory(
    pipeline_template: list[JobConfig],
) -> Callable[[Mapping[str, Any]], PipelineSubmitter]:
    """Return a factory that clones a pipeline template for a set of variables.

    Each call to the returned factory produces a fresh copy of
    ``pipeline_template`` with new UUIDs, chained dependencies, and the
    supplied variable mapping injected into every job.

    Args:
        pipeline_template: The list of
            :class:`~pyantz.infrastructure.config.job.JobConfig`
            objects to clone for each case.

    Returns:
        A callable that accepts a variable mapping and returns a
        ``PipelineSubmitter`` closure.  Calling that closure with a
        ``SubmissionFnType`` enqueues the cloned pipeline.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig
            from pyantz.jobs.branching.case_matrix import _pipeline_factory_factory

            template = [
                JobConfig(function="pyantz.jobs.testing.nop.do_nothing", parameters={}),
                JobConfig(function="pyantz.jobs.testing.nop.do_nothing", parameters={}),
            ]
            create_pipeline = _pipeline_factory_factory(template)
            submitted = []
            create_pipeline({"x": 1})(submitted.append)
            first, second = submitted
            print(second.depends_on == {first.job_id}, first.variables)

        .. testoutput::

            True {'x': 1, 'pipeline_id': 0}

    """
    # get the original ids to erase them
    ids_in_pipeline = {job.job_id for job in pipeline_template}

    # old id -> id for this clone, rebuilt for every clone
    def reset_job_template(job: JobConfig, id_map: Mapping[str, str]) -> JobConfig:
        """Give the job a fresh id, pointing its dependencies at the new ids.

        Dependencies on jobs outside of the template are kept, and jobs nested in the
        parameters (like the branches of an `if_else`) get new ids too.

        Args:
            job: a job of the template.
            id_map: ids of the template's jobs mapped to their ids in this clone.

        Returns:
            JobConfig: the job with its new ids.

        Raises:
            KeyError: if the job isn't in ``id_map``.

        """
        return job.model_copy(
            update={
                "job_id": id_map[job.job_id],
                "depends_on": {
                    id_map.get(dep, dep) for dep in (job.depends_on or set[str]())
                },
                "parameters": _regenerate_nested_ids(job.parameters),
            }
        )

    # if the template says nothing about the order of its jobs, run them in list order
    template_has_structure = any(
        dep in ids_in_pipeline
        for job in pipeline_template
        for dep in (job.depends_on or set[str]())
    )

    def string_pipeline(pipeline: list[JobConfig]) -> list[JobConfig]:
        """Add sequential dependencies so jobs execute in list order.

        Args:
            pipeline: the jobs, in the order they should run.

        Returns:
            list[JobConfig]: the jobs, each depending on the one before it.

        Raises:
            None.

        """
        prev: None | JobConfig = None

        def transform(curr: JobConfig) -> JobConfig:
            """Chain curr to depend on prev and advance the prev pointer.

            Args:
                curr: the next job of the pipeline.

            Returns:
                JobConfig: ``curr`` depending on the previous job too.

            Raises:
                None.

            """
            nonlocal prev
            updated = curr.model_copy(
                update={
                    "depends_on": {
                        *(curr.depends_on or set[str]()),
                        *([prev.job_id] if prev else []),
                    }
                }
            )
            prev = updated
            return updated

        return [transform(curr) for curr in pipeline]

    def add_variables(
        pipeline: list[JobConfig],
        variables: Mapping[str, Any],
    ) -> list[JobConfig]:
        """Inject *variables* into every job as inherited context.

        Args:
            pipeline: the jobs.
            variables: the variables to add; the jobs' own variables take
                precedence.

        Returns:
            list[JobConfig]: the jobs, with their variables.

        Raises:
            None.

        """
        return [
            JobWithContext.from_config(job).inherit_context(variables)
            for job in pipeline
        ]

    pipeline_id_counter = itertools.count()

    def create_pipeline(pipeline_vars: Mapping[str, Any]) -> PipelineSubmitter:
        """Clone the template, wire it up, and bind the given variable row.

        Args:
            pipeline_vars: the variables of this clone (a row of a case matrix);
                ``pipeline_id`` is added to them.

        Returns:
            PipelineSubmitter: function which submits the cloned jobs.

        Raises:
            None.

        """
        # first, create a "clone" of our pipeline, which requires wiping the ids
        id_map = {job.job_id: str(uuid.uuid4()) for job in pipeline_template}
        child_pipeline = [reset_job_template(job, id_map) for job in pipeline_template]
        # then, if the template has no structure of its own, run the jobs in order
        if not template_has_structure:
            child_pipeline = string_pipeline(child_pipeline)
        # now add our variables to the child pipeline
        # first, update our pipeline id!
        pipeline_id = next(pipeline_id_counter)
        pipeline_vars = {**pipeline_vars, "pipeline_id": pipeline_id}
        child_pipeline = add_variables(child_pipeline, pipeline_vars)

        # not make our closure
        def submit_pipeline(submit_fn: SubmissionFnType) -> None:
            """Enqueue all cloned jobs in order.

            Args:
                submit_fn: function to submit each job with.

            Returns:
                None.

            Raises:
                None.

            """
            for job in child_pipeline:
                submit_fn(job)

        return submit_pipeline

    return create_pipeline
