"""Continuously run code until some condition is true."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import (
    JobConfig,
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

    jobs: list[JobConfig]


@add_parameters(LocalForLoopParams)
def local_for_loop(params: LocalForLoopParams, submit_fn: SubmissionFnType) -> bool:
    """Run a series of jobs locally for a set of iterations."""
    success = True
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    for _iter in range(params.num_iterations):
        for job in params.jobs:
            job_ctx = JobWithContext.from_config(job).inherit_context(curr_variables)
            success &= run_job_no_parent_wrapper(job_ctx, submit_fn)
            if not success:
                break

    return success
