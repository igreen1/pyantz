"""Startup our program.

Check if we're in the right execution environment,
the point to the correct local runner.
"""

from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local

from ._remotes.container import run_container as start_container
from ._remotes.ssh import run_ssh as start_ssh

if TYPE_CHECKING:
    from collections.abc import Mapping


def start(config: _InitialConfig[Any] | Mapping[str, Any]) -> None:
    """Check how to start the program and route to the proper starter."""
    loaded_config: _InitialConfig[Any] = _InitialConfig.model_validate(config)  # pyright: ignore[reportUnknownVariableType]
    if loaded_config.host.type_ == "local":
        return run_local(loaded_config)
    if loaded_config.host.type_ == "container":
        return start_container(loaded_config)
    if loaded_config.host.type_ == "ssh":
        return start_ssh(loaded_config)

    return None


def run_local(config: _InitialConfig[Any]) -> None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    # if not loaded, check it
    if config.submitter.type_ == "local_proc":
        # start local runner
        _start_local(config)
    else:
        raise ValueError
