"""Configurations for the various runners to be used by pyantz."""

from __future__ import annotations

from .local_runner import LocalRunnerConfig
from .slurm_runner import SlurmRunnerConfig

__all__ = [
    "LocalRunnerConfig",
    "SlurmRunnerConfig",
]
