"""Test the working directory is created on the remote in a way that can repeat."""

from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.runner._remotes import ssh as ssh_module

from .fake_ssh import commands, install, ssh_config

if TYPE_CHECKING:
    from pathlib import Path


def test_directory_is_created_with_parents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested working dir is made with `mkdir -p`, not with sftp mkdir."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/a/b/c")

    ssh_module.run_ssh(config)

    assert commands(fake)[0] == "mkdir -p /srv/a/b/c"
    assert not [call for call in fake.calls if call[0] == "mkdir"]
    assert ("put", "/srv/a/b/c/setup.tar.gz") in fake.calls


def test_existing_directory_is_fine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running twice with the same directory doesn't raise (mkdir -p succeeds)."""
    fake = install(monkeypatch)
    fake.existing_dirs.add("/srv/work")
    config = ssh_config(tmp_path, working_dir="/srv/work")

    ssh_module.run_ssh(config)
    ssh_module.run_ssh(config)

    assert commands(fake).count("mkdir -p /srv/work") == 2  # noqa: PLR2004


def test_failure_to_create_directory_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the remote can't create the directory, the error says why."""
    fake = install(monkeypatch)
    fake.responses["mkdir -p"] = (
        1,
        "",
        "mkdir: cannot create directory: Permission denied",
    )
    config = ssh_config(tmp_path, working_dir="/root/work")

    with pytest.raises(RuntimeError, match="Permission denied"):
        ssh_module.run_ssh(config)

    assert not [call for call in fake.calls if call[0] == "put"]


def test_directory_with_spaces_is_quoted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unusual characters in the path don't change what is run."""
    fake = install(monkeypatch)
    config = ssh_config(tmp_path, working_dir="/srv/my work; ls")

    ssh_module.run_ssh(config)

    assert commands(fake)[0] == "mkdir -p '/srv/my work; ls'"
