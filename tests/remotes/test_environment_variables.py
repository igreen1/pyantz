"""Test environment variables from the host config reach the remote command."""

import shlex
from typing import TYPE_CHECKING, Any

import docker
import pytest

from pyantz.infrastructure.config import ContainerConfig, InitialConfig, SshConfig
from pyantz.infrastructure.runner._remotes import container as container_module
from pyantz.infrastructure.runner._remotes import ssh as ssh_module
from pyantz.infrastructure.runner._remotes._transfers import get_environment

from .fake_ssh import commands, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


class _FakeContainer:
    def put_archive(self, *_args: object) -> bool:
        return True

    def start(self) -> None:
        return None

    def wait(self) -> dict[str, int]:
        return {"StatusCode": 0}

    def logs(self) -> bytes:
        return b""

    def remove(self) -> None:
        return None


class _FakeDocker:
    """Records the settings given when creating a container."""

    def __init__(self) -> None:
        self.create_kwargs: dict[str, Any] = {}
        self.containers = self
        self.images = self

    def get(self, _image: str) -> object:
        return object()

    def create(self, **kwargs: Any) -> _FakeContainer:  # noqa: ANN401
        self.create_kwargs = kwargs
        return _FakeContainer()


def test_environment_file_and_mapping_are_merged(tmp_path: Path) -> None:
    """Variables in the config override those from the file."""
    env_file = tmp_path / "env"
    env_file.write_text(
        "# a comment\n\nA=from_file\nexport B='quoted value'\nC=\"x=y\"\n",
    )
    host = SshConfig(
        remote_host="h",
        environment_variables_file=str(env_file),
        environment_variables={"A": "from_config", "D": "4"},
    )

    assert get_environment(host) == {
        "A": "from_config",
        "B": "quoted value",
        "C": "x=y",
        "D": "4",
    }


def test_invalid_environment_file_line_is_reported(tmp_path: Path) -> None:
    """A line which isn't KEY=VALUE names itself in the error."""
    env_file = tmp_path / "env"
    env_file.write_text("FINE=1\nnot a variable\n")
    host = ContainerConfig(environment_variables_file=str(env_file))

    with pytest.raises(ValueError, match="not a variable"):
        get_environment(host)


def test_no_environment_by_default() -> None:
    """Without configuration there is nothing to set."""
    assert get_environment(SshConfig(remote_host="h")) == {}


def test_container_receives_the_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`containers.create` is given the merged environment."""
    env_file = tmp_path / "env"
    env_file.write_text("FROM_FILE=1\nSHARED=file\n")
    fake = _FakeDocker()
    monkeypatch.setattr(docker, "from_env", lambda: fake)
    config = InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {"type_": "local_proc", "working_directory": "/workspace"},
            "host": {
                "type_": "container",
                "environment_variables_file": str(env_file),
                "environment_variables": {"SHARED": "config", "OTHER": "2"},
            },
        },
    )

    container_module.run_container(config)

    assert fake.create_kwargs["environment"] == {
        "FROM_FILE": "1",
        "SHARED": "config",
        "OTHER": "2",
    }


def test_ssh_command_has_quoted_assignments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The remote command is run through `env` with each assignment quoted."""
    fake = install(monkeypatch)
    config = ssh_config(
        tmp_path,
        working_dir="/srv/work",
        environment_variables={"GREETING": "hello world; rm -rf ~", "N": "1"},
    )

    ssh_module.run_ssh(config)

    run_cmd = commands(fake)[-1]
    assert " env 'GREETING=hello world; rm -rf ~' N=1 uvx " in run_cmd
    assert "GREETING=hello world; rm -rf ~" in shlex.split(run_cmd)


def test_ssh_command_without_environment_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No variables, no `env` prefix."""
    fake = install(monkeypatch)

    ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    assert " env " not in commands(fake)[-1]
