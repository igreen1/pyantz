"""Wrap the job ina new submission type."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyantz import start
from pyantz.infrastructure.config import (
    ContainerConfig,
    InitialConfig,
    JobConfig,
    LocalConfig,
    SshConfig,
    add_parameters,
    no_submit_fn,
)
from pyantz.infrastructure.config.runners import LocalRunnerConfig, SlurmRunnerConfig
from pyantz.infrastructure.runner.job_manager import (
    JobVariables,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Final


class SubmitParams[S: (LocalRunnerConfig, SlurmRunnerConfig)](BaseModel):
    """Parameters to submit a job through a new submitter."""

    model_config = ConfigDict(frozen=True)

    # the wrapped configuration to submti
    runner_config: S

    jobs: tuple[JobConfig, ...]


@add_parameters(SubmitParams)
@no_submit_fn  # we're making our own!
def submit(params: SubmitParams[Any]) -> bool:
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

    start(new_initial_config)

    return True


class HostParams[
    H: (ContainerConfig, LocalConfig, SshConfig),
    S: (LocalRunnerConfig, SlurmRunnerConfig),
](BaseModel):
    """Parameters to submit a job through a new submitter."""

    model_config = ConfigDict(frozen=True)

    # configuration of the host to run on
    host_config: H

    # configuration of the submitter to use on the new host
    submit_config: S

    jobs: tuple[JobConfig, ...]


@add_parameters(HostParams)
@no_submit_fn  # we're making our own!
def new_host(params: HostParams[Any, Any]) -> bool:
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

    start(new_initial_config)

    return True
