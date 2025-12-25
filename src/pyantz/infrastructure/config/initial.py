"""Configuration of the analysis overall."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from .job import JobConfig
from .runners import LocalRunnerConfig

type AnyRunner = LocalRunnerConfig


class InitialConfig[S: (LocalRunnerConfig)](BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    jobs: tuple[JobConfig, ...]

    submitter: S = Field(discriminator="type_")

    variables: Mapping[str, Any] = Field(default_factory=dict)
