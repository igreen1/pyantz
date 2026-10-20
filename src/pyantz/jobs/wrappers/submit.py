"""Jobs that wrap a sub-pipeline in a different submitter or host.

:func:`submit` re-wraps a list of jobs under a new
:class:`~pyantz.infrastructure.config.runners.LocalRunnerConfig` or
:class:`~pyantz.infrastructure.config.runners.slurm_runner.SlurmRunnerConfig`,
letting users switch execution backends mid-pipeline.

:func:`new_host` additionally moves execution to a different host (SSH or
container) before using the new submitter.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyantz import start
from pyantz.infrastructure.config import (
    AnyRunner,
    InitialConfig,
    JobConfig,
    add_parameters,
    no_submit_fn,
)
from pyantz.infrastructure.config.host_config import HostConfig
from pyantz.infrastructure.runner.job_manager import (
    JobVariables,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Final


class SubmitParams(BaseModel):
    """Parameters to submit a job through a new submitter."""

    model_config = ConfigDict(frozen=True)

    # the wrapped configuration to submit
    runner_config: AnyRunner

    jobs: tuple[JobConfig, ...]


@add_parameters(SubmitParams)
@no_submit_fn  # we're making our own!
def submit(params: SubmitParams) -> bool:
    """Wrap a set of jobs in a new submitter.

    This allows a user to switch submitters in their pipeline, which may
    prove useful in some cases.

    For example, the user may want to submit a set of jobs to slurm
    but then have the jobs run serially locally in a simple multiprocess
    to reduce the impact to their "priority" level from the slurm scheduler.
    """
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )
    new_initial_config = InitialConfig(
        jobs=params.jobs, submitter=params.runner_config, variables=curr_variables
    )

    report = start(new_initial_config)

    return report is None or report.all_succeeded


class HostParams(BaseModel):
    """Parameters to submit a job through a new submitter."""

    model_config = ConfigDict(frozen=True)

    # configuration of the host to run on
    host_config: HostConfig

    # configuration of the submitter to use on the new host
    submit_config: AnyRunner

    jobs: tuple[JobConfig, ...]


@add_parameters(HostParams)
@no_submit_fn  # we're making our own!
def new_host(params: HostParams) -> bool:
    """Run a set of jobs on a new host."""
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )
    new_initial_config = InitialConfig(
        jobs=params.jobs,
        variables=curr_variables,
        submitter=params.submit_config,
        host=params.host_config,
    )

    report = start(new_initial_config)

    return report is None or report.all_succeeded
