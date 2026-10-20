"""Test values are quoted when building the shell commands for the remote."""

import io
import shlex
from typing import TYPE_CHECKING

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import commands, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NASTY_DIR = "/srv/a b; echo pwned"


def test_working_dir_is_one_quoted_token_in_every_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A working_dir with spaces and shell syntax stays a single argument."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir=NASTY_DIR)

    ssh_module.run_ssh(config)

    cmds = commands(fake)
    assert cmds
    for cmd in cmds:
        tokens = shlex.split(cmd)
        # the injected text never ends up as a separate word of its own
        assert all(token.startswith(NASTY_DIR) for token in tokens if "pwned" in token)
        assert "echo" not in tokens
        # the value shows up quoted, never raw
        assert shlex.quote(NASTY_DIR) in cmd
        assert f" {NASTY_DIR} " not in cmd


def test_project_dir_extraction_is_quoted_too(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The extra untar and the --with path are quoted when copying the project."""
    fake = install(monkeypatch)
    monkeypatch.setattr(ssh_module, "get_project_dir", lambda: io.BytesIO(b"tar"))
    config = ssh_config(tmp_path, working_dir=NASTY_DIR, copy_project_dir=True)

    ssh_module.run_ssh(config)

    cmds = commands(fake)
    assert len(cmds) >= 3  # noqa: PLR2004
    for cmd in cmds:
        assert (
            shlex.quote(NASTY_DIR) in cmd or shlex.quote(NASTY_DIR + "/pyantz") in cmd
        )
        for token in shlex.split(cmd):
            assert "pwned" not in token or token.startswith(NASTY_DIR)


def test_plain_paths_are_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary paths don't get any extra quoting."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/work")

    ssh_module.run_ssh(config)

    run_cmd = commands(fake)[-1]
    assert run_cmd.startswith("cd /srv/work && uvx ")
    assert "/srv/work/config.json" in run_cmd
