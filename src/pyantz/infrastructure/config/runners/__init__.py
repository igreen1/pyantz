"""Configurations for the various runners to be used by pyantz."""

from pydantic import BaseModel, Field

from .local_runner import LocalRunnerConfig


class RunnerConfig(BaseModel):
    """Wrapper for the configurations."""

    config: LocalRunnerConfig = Field(discriminator="type_")


__all__ = [
    "LocalRunnerConfig",
    "RunnerConfig",
]
