"""Configuration for the host execution location.

Before the first submitter is started, the program will look
to the host configuration to determine where to start the program.
So, while the submitter configuration tells the program how to submit new jobs
the host config tells the program how to start itself.
"""

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class LocalConfig(BaseModel):
    """Execute the submitter locally."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["local"] = "local"


class SshConfig(BaseModel):
    """Execute using ssh to access a remote machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["ssh"] = "ssh"

    # host to ssh
    remote_host: str

    # port to use for ssh (default is 22)
    remote_port: str | int = 22


class ContainerConfig(BaseModel):
    """Execute in a docker container that is running on the machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["container"] = "container"

    # which docker software to use
    container_service: Literal["podman", "docker"] = "docker"

    image: str ="ghcr.io/astral-sh/uv:alpine"

    # name of the container to exec into
    name: str | None = None

    # pass a list of environment variables to be set in the container
    environment_variables: Mapping[str, str] = Field(default_factory=dict)

    # if set, read in a file of environment variables
    environment_variables_file: str | None = None

    # if set, the working directory from the container
    # will be copied to this directory
    output_dir: str | None = None

    # if set, will use this as the directory to run as cwd
    # if not set, will use the tmpfs location
    working_dir: str = "/pyantz"

    # files to add as python requirements
    requirements: list[str] | None = None

type HostConfig = Annotated[
    SshConfig | ContainerConfig | LocalConfig,
    Field(discriminator="type_"),
]
