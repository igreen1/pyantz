"""Run a sequence of jobs synchronously within the current process.

:func:`run_pipeline` executes jobs one after another, short-circuiting on
the first failure.  It does *not* submit jobs to the queue — all execution
happens inline, which is more efficient for very small, fast steps.

Use this when you want to avoid queue overhead for a tight inner loop, or
when you need to share in-memory state between steps without a file system.
"""

from __future__ import annotations

import logging
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

    jobs: JobPipeline
    """The jobs to run, in order."""

    inter_job_named_pipes: list[str] = Field(default_factory=list)
    """Not implemented: accepted so that existing configurations keep validating,
    but the value is ignored."""


@add_parameters(LocalPipelineParameters)
@no_submit_fn
def run_pipeline(params: LocalPipelineParameters) -> bool:
    """Run the pipeline of jobs sequentially.

    The jobs run in this process, one after another, and inherit the variables of
    this job. The pipeline stops at the first job which fails. The jobs can't
    submit other jobs.

    Args:
        params: the job's parameters, validated as :class:`LocalPipelineParameters`.

    Parameters:
        jobs (JobPipeline): the jobs to run, in order.
        inter_job_named_pipes (list[str]): not implemented; ignored.

    Returns:
        bool: True if every job succeeded, False as soon as one fails (including
        a job which tries to submit another job).

    Raises:
        None: failures of the jobs are reported by returning False.

    Example:
        .. testsetup:: wrappers-local

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: wrappers-local

            import os

            from pyantz.jobs.wrappers.local import run_pipeline

            touch = "pyantz.jobs.testing.touch_file.touch_file"
            success = run_pipeline(
                {
                    "jobs": [
                        {"function": touch, "parameters": {"path": "first.txt"}},
                        {"function": touch, "parameters": {"path": "second.txt"}},
                    ],
                },
                lambda job: None,
            )
            print(success, os.path.exists("first.txt"), os.path.exists("second.txt"))

        .. testoutput:: wrappers-local

            True True True

        .. testcleanup:: wrappers-local

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    def submit_fn(job: JobConfig, parent: Any) -> None:  # noqa: ANN401
        """Raise immediately: submitting jobs from a local pipeline is unsupported.

        Args:
            job: the job which was to be submitted (ignored).
            parent: the id of the submitting job (ignored).

        Returns:
            None: never returns.

        Raises:
            RuntimeError: always.

        """
        del job, parent  # just to say we "used" them
        msg = "Cannot submit jobs from within a local pipeline."
        raise RuntimeError(msg)

    logger = logging.getLogger(__name__)
    logger.debug("Running local pipeline of %d job(s)", len(params.jobs))
    success: bool = True
    for job in params.jobs:
        job_with_parent_context = JobWithContext.from_config(job).inherit_context(
            curr_variables
        )
        if not run_job(job_with_parent_context, submitter_fn=submit_fn):
            logger.debug(
                "Job %s failed, stopping the local pipeline",
                job_with_parent_context.job_id,
            )
            success = False
            break

    return success
