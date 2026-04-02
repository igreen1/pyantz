"""Run pipelines from a case matrix."""

import itertools
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl
from pydantic import BaseModel, ConfigDict

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


class CaseMatrixExpansionParams(BaseModel):
    """Parameters to create many pipelines from a case matrix."""

    model_config = ConfigDict(frozen=True)

    case_matrix_parquet: Path

    # if provided, these columns will not be read by the job
    # useful if you have large columns just for human readability
    cols_to_exclude: tuple[str] | None = None

    pipeline_template: JobPipeline


class ContinuousRange[S: int | float](BaseModel):
    """Range of values like numpy arange."""

    model_config = ConfigDict(frozen=True)

    min_value: S

    max_value: S

    step: S

    def get_values(self) -> Generator[S]:
        """Generate values from this range."""
        curr_value: S = self.min_value
        while curr_value < self.max_value:  # type: ignore[operator]
            yield curr_value
            curr_value += self.step  # type: ignore[assignment,operator] # ty: ignore[unsupported-operator]


class DiscreteRange[S](BaseModel):
    """Range of values defined by the user."""

    model_config = ConfigDict(frozen=True)

    possible_values: set[S]

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

    variables: Mapping[str, VariableDefinition]

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
    id_counter = itertools.count()
    output_dir = Path(params.output_dir)
    output_dir.mkdir(exist_ok=True)

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
        "parent_"+pipeline_id_name: pipeline_id_val
        for pipeline_id_name, pipeline_id_val in parent_pipelines.items()
    }

    def output_dir_submit(child_job: JobConfig) -> None:
        """Submit the job with an additional output_dir variable."""
        id_ = next(id_counter)
        run_dir = output_dir / f"run_{id_}"
        run_dir.mkdir(exist_ok=True)

        wrapped_job = JobWithContext.from_config(child_job).inherit_context(
            {
                **new_variables,
                "pipeline_id": id_,
                "output_dir": run_dir,
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

    for sub_matrix in case_matrix.collect_batches():
        for row_entry in sub_matrix.iter_rows(named=True):
            pipeline_submit_factory = _pipeline_factory_factory(
                params.pipeline_template
            )
            pipeline_submitter = pipeline_submit_factory(row_entry)
            pipeline_submitter(submit_fn)

    return True


# Function which acceps a submit function and submits a pipeline.
type PipelineSubmitter = Callable[[SubmissionFnType], None]


def _pipeline_factory_factory(
    pipeline_template: list[JobConfig],
) -> Callable[[Mapping[str, Any]], PipelineSubmitter]:
    """Create a factory which accepts variables and returns a job config."""
    # get the original ids to erase them
    ids_in_pipeline = {job.job_id for job in pipeline_template}

    def reset_job_template(job: JobConfig) -> JobConfig:
        """Reset the job id and dependencies."""
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
        """Add dependencies in the pipeline so they execute in order."""
        prev: None | JobConfig = None

        def transform(curr: JobConfig) -> JobConfig:
            nonlocal prev
            updated = curr.model_copy(
                update={
                    "depends_on": {
                        *(curr.depends_on or []),
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
        """Add the inherited variables."""
        return [
            JobWithContext.from_config(job).inherit_context(variables)
            for job in pipeline
        ]

    def create_pipeline(pipeline_vars: Mapping[str, Any]) -> PipelineSubmitter:
        # first, create a "clone" of our pipeline, which requires wiping the ids
        child_pipeline = [reset_job_template(job) for job in pipeline_template]
        # then string it together so the dependencies work right
        child_pipeline = string_pipeline(child_pipeline)
        # now add our variables to the child pipeline
        child_pipeline = add_variables(child_pipeline, pipeline_vars)
        # not make our closure
        def submit_pipeline(submit_fn: SubmissionFnType) -> None:
            for job in child_pipeline:
                submit_fn(job)

        return submit_pipeline

    return create_pipeline
