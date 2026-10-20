"""Test copying the results back from the remote host with rsync."""

import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def rsync_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Fake out the ssh connection and rsync, recording the rsync commands."""
    install(monkeypatch)
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(ssh_module.shutil, "which", lambda _name: "/opt/bin/rsync")
    return calls


def _sync_config(tmp_path: Path, **host: Any) -> Any:  # noqa: ANN401
    return ssh_config(
        tmp_path,
        working_dir="/srv/work",
        run_async=False,
        sync_data_at_end=True,
        output_dir=str(tmp_path / "out"),
        **host,
    )


def test_rsync_uses_the_configured_port(
    tmp_path: Path,
    rsync_calls: list[list[str]],
) -> None:
    """The ssh port from the config is given to rsync's ssh."""
    ssh_module.run_ssh(_sync_config(tmp_path, remote_port=2222))

    (cmd,) = rsync_calls
    assert cmd[cmd.index("-e") + 1] == "ssh -p 2222"
    assert cmd[-2] == "me@remote.example:/srv/work"
    assert cmd[-1] == str(tmp_path / "out")


def test_rsync_is_found_on_the_path(
    tmp_path: Path,
    rsync_calls: list[list[str]],
) -> None:
    """The rsync which is installed is used, not a hard coded location."""
    ssh_module.run_ssh(_sync_config(tmp_path))

    assert rsync_calls[0][0] == "/opt/bin/rsync"
    assert "ssh -p 22" in rsync_calls[0]


def test_missing_rsync_gives_a_clear_error(
    tmp_path: Path,
    rsync_calls: list[list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without rsync installed, the error says what to do."""
    monkeypatch.setattr(ssh_module.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="rsync was not found"):
        ssh_module.run_ssh(_sync_config(tmp_path))

    assert not rsync_calls
