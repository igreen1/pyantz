"""Configuration for the remote execution."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RemoteExecutionConfig(BaseModel):
    """Configuration for executing remotely."""

    model_config = ConfigDict(frozen=True)


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

    # name of the container to exec into
    container_name: str
