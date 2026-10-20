"""Run a sequence of jobs synchronously within the current process.

:func:`run_pipeline` executes jobs one after another, short-circuiting on
the first failure.  It does *not* submit jobs to the queue — all execution
happens inline, which is more efficient for very small, fast steps.

Use this when you want to avoid queue overhead for a tight inner loop, or
when you need to share in-memory state between steps without a file system.
"""

from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, ConfigDict, Field

from pyantz.infrastructure.config import (
    JobConfig,
    JobPipeline,
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
    jobs: JobPipeline

    # Not implemented: accepted so that existing configurations keep validating,
    # but the value is ignored
    inter_job_named_pipes: list[str] = Field(default_factory=list)


@add_parameters(LocalPipelineParameters)
@no_submit_fn
def run_pipeline(params: LocalPipelineParameters) -> bool:
    """Run the pipeline of jobs sequentially."""
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    def submit_fn(job: JobConfig, parent: Any) -> None:  # noqa: ANN401
        """Raise immediately — submitting jobs from a local pipeline is not supported."""
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
