"""Jobs for repeating a pipeline a fixed number of times.

:func:`local_for_loop` runs a sequence of jobs synchronously N times in
the current process.  All jobs in the inner pipeline share the same
variable context from the enclosing scope.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import (
    JobPipeline,
    JobWithContext,
    SubmissionFnType,
    add_parameters,
)
from pyantz.infrastructure.runner.job_manager import (
    JobVariables,
    run_job_no_parent_wrapper,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Final


class LocalForLoopParams(BaseModel):
    """Run a loop of jobs locally."""

    model_config = ConfigDict(frozen=True)

    num_iterations: int

    jobs: JobPipeline


@add_parameters(LocalForLoopParams)
def local_for_loop(params: LocalForLoopParams, submit_fn: SubmissionFnType) -> bool:
    """Run a series of jobs locally for a set of iterations."""
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    for _iter in range(params.num_iterations):
        for job in params.jobs:
            job_ctx = JobWithContext.from_config(job).inherit_context(curr_variables)
            if not run_job_no_parent_wrapper(job_ctx, submit_fn):
                # stop everything: later jobs and iterations must not run
                return False

    return True
