"""Jobs for repeating a pipeline a fixed number of times.

:func:`local_for_loop` runs a sequence of jobs synchronously N times in
the current process.  All jobs in the inner pipeline share the same
variable context from the enclosing scope.
"""

from __future__ import annotations

import logging
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
    """How many times to run the jobs."""

    jobs: JobPipeline
    """The jobs to run in each iteration, in order."""

    index_variable: str = "loop_index"
    """Name of the variable holding the index of the iteration (0, 1, ...) which
    the jobs can use, for example in a path like ``out_%{loop_index}.txt``."""

    stop_on_failure: bool = True
    """If true, the loop ends at the first failing job; if false, the rest of the
    iteration and all later iterations still run, and the loop fails at the end."""


@add_parameters(LocalForLoopParams)
def local_for_loop(params: LocalForLoopParams, submit_fn: SubmissionFnType) -> bool:
    """Run a series of jobs locally for a set of iterations.

    The jobs run in this process and inherit the variables of this job, plus the
    index of the iteration in ``index_variable``. Jobs submitted by the inner jobs
    are passed on to ``submit_fn``.

    Args:
        params: the job's parameters, validated as :class:`LocalForLoopParams`.
        submit_fn: function the inner jobs submit their jobs with.

    Parameters:
        num_iterations (int): how many times to run the jobs.
        jobs (JobPipeline): the jobs to run in each iteration, in order.
        index_variable (str): name of the variable holding the iteration's index.
            Defaults to ``"loop_index"``.
        stop_on_failure (bool): if True, stop at the first failing job; otherwise
            keep going and fail at the end. Defaults to True.

    Returns:
        bool: True if every job of every iteration succeeded, otherwise False.

    Raises:
        None: failures of the jobs are reported by returning False.

    Example:
        .. testsetup:: wrappers-loop

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: wrappers-loop

            import os

            from pyantz.jobs.wrappers.loops import local_for_loop

            success = local_for_loop(
                {
                    "num_iterations": 3,
                    "jobs": [
                        {
                            "function": "pyantz.jobs.testing.touch_file.touch_file",
                            "parameters": {"path": "loop_%{loop_index}.txt"},
                        },
                    ],
                },
                lambda job: None,
            )
            print(success, sorted(f for f in os.listdir() if f.startswith("loop_")))

        .. testoutput:: wrappers-loop

            True ['loop_0.txt', 'loop_1.txt', 'loop_2.txt']

        .. testcleanup:: wrappers-loop

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    logger = logging.getLogger(__name__)
    success = True
    for index in range(params.num_iterations):
        logger.debug(
            "Loop iteration %d of %d (%s=%d)",
            index + 1,
            params.num_iterations,
            params.index_variable,
            index,
        )
        iteration_variables = {**curr_variables, params.index_variable: index}
        for job in params.jobs:
            job_ctx = JobWithContext.from_config(job).inherit_context(
                iteration_variables,
            )
            if not run_job_no_parent_wrapper(job_ctx, submit_fn):
                # later jobs and iterations must not run, unless asked to go on
                logger.debug("Job %s failed in iteration %d", job_ctx.job_id, index)
                if params.stop_on_failure:
                    return False
                success = False

    return success
