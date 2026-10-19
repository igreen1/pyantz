"""Configuration for the local multiprocessing runner.

:class:`LocalRunnerConfig` describes how many worker processes to spawn, where
to store the SQLite queue, how often to poll for new jobs, and an optional
overall timeout.  It is the default runner for local development and testing.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LocalRunnerConfig(BaseModel):
    """Configuration for the local runner."""

    model_config = ConfigDict(frozen=True)

    # used to find out which config is being used for serialiation
    type_: Literal["local_proc"] = "local_proc"

    # location to save temporary files and the queue
    working_directory: Path

    # how long to wait between each check of the qeue
    # used while actively pending
    poll_timeout: float = 1.0

    # how many processes to start
    number_processes: int = 2

    # if set, will timeout the runner if jobs are
    # not received in a certain time
    timeout: float | None = None

    # if true, use this process rather than a pool
    # (easier debugging and faster for small jobs)
    use_same_proc: bool = False
