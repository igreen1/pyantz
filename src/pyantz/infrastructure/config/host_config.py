"""Configuration for *where* the pipeline controller runs.

The host config controls where pyantz starts its submitter process, which
is distinct from *how* individual jobs are submitted (the runner config).

* :class:`LocalConfig` — run the controller on this machine (default).
* :class:`SshConfig` — SSH into a remote host, copy the config, and run
  pyantz there.
* :class:`ContainerConfig` — exec into a running Docker/Podman container.

After reaching the remote host, the ``subsequent_host`` field lets you
chain hops (e.g. SSH into a bastion, then exec into a container).
"""

from __future__ import annotations

import getpass
from collections.abc import Mapping
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _current_user() -> str:
    """Get the name of the user running pyantz."""
    return getpass.getuser()


class LocalConfig(BaseModel):
    """Execute the submitter locally."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["local"] = "local"


class RemoteConfig(BaseModel):
    """Execute on a remote machine.

    Just a base class for other configurations.
    """

    model_config = ConfigDict(frozen=True)

    # if set, a file on *this* machine with `KEY=VALUE` lines (blank lines and
    # `#` comments are ignored) which is read and sent as environment variables
    # of the remote command. Variables in `environment_variables` take precedence
    environment_variables_file: str | None = None

    # if set, the working directory from the remote
    # will be copied to this directory
    output_dir: str | None = None

    # if set, will use this as the directory to run as cwd
    # if not set, ssh hosts use a new temporary directory created on the remote
    # and containers use /workspace
    working_dir: str | None = None

    # files to add as python requirements
    requirements: list[str] | None = None

    # if true, copy this project directory
    # primarily useful for testing
    copy_project_dir: bool = False

    # after connecting to the remote, what host to use there
    subsequent_host: HostConfig = LocalConfig()

    # environment variables to set for the command run on the remote host
    # (for containers, in the container)
    environment_variables: Mapping[str, str] = Field(default_factory=dict)


class SshConfig(RemoteConfig):
    """Execute using ssh to access a remote machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["ssh"] = "ssh"

    # host to ssh
    remote_host: str

    # port to use for ssh (default is 22)
    remote_port: int = 22

    # defaults to the current user, looked up when the config is created
    remote_user: str = Field(default_factory=_current_user)

    # seconds to wait when connecting before giving up
    connect_timeout: float = 30

    # private key file to authenticate with; if not set, paramiko tries the
    # ssh agent and the usual keys in ~/.ssh
    key_filename: str | None = None

    # what to do with a host that is not in the known hosts:
    # "reject" refuses to connect, "warn" connects and logs a warning,
    # "auto_add" trusts and remembers it (unsafe on untrusted networks)
    known_hosts_policy: Literal["reject", "warn", "auto_add"] = "reject"

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


# HostConfig is defined after the classes that refer to it
RemoteConfig.model_rebuild()
SshConfig.model_rebuild()
ContainerConfig.model_rebuild()
