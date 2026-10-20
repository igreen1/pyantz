"""Test the password fallback only prompts when a person can answer."""

import getpass
import io
from typing import TYPE_CHECKING, Any

import paramiko
import pytest

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import FakeSshClient, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path


class _Stdin(io.StringIO):
    def __init__(self, *, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture
def keys_rejected(monkeypatch: pytest.MonkeyPatch) -> type[FakeSshClient]:
    """Make the remote refuse key authentication but accept a password."""
    fake = install(monkeypatch)

    def _connect(self: FakeSshClient, **kwargs: Any) -> None:  # noqa: ANN401
        type(self).calls.append(("connect", kwargs))
        if "password" not in kwargs:
            msg = "Authentication failed."
            raise paramiko.AuthenticationException(msg)

    monkeypatch.setattr(fake, "connect", _connect)
    return fake


def test_without_a_terminal_it_fails_clearly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keys_rejected: type[FakeSshClient],
) -> None:
    """No terminal: no prompt, and an error which says what to do."""
    monkeypatch.setattr("sys.stdin", _Stdin(tty=False))

    def _no_prompt(*_args: object) -> str:
        pytest.fail("getpass must not be called without a terminal")

    monkeypatch.setattr(getpass, "getpass", _no_prompt)

    with pytest.raises(RuntimeError, match=r"no terminal.*key based login") as info:
        ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    assert "remote.example" in str(info.value)
    assert isinstance(info.value.__cause__, paramiko.AuthenticationException)
    assert [kind for kind, _ in keys_rejected.calls].count("connect") == 1


def test_with_a_terminal_the_password_is_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keys_rejected: type[FakeSshClient],
) -> None:
    """With a terminal, the user is asked and the password is used to connect."""
    monkeypatch.setattr("sys.stdin", _Stdin(tty=True))
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: "secret")

    ssh_module.run_ssh(ssh_config(tmp_path, working_dir="/srv/work"))

    connects = [arg for kind, arg in keys_rejected.calls if kind == "connect"]
    assert len(connects) == 2  # noqa: PLR2004
    assert "password" not in connects[0]
    assert connects[1]["password"] == "secret"  # noqa: S105
