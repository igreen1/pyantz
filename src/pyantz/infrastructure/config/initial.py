"""Configuration of the analysis overall."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .runners import LocalRunnerConfig, SlurmRunnerConfig

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .job import JobConfig

type AnyRunner = LocalRunnerConfig


class InitialConfig[S: (LocalRunnerConfig, SlurmRunnerConfig)](BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    jobs: tuple[JobConfig, ...]

    submitter: S = Field(discriminator="type_")

    variables: Mapping[str, Any] = Field(default_factory=dict)
