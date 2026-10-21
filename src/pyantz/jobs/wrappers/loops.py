"""Jobs for repeating a pipeline a fixed number of times.

:func:`local_for_loop` runs a sequence of jobs synchronously N times in
the current process.  All jobs in the inner pipeline share the same
variable context from the enclosing scope.
"""

from __future__ import annotations

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

    # name of the variable holding the index of the iteration (0, 1, ...) which the
    # jobs can use, for example in a path like `out_%{loop_index}.txt`
    index_variable: str = "loop_index"

    # if true, the loop ends at the first failing job; if false, the rest of the
    # iteration and all later iterations still run, and the loop fails at the end
    stop_on_failure: bool = True


@add_parameters(LocalForLoopParams)
def local_for_loop(params: LocalForLoopParams, submit_fn: SubmissionFnType) -> bool:
    """Run a series of jobs locally for a set of iterations."""
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    success = True
    for index in range(params.num_iterations):
        iteration_variables = {**curr_variables, params.index_variable: index}
        for job in params.jobs:
            job_ctx = JobWithContext.from_config(job).inherit_context(
                iteration_variables,
            )
            if not run_job_no_parent_wrapper(job_ctx, submit_fn):
                # later jobs and iterations must not run, unless asked to go on
                if params.stop_on_failure:
                    return False
                success = False

    return success
