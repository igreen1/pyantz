"""Jobs for running a pipeline over a grid of parameter combinations.

:func:`create_case_matrix` produces a Parquet case-matrix file from a set
of :class:`VariableDefinition` ranges, then :func:`pipeline_expansion`
reads that file and submits one copy of a ``pipeline_template`` per row,
with each row's columns injected as variables.

:func:`pipeline_expansion_with_output_dir` is a convenience wrapper that
also creates per-run output directories and injects ``output_dir`` and
``pipeline_id`` variables.
"""

import itertools
import math
import os
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

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
from pyantz.infrastructure.runner.job_manager import JobVariables

if TYPE_CHECKING:
    from collections.abc import Generator

# values of float ranges are rounded to this many places to hide float noise
FLOAT_DECIMALS = 12


class CaseMatrixExpansionParams(BaseModel):
    """Parameters to create many pipelines from a case matrix."""

    model_config = ConfigDict(frozen=True)

    case_matrix_parquet: Path

    # if provided, these columns will not be read by the job
    # useful if you have large columns just for human readability
    cols_to_exclude: tuple[str, ...] | None = None

    pipeline_template: JobPipeline


class ContinuousRange[S: int | float](BaseModel):
    """Range of values like numpy arange: ``min_value`` up to, excluding, the max."""

    model_config = ConfigDict(frozen=True)

    min_value: S

    max_value: S

    step: S

    @model_validator(mode="after")
    def _check_step_is_positive(self) -> Self:
        """Ensure that the range makes progress, instead of looping forever."""
        if self.step <= 0:  # type: ignore[operator]
            msg = f"step must be greater than 0, got {self.step}"
            raise ValueError(msg)
        return self

    def get_values(self) -> Generator[S]:
        """Generate values from this range.

        Each value is computed as ``min_value + i * step`` (rather than by repeatedly
        adding the step) so floating point errors don't build up.
        """
        # the epsilon stops 0.7/0.1-style rounding noise from including the max
        count = math.ceil((self.max_value - self.min_value) / self.step - 1e-9)  # type: ignore[operator]  # ty: ignore[unsupported-operator]
        for index in range(max(count, 0)):
            value = self.min_value + index * self.step  # type: ignore[operator]  # ty: ignore[unsupported-operator]
            yield round(value, FLOAT_DECIMALS) if isinstance(value, float) else value  # type: ignore[misc]  # ty: ignore[invalid-yield]


class DiscreteRange[S](BaseModel):
    """Range of values defined by the user."""

    model_config = ConfigDict(frozen=True)

    # values are used in the order given, with repeated values removed
    possible_values: list[S]

    @field_validator("possible_values", mode="after")
    @classmethod
    def _remove_repeats(cls, values: list[S]) -> list[S]:
        """Drop repeated values keeping the first of each (works for unhashable)."""
        unique: list[S] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique

    def get_values(self) -> Generator[S]:
        """Generate values from the user defined range."""
        yield from self.possible_values


class VariableDefinition(BaseModel):
    """Defines how to create a range of values for the case matrix."""

    range: ContinuousRange[Any] | DiscreteRange[Any]


class CaseMatrixCreator(BaseModel):
    """Parameters to create a case matrix from a set of variables.

    Produces the cartesian products (aka all possible permutations) of the variables
    to create an expansive dense case matrix.
    """

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, VariableDefinition] = Field(min_length=1)

    # parquet file to save to
    save_file: str


class CaseMatrixRunSetup(CaseMatrixExpansionParams):
    """Create a case matrix and provide each sub-pipeline with an output directory."""

    # root path for all the output directories
    output_dir: str


@add_parameters(CaseMatrixRunSetup)
def pipeline_expansion_with_output_dir(
    params: CaseMatrixRunSetup,
    submit_fn: SubmissionFnType,
) -> bool:
    """Add variables `output_dir` and `pipeline_id` for each child pipeline."""
    output_dir = Path(params.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # if a pipeline runs in a pipeline running in a pipeline
    # we want it to have pipeline_id, its parent pipeline id, and its "grand parent" id
    # to do this, we look at our current context
    # if, in our current context, we are in a pipeline
    # we create variables like "parent_pipeline_id"
    # rather than "grandparent", we just keep pre-pending parent for simplicity
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
        """Wrap submit_fn to inject output_dir into each child job."""
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
    """Create a case matrix as a cartesian product of the variables."""
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
    """Submit a set of pipelines based on the case matrix."""
    case_matrix = pl.scan_parquet(
        params.case_matrix_parquet,
    )

    if params.cols_to_exclude:
        case_matrix = case_matrix.select(pl.exclude(*params.cols_to_exclude))

    pipeline_submit_factory = _pipeline_factory_factory(params.pipeline_template)
    for sub_matrix in case_matrix.collect_batches():
        for row_entry in sub_matrix.iter_rows(named=True):
            pipeline_submitter = pipeline_submit_factory(row_entry)
            pipeline_submitter(submit_fn)

    return True


# Function which acceps a submit function and submits a pipeline.
type PipelineSubmitter = Callable[[SubmissionFnType], None]


def _pipeline_factory_factory(
    pipeline_template: list[JobConfig],
) -> Callable[[Mapping[str, Any]], PipelineSubmitter]:
    """Return a factory that clones a pipeline template for a set of variables.

    Each call to the returned factory produces a fresh copy of
    ``pipeline_template`` with new UUIDs, chained dependencies, and the
    supplied variable mapping injected into every job.

    Args:
        pipeline_template: The list of :class:`~pyantz.infrastructure.config.job.JobConfig`
            objects to clone for each case.

    Returns:
        A callable that accepts a variable mapping and returns a
        ``PipelineSubmitter`` closure.  Calling that closure with a
        ``SubmissionFnType`` enqueues the cloned pipeline.
    """
    # get the original ids to erase them
    ids_in_pipeline = {job.job_id for job in pipeline_template}

    def reset_job_template(job: JobConfig) -> JobConfig:
        """Give the job a fresh UUID and drop any intra-template dependency ids."""
        return job.model_copy(
            update={
                "job_id": str(uuid.uuid4()),
                "depends_on": (
                    dep
                    for dep in (job.depends_on or set())
                    if dep not in ids_in_pipeline
                ),
            }
        )

    def string_pipeline(pipeline: list[JobConfig]) -> list[JobConfig]:
        """Add sequential dependencies so jobs execute in list order."""
        prev: None | JobConfig = None

        def transform(curr: JobConfig) -> JobConfig:
            """Chain curr to depend on prev and advance the prev pointer."""
            nonlocal prev
            updated = curr.model_copy(
                update={
                    "depends_on": [
                        *(curr.depends_on or []),
                        *([prev.job_id] if prev else []),
                    ]
                }
            )
            prev = updated
            return updated

        return [transform(curr) for curr in pipeline]

    def add_variables(
        pipeline: list[JobConfig],
        variables: Mapping[str, Any],
    ) -> list[JobConfig]:
        """Inject *variables* into every job as inherited context."""
        return [
            JobWithContext.from_config(job).inherit_context(variables)
            for job in pipeline
        ]

    pipeline_id_counter = itertools.count()

    def create_pipeline(pipeline_vars: Mapping[str, Any]) -> PipelineSubmitter:
        """Clone the template, wire it up, and bind the given variable row."""
        # first, create a "clone" of our pipeline, which requires wiping the ids
        child_pipeline = [reset_job_template(job) for job in pipeline_template]
        # then string it together so the dependencies work right
        child_pipeline = string_pipeline(child_pipeline)
        # now add our variables to the child pipeline
        # first, update our pipeline id!
        pipeline_id = next(pipeline_id_counter)
        pipeline_vars = {**pipeline_vars, "pipeline_id": pipeline_id}
        child_pipeline = add_variables(child_pipeline, pipeline_vars)

        # not make our closure
        def submit_pipeline(submit_fn: SubmissionFnType) -> None:
            """Enqueue all cloned jobs in order."""
            for job in child_pipeline:
                submit_fn(job)

        return submit_pipeline

    return create_pipeline
