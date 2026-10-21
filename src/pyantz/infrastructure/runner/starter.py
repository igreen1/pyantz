"""Startup our program.

Check if we're in the right execution environment,
the point to the correct local runner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local
from pyantz.infrastructure.runner.slurm import start as _start_slurm

from ._remotes.container import run_container as start_container
from ._remotes.ssh import run_ssh as start_ssh

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyantz.infrastructure.distributed_queue.common.return_types import JobsReport


def start(config: _InitialConfig | Mapping[str, Any]) -> JobsReport | None:
    """Check how to start the program and route to the proper starter.

    Returns:
        JobsReport | None: final report of the jobs when the run is local and
            blocking; None if the outcome is not known (e.g. remote hosts).

    """
    loaded_config: _InitialConfig = _InitialConfig.model_validate(config)
    if loaded_config.host.type_ == "local":
        return run_local(loaded_config)
    if loaded_config.host.type_ == "container":
        start_container(loaded_config)
        return None
    if loaded_config.host.type_ == "ssh":
        start_ssh(loaded_config)
        return None

    return None


def run_local(config: _InitialConfig) -> JobsReport | None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    # if not loaded, check it
    if config.submitter.type_ == "local_proc":
        # start local runner
        return _start_local(config)
    if config.submitter.type_ == "slurm_sbatch":
        _start_slurm(config)
        return None
    msg = f"Unknown submitter type: {config.submitter.type_!r}"
    raise ValueError(msg)
