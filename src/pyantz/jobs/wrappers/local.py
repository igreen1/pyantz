"""Jobs to run a set of jobs locally without worrying about submitters.

This is a bit of a workaround to the pyantz "normal" way of doing things,
but it can be more efficient for a series of very small jobs.

It can also be useful for passing data around without using a file system
as it will create and manage a local store of data.
"""

from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import (
    JobConfig,
    JobWithContext,
    add_parameters,
    no_submit_fn,
)
from pyantz.infrastructure.runner.job_manager import JobVariables, run_job

if TYPE_CHECKING:
    from collections.abc import Mapping


class LocalPipelineParameters(BaseModel):
    """Parameters for running jobs sequentially within this job without submitting."""

    model_config = ConfigDict(frozen=True)

    # The job's first parameter will be a dictionary
    jobs: list[JobConfig]

    inter_job_named_pipes: set[str]


@add_parameters(LocalPipelineParameters)
@no_submit_fn
def run_pipeline(params: LocalPipelineParameters) -> bool:
    """Run the pipeline of jobs sequentially."""
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    def submit_fn(job: JobConfig, parent: Any) -> None:  # noqa: ANN401
        del job, parent  # just to say we "used" them
        msg = "Cannot submit jobs from within a local pipeline."
        raise RuntimeError(msg)

    success: bool = True
    for job in params.jobs:
        job_with_parent_context = JobWithContext.from_config(job).inherit_context(
            curr_variables
        )
        if not run_job(job_with_parent_context, submitter_fn=submit_fn):
            success = False
            break

    return success
