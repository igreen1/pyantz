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
    """Get the name of the user running pyantz.

    Used as the default of :attr:`SshConfig.remote_user`.

    Args:
        None.

    Returns:
        str: the login name of the current user.

    Raises:
        OSError: if the user's name can't be found (see :func:`getpass.getuser`).

    """
    return getpass.getuser()


class LocalConfig(BaseModel):
    """Execute the submitter locally."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["local"] = "local"
    """Identifies this host configuration."""


class RemoteConfig(BaseModel):
    """Execute on a remote machine.

    Just a base class for other configurations.
    """

    model_config = ConfigDict(frozen=True)

    environment_variables_file: str | None = None
    """If set, a file on *this* machine with ``KEY=VALUE`` lines (blank lines and
    ``#`` comments are ignored) which is read and sent as environment variables
    of the remote command. Variables in ``environment_variables`` take
    precedence."""

    output_dir: str | None = None
    """If set, the working directory from the remote will be copied to this
    directory."""

    working_dir: str | None = None
    """If set, the directory to run in on the remote; if not set, ssh hosts use a
    new temporary directory created on the remote and containers use
    ``/workspace``."""

    requirements: list[str] | None = None
    """Python requirements to install on the remote (as given to ``pip
    install``)."""

    copy_project_dir: bool = False
    """If true, copy this project directory to the remote; primarily useful for
    testing."""

    subsequent_host: HostConfig = LocalConfig()
    """After connecting to the remote, what host to use there."""

    environment_variables: Mapping[str, str] = Field(default_factory=dict)
    """Environment variables to set for the command run on the remote host (for
    containers, in the container)."""


class SshConfig(RemoteConfig):
    """Execute using ssh to access a remote machine."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["ssh"] = "ssh"
    """Identifies this host configuration."""

    remote_host: str
    """Host to ssh into."""

    remote_port: int = 22
    """Port to use for ssh."""

    remote_user: str = Field(default_factory=_current_user)
    """User to log in as; defaults to the current user, looked up when the config
    is created."""

    connect_timeout: float = 30
    """Seconds to wait when connecting before giving up."""

    key_filename: str | None = None
    """Private key file to authenticate with; if not set, paramiko tries the ssh
    agent and the usual keys in ``~/.ssh``."""

    known_hosts_policy: Literal["reject", "warn", "auto_add"] = "reject"
    """What to do with a host that is not in the known hosts: ``reject`` refuses
    to connect, ``warn`` connects and logs a warning, ``auto_add`` trusts and
    remembers it (unsafe on untrusted networks)."""

    run_async: bool = True
    """If true, don't wait for the command to finish before closing the ssh
    connection."""

    sync_data_at_end: bool = False
    """If true, copy the remote working directory back to ``output_dir`` once
    the command finishes; needs ``run_async`` to be false."""

    @model_validator(mode="after")
    def check_syncs(self) -> Self:
        """Check that sync settings make sense.

        Args:
            None.

        Returns:
            Self: the validated configuration.

        Raises:
            ValueError: if ``sync_data_at_end`` is set with ``run_async`` or
                without ``output_dir``.

        Example:
            .. testcode::

                from pydantic import ValidationError

                from pyantz.infrastructure.config import SshConfig

                try:
                    SshConfig(remote_host="hpc", sync_data_at_end=True)
                except ValidationError:
                    print("can't sync data at the end of an async run")

            .. testoutput::

                can't sync data at the end of an async run

        """
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
    """Identifies this host configuration."""

    container_service: Literal["podman", "docker"] = "docker"
    """Which container software to use."""

    image: str = "ghcr.io/astral-sh/uv:alpine"
    """Image to run if no container is named; it must provide ``uv``."""

    name: str | None = None
    """Name of the running container to exec into; if not set, a new container
    is started from ``image``."""


type HostConfig = Annotated[
    SshConfig | ContainerConfig | LocalConfig,
    Field(discriminator="type_"),
]
"""Any host configuration, told apart by its ``type_``."""


# HostConfig is defined after the classes that refer to it
RemoteConfig.model_rebuild()
SshConfig.model_rebuild()
ContainerConfig.model_rebuild()
