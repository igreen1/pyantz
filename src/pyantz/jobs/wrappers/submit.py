"""Jobs that wrap a sub-pipeline in a different submitter or host.

:func:`submit` re-wraps a list of jobs under a new
:class:`~pyantz.infrastructure.config.runners.LocalRunnerConfig` or
:class:`~pyantz.infrastructure.config.runners.slurm_runner.SlurmRunnerConfig`,
letting users switch execution backends mid-pipeline.

:func:`new_host` additionally moves execution to a different host (SSH or
container) before using the new submitter.
"""

from __future__ import annotations

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

    runner_config: AnyRunner
    """The submitter to run the jobs with."""

    jobs: tuple[JobConfig, ...]
    """The jobs to run."""


@add_parameters(SubmitParams)
@no_submit_fn  # we're making our own!
def submit(params: SubmitParams) -> bool:
    """Wrap a set of jobs in a new submitter.

    This allows a user to switch submitters in their pipeline, which may
    prove useful in some cases.

    For example, the user may want to submit a set of jobs to slurm
    but then have the jobs run serially locally in a simple multiprocess
    to reduce the impact to their "priority" level from the slurm scheduler.

    The jobs inherit the variables of this job. This job waits for them when the
    submitter reports back (the local runner does); otherwise it succeeds once
    they are submitted.

    Args:
        params: the job's parameters, validated as :class:`SubmitParams`.

    Parameters:
        runner_config (AnyRunner): the submitter to run the jobs with, such as a
            :class:`~pyantz.infrastructure.config.runners.LocalRunnerConfig`.
        jobs (tuple[JobConfig, ...]): the jobs to run.

    Returns:
        bool: True if every job succeeded (or the submitter doesn't report on
        them), otherwise False.

    Raises:
        pydantic.ValidationError: if the jobs don't form a valid configuration
            (e.g., they depend on unknown jobs).

    Example:
        .. testsetup:: wrappers-submit

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: wrappers-submit

            import os

            from pyantz.jobs.wrappers.submit import submit

            success = submit(
                {
                    "runner_config": {
                        "type_": "local_proc",
                        "working_directory": ".",
                        "use_same_proc": True,
                    },
                    "jobs": [
                        {
                            "function": "pyantz.jobs.testing.touch_file.touch_file",
                            "parameters": {"path": "submitted.txt"},
                        },
                    ],
                },
                lambda job: None,
            )
            print(success, os.path.exists("submitted.txt"))

        .. testoutput:: wrappers-submit

            True True

        .. testcleanup:: wrappers-submit

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

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
    """Parameters to run jobs through a new submitter on another host."""

    model_config = ConfigDict(frozen=True)

    host_config: HostConfig
    """Configuration of the host to run on."""

    submit_config: AnyRunner
    """Configuration of the submitter to use on the new host."""

    jobs: tuple[JobConfig, ...]
    """The jobs to run."""


@add_parameters(HostParams)
@no_submit_fn  # we're making our own!
def new_host(params: HostParams) -> bool:
    """Run a set of jobs on a new host.

    Like :func:`submit`, but the submitter first moves to another host, such as
    a machine reached over ssh or a container.

    Args:
        params: the job's parameters, validated as :class:`HostParams`.

    Parameters:
        host_config (HostConfig): the host to run on (``local``, ``ssh`` or
            ``container``).
        submit_config (AnyRunner): the submitter to use on the new host.
        jobs (tuple[JobConfig, ...]): the jobs to run.

    Returns:
        bool: True if every job succeeded (or the host or submitter doesn't
        report on them), otherwise False.

    Raises:
        pydantic.ValidationError: if the jobs don't form a valid configuration.
        Exception: errors reaching the host, e.g., an ssh connection failure, are
            raised by the host's runner.

    Example:
        .. testsetup:: wrappers-new-host

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: wrappers-new-host

            import os

            from pyantz.jobs.wrappers.submit import new_host

            success = new_host(
                {
                    "host_config": {"type_": "local"},
                    "submit_config": {
                        "type_": "local_proc",
                        "working_directory": ".",
                        "use_same_proc": True,
                    },
                    "jobs": [
                        {
                            "function": "pyantz.jobs.testing.touch_file.touch_file",
                            "parameters": {"path": "on_new_host.txt"},
                        },
                    ],
                },
                lambda job: None,
            )
            print(success, os.path.exists("on_new_host.txt"))

        .. testoutput:: wrappers-new-host

            True True

        .. testcleanup:: wrappers-new-host

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
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
