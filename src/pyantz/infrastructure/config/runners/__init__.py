"""Configurations for the various runners to be used by pyantz."""

from .local_runner import LocalRunnerConfig
from .slurm_runner import SlurmRunnerConfig


__all__ = [
    "LocalRunnerConfig",
    "SlurmRunnerConfig",
]
