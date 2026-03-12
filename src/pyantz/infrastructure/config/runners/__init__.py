"""Configurations for the various runners to be used by pyantz."""

from pydantic import BaseModel, Field

from .local_runner import LocalRunnerConfig
from .slurm_runner import SlurmRunnerConfig


class RunnerConfig(BaseModel):
    """Wrapper for the configurations."""

    config: LocalRunnerConfig | SlurmRunnerConfig = Field(discriminator="type_")


__all__ = [
    "LocalRunnerConfig",
    "RunnerConfig",
]
