"""Test how the ssh runner opens and closes its connection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import paramiko
import pytest

from pyantz.infrastructure.config import SshConfig
from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import FakeSshClient, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path


def _connect_kwargs(fake: type[FakeSshClient]) -> dict[str, Any]:
    (kwargs,) = [arg for kind, arg in fake.calls if kind == "connect"]
    return kwargs


def test_connection_is_closed_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ssh and sftp connections are closed at the end of a run."""
    fake = install(monkeypatch)

    ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    assert ("close", "") in fake.calls
    assert ("sftp_close", "") in fake.calls


def test_connection_is_closed_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If something fails midway, the connections are still closed."""
    fake = install(monkeypatch)

    def _boom(*_args: object) -> None:
        raise OSError

    monkeypatch.setattr(ssh_module, "get_setup_tar", _boom)

    with pytest.raises(OSError):  # noqa: PT011
        ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    assert ("close", "") in fake.calls
    assert ("sftp_close", "") in fake.calls


def test_connection_closed_if_connecting_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure to connect (e.g. a timeout) still closes the client."""
    fake = install(monkeypatch)

    def _timeout(_self: FakeSshClient, **_kwargs: object) -> None:
        raise TimeoutError

    monkeypatch.setattr(fake, "connect", _timeout)

    with pytest.raises(TimeoutError):
        ssh_module.run_ssh(ssh_config(tmp_path))

    assert ("close", "") in fake.calls


def test_timeout_and_key_file_are_passed_to_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The configured timeout and private key reach paramiko."""
    fake = install(monkeypatch)
    config = ssh_config(
        tmp_path,
        working_dir="/srv/work",
        connect_timeout=5,
        key_filename="/home/me/.ssh/special",
    )

    ssh_module.run_ssh(config)

    kwargs = _connect_kwargs(fake)
    assert kwargs["timeout"] == 5  # noqa: PLR2004
    assert kwargs["key_filename"] == "/home/me/.ssh/special"
    assert kwargs["hostname"] == "remote.example"
    assert kwargs["username"] == "me"


def test_defaults_have_a_timeout_and_no_key_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without configuration, connecting still can't hang forever."""
    fake = install(monkeypatch)

    ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    kwargs = _connect_kwargs(fake)
    assert kwargs["timeout"] == 30  # noqa: PLR2004
    assert kwargs["key_filename"] is None


@pytest.mark.parametrize(
    ("name", "policy"),
    [
        ("reject", paramiko.RejectPolicy),
        ("warn", paramiko.WarningPolicy),
        ("auto_add", paramiko.AutoAddPolicy),
    ],
)
def test_known_hosts_policy_is_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    policy: type[paramiko.MissingHostKeyPolicy],
) -> None:
    """The configured policy for unknown hosts is the one set on the client."""
    fake = install(monkeypatch)
    applied: list[object] = []
    monkeypatch.setattr(
        fake,
        "set_missing_host_key_policy",
        lambda _self, chosen: applied.append(chosen),
    )

    ssh_module.run_ssh(
        ssh_config(tmp_path, working_dir="/srv/work", known_hosts_policy=name),
    )

    (chosen,) = applied
    assert isinstance(chosen, policy)


def test_default_policy_rejects_unknown_hosts() -> None:
    """The safe policy is the default."""
    assert SshConfig(remote_host="h").known_hosts_policy == "reject"
