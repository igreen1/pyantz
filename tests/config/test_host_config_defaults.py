"""Test the defaults of the host configs."""

import getpass
import subprocess
import sys
from typing import TYPE_CHECKING

from pyantz.infrastructure.config import host_config

if TYPE_CHECKING:
    import pytest

IMPORT_WITHOUT_USER = """
import getpass

def _raise():
    raise OSError("no user")

getpass.getuser = _raise
import pyantz.infrastructure.config.host_config
"""


def test_import_does_not_look_up_user() -> None:
    """Importing the module must work where there is no user name."""
    result = subprocess.run(
        [sys.executable, "-c", IMPORT_WITHOUT_USER],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_default_user_is_looked_up_per_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default is evaluated when the config is created, not at import."""
    monkeypatch.setattr(getpass, "getuser", lambda: "first")
    first = host_config.SshConfig(remote_host="h")
    monkeypatch.setattr(getpass, "getuser", lambda: "second")
    second = host_config.SshConfig(remote_host="h")

    assert first.remote_user == "first"
    assert second.remote_user == "second"


def test_explicit_user_wins() -> None:
    """A user given in the config is used as is."""
    assert host_config.SshConfig(remote_host="h", remote_user="me").remote_user == "me"
