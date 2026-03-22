"""Run pipelines from a case matrix."""

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import (
    JobConfig,
    JobWithContext,
    SubmissionFnType,
    add_parameters,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


class CaseMatrixExpansionParams(BaseModel):
    """Parameters to create many pipelines from a case matrix."""

    model_config = ConfigDict(frozen=True)

    case_matrix_parquet: Path

    # if provided, these columns will not be read by the job
    # useful if you have large columns just for human readability
    cols_to_exclude: tuple[str] | None = None

    pipeline_template: list[JobConfig]


@add_parameters(CaseMatrixExpansionParams)
def pipeline_expansion(
    params: CaseMatrixExpansionParams, submit_fn: SubmissionFnType
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
                "job_id": uuid.uuid4(),
                "depends_on": (
                    dep for dep in (job.depends_on or []) if dep not in ids_in_pipeline
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
                    "depends_on": [*(curr.depends_on or []), *([prev] if prev else [])]
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
