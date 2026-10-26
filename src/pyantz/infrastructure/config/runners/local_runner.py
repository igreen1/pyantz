"""Configuration for the local multiprocessing runner.

:class:`LocalRunnerConfig` describes how many worker processes to spawn, where
to store the SQLite queue, how often to poll for new jobs, and an optional
overall timeout.  It is the default runner for local development and testing.

Example of :class:`LocalRunnerConfig`:

    .. testcode::

        from pyantz.infrastructure.config import LocalRunnerConfig

        config = LocalRunnerConfig(working_directory=".", number_processes=4)
        print(config.type_, config.number_processes, config.use_same_proc)

    .. testoutput::

        local_proc 4 False
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LocalRunnerConfig(BaseModel):
    """Configuration for the local runner."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["local_proc"] = "local_proc"
    """Identifies this submitter configuration."""

    working_directory: Path
    """Location to save temporary files and the queue (``queue.db``)."""

    poll_timeout: float = 1.0
    """Seconds to wait between each check of the queue while waiting for jobs."""

    number_processes: int = 2
    """How many worker processes to start."""

    timeout: float | None = None
    """If set, the runner stops when it hasn't received a job for this many
    seconds."""

    progress_interval: float | None = 30.0
    """With several worker processes, log a progress report this often (in
    seconds); None turns the reports off."""

    use_same_proc: bool = False
    """If true, run the jobs in this process rather than a pool (easier
    debugging and faster for small jobs)."""
