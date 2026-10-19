"""Test failures of remote commands are reported rather than ignored."""

import io
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import commands, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path


def test_failed_untar_raises_with_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tar failure stops the run and shows the remote's error text."""
    fake = install(monkeypatch)
    fake.responses["tar -xvzf"] = (2, "", "tar: setup.tar.gz: Cannot open")
    config = ssh_config(tmp_path, working_dir="/srv/work")

    with pytest.raises(RuntimeError, match="Cannot open") as exc_info:
        ssh_module.run_ssh(config)

    assert "Extracting the setup files" in str(exc_info.value)
    assert "exit code 2" in str(exc_info.value)
    # nothing was run after the failure
    assert not [cmd for cmd in commands(fake) if "uvx" in cmd]


def test_failed_project_untar_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The second extraction (project files) is checked too."""
    fake = install(monkeypatch)
    monkeypatch.setattr(ssh_module, "get_project_dir", lambda: io.BytesIO(b"tar"))
    fake.responses["tar -xzvf"] = (1, "", "gzip: stdin: not in gzip format")
    config = ssh_config(tmp_path, working_dir="/srv/work", copy_project_dir=True)

    with pytest.raises(RuntimeError, match="not in gzip format"):
        ssh_module.run_ssh(config)


def test_failed_pyantz_command_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing uvx (or a failing pipeline) is a failure, not a silent success."""
    fake = install(monkeypatch)
    fake.responses["uvx"] = (127, "", "bash: uvx: command not found")
    config = ssh_config(tmp_path, working_dir="/srv/work")

    with pytest.raises(RuntimeError, match="uvx: command not found"):
        ssh_module.run_ssh(config)


def test_successful_run_does_not_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero exit codes everywhere run all of the commands."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/work")

    ssh_module.run_ssh(config)

    assert len(commands(fake)) == 2  # noqa: PLR2004
