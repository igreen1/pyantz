"""Configurations for the various runners to be used by pyantz."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .local_runner import LocalRunnerConfig

if TYPE_CHECKING:
    from .slurm_runner import SlurmRunnerConfig


class RunnerConfig(BaseModel):
    """Wrapper for the configurations."""

    config: LocalRunnerConfig | SlurmRunnerConfig = Field(discriminator="type_")


__all__ = [
    "LocalRunnerConfig",
    "RunnerConfig",
]
