"""Test the working directory used on remote hosts when none is configured."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Self

import pytest

from pyantz.infrastructure.config import InitialConfig, SshConfig
from pyantz.infrastructure.runner._remotes import ssh as ssh_module
from pyantz.infrastructure.runner._remotes._transfers import (
    DEFAULT_CONTAINER_WORKING_DIR,
    get_cmd,
)

if TYPE_CHECKING:
    from pathlib import Path

REMOTE_TMP = "/tmp/tmp.AbC123"  # noqa: S108
NOP = "pyantz.jobs.testing.nop.do_nothing"


class _ExitStatus:
    @staticmethod
    def recv_exit_status() -> int:
        return 0


class _Channel:
    def __init__(self, output: str = "") -> None:
        self._output = output.encode()
        self.channel = _ExitStatus()

    def read(self) -> bytes:
        return self._output


class _FakeSftp:
    def __init__(self, calls: list[tuple[str, str]]) -> None:
        self._calls = calls

    def mkdir(self, path: str) -> None:
        self._calls.append(("mkdir", path))

    def put(self, _local: str, remote: str) -> None:
        self._calls.append(("put", remote))

    def close(self) -> None:
        return None


class _FakeSshClient:
    """Stand-in for ``paramiko.SSHClient`` recording what it was asked to do."""

    calls: list[tuple[str, str]]

    def __init__(self) -> None:
        type(self).calls = []

    def load_system_host_keys(self) -> None:
        return None

    def set_missing_host_key_policy(self, _policy: object) -> None:
        return None

    def close(self) -> None:
        return None

    def connect(self, **_kwargs: Any) -> None:  # noqa: ANN401
        return None

    def open_sftp(self) -> _FakeSftp:
        return _FakeSftp(type(self).calls)

    def exec_command(self, cmd: str) -> tuple[io.BytesIO, _Channel, _Channel]:
        type(self).calls.append(("exec", cmd))
        output = REMOTE_TMP + "\n" if cmd == "mktemp -d" else ""
        return io.BytesIO(), _Channel(output), _Channel()

    def __enter__(self) -> Self:
        return self


@pytest.fixture
def fake_ssh(monkeypatch: pytest.MonkeyPatch) -> type[_FakeSshClient]:
    """Replace paramiko's client in the ssh runner."""
    monkeypatch.setattr(ssh_module.paramiko, "SSHClient", _FakeSshClient)
    return _FakeSshClient


def _config(tmp_path: Path, **host: Any) -> InitialConfig:  # noqa: ANN401
    return InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {
                "type_": "local_proc",
                "working_directory": str(tmp_path),
            },
            "host": {"type_": "ssh", "remote_host": "h", "run_async": False, **host},
        },
    )


def test_ssh_without_working_dir_uses_remote_temp_dir(
    tmp_path: Path,
    fake_ssh: type[_FakeSshClient],
) -> None:
    """With no working_dir, a directory is made by mktemp on the remote."""
    ssh_module.run_ssh(_config(tmp_path))

    calls = fake_ssh.calls
    assert ("exec", "mktemp -d") in calls
    assert ("put", f"{REMOTE_TMP}/setup.tar.gz") in calls
    assert not [call for call in calls if call[0] == "mkdir"]
    run_cmd = next(arg for kind, arg in calls if kind == "exec" and "pyantz" in arg)
    assert run_cmd.startswith(f"cd {REMOTE_TMP} &&")
    assert f"{REMOTE_TMP}/config.json" in run_cmd


def test_ssh_with_working_dir_is_used_as_given(
    tmp_path: Path,
    fake_ssh: type[_FakeSshClient],
) -> None:
    """An explicit working_dir is created and used, with no mktemp."""
    ssh_module.run_ssh(_config(tmp_path, working_dir="/srv/mine"))

    calls = fake_ssh.calls
    assert ("exec", "mkdir -p /srv/mine") in calls
    assert ("exec", "mktemp -d") not in calls
    assert ("put", "/srv/mine/setup.tar.gz") in calls


def test_container_default_is_workspace() -> None:
    """Containers still default to /workspace."""
    host = SshConfig(remote_host="h")
    assert host.working_dir is None
    cmd = get_cmd(host, DEFAULT_CONTAINER_WORKING_DIR)
    assert cmd[-1] == "/workspace/config.json"
