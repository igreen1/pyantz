"""Configuration for the host execution location.

Before the first submitter is started, the program will look
to the host configuration to determine where to start the program.
So, while the submitter configuration tells the program how to submit new jobs
the host config tells the program how to start itself.
"""

import getpass
from collections.abc import Mapping
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocalConfig(BaseModel):
    """Execute the submitter locally."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["local"] = "local"


class RemoteConfig(BaseModel):
    """Execute on a remote machine.

    Just a base class for other configurations.
    """

    model_config = ConfigDict(frozen=True)

    # if set, read in a file of environment variables
    environment_variables_file: str | None = None

    # if set, the working directory from the remote
    # will be copied to this directory
    output_dir: str | None = None

    # if set, will use this as the directory to run as cwd
    # if not set, will use the tmpfs location
    working_dir: str = "/workspace"

    # files to add as python requirements
    requirements: list[str] | None = None

    # if true, copy this project directory
    # primarily useful for testing
    copy_project_dir: bool = False

    # after connecting to the remote, what host to use there
    subsequent_host: ContainerConfig | HostConfig | LocalConfig = LocalConfig()

    # pass a list of environment variables to be set in the container
    environment_variables: Mapping[str, str] = Field(default_factory=dict)


class SshConfig(RemoteConfig):
    """Execute using ssh to access a remote machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["ssh"] = "ssh"

    # host to ssh
    remote_host: str

    # port to use for ssh (default is 22)
    remote_port: int = 22

    remote_user: str = getpass.getuser()

    # if set to true, will not wait for the command to finish to terminate
    # the ssh terminal
    run_async: bool = True

    # sync data back after running?
    # if set to a truthy value, will rsync data from remote working dir to this location
    sync_data_at_end: bool = False

    @model_validator(mode="after")
    def check_syncs(self) -> Self:
        """Check that sync settings make sense."""
        if self.sync_data_at_end and self.run_async:
            msg = "Cannot run async and sync data at the end of ssh runs."
            raise ValueError(msg)
        if self.sync_data_at_end and not self.output_dir:
            msg = "Must set output dir if syncing data at the end."
            raise ValueError(msg)
        return self


class ContainerConfig(RemoteConfig):
    """Execute in a docker container that is running on the machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["container"] = "container"

    # which docker software to use
    container_service: Literal["podman", "docker"] = "docker"

    image: str = "ghcr.io/astral-sh/uv:alpine"

    # name of the container to exec into
    name: str | None = None


type HostConfig = Annotated[
    SshConfig | ContainerConfig | LocalConfig,
    Field(discriminator="type_"),
]
