"""Configuration of the analysis overall."""

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from pyantz.infrastructure.virtual import compile_virtual

from .host_config import HostConfig, LocalConfig
from .job import JobConfig, make_job
from .runners import LocalRunnerConfig, SlurmRunnerConfig

type AnyRunner = LocalRunnerConfig | SlurmRunnerConfig


def make_and_compile(jobs: Any) -> list[JobConfig]:  # noqa: ANN401
    """Make jobs and compile them."""
    return compile_virtual(list(map(make_job, jobs)))


class InitialConfig[S: (LocalRunnerConfig, SlurmRunnerConfig)](BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    jobs: Annotated[tuple[JobConfig, ...], BeforeValidator(make_and_compile)]

    submitter: S = Field(discriminator="type_")

    variables: Mapping[str, Any] = Field(default_factory=dict)

    host: HostConfig = LocalConfig()
