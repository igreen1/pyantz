"""Test running in the background on a remote host returns without waiting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import commands, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_async_run_detaches_and_redirects_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The background command redirects everything, so the channel can close."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/work", run_async=True)

    ssh_module.run_ssh(config)

    run_cmd = commands(fake)[-1]
    assert run_cmd.startswith("cd /srv/work && nohup uvx ")
    assert run_cmd.endswith(" > pyantz.log 2>&1 < /dev/null &")


def test_async_run_logs_where_the_output_goes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The user is told which remote file to look at."""
    install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/work", run_async=True)

    with caplog.at_level("INFO"):
        ssh_module.run_ssh(config)

    assert "/srv/work/pyantz.log" in caplog.text
    assert "remote.example" in caplog.text


def test_blocking_run_is_not_redirected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A synchronous run keeps its output so it can be logged."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/work", run_async=False)

    ssh_module.run_ssh(config)

    run_cmd = commands(fake)[-1]
    assert "nohup" not in run_cmd
    assert "pyantz.log" not in run_cmd
    assert not run_cmd.endswith("&")
