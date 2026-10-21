"""Test the archive of the project directory sent to remote hosts."""

from __future__ import annotations

import tarfile
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.runner._remotes._transfers import (
    find_project_root,
    get_project_dir,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def archive_names() -> list[str]:
    """Names of all the entries of the project archive."""
    with tarfile.open(fileobj=get_project_dir(), mode="r:gz") as tf:
        return tf.getnames()


def test_archive_has_the_project(archive_names: list[str]) -> None:
    """The files needed to install the project are present."""
    assert "pyantz/pyproject.toml" in archive_names
    assert "pyantz/src/pyantz/__init__.py" in archive_names


def test_archive_skips_environments_and_caches(archive_names: list[str]) -> None:
    """Version control, virtual environments and caches are not copied."""
    unwanted = (".git", ".venv", "node_modules", "__pycache__", ".pytest_cache")
    offenders = [
        name
        for name in archive_names
        if any(part in unwanted for part in name.split("/"))
        or name.endswith((".db", ".pyc"))
    ]
    assert not offenders


def test_project_root_is_found_from_a_nested_directory(tmp_path: Path) -> None:
    """The root is the closest parent which has a pyproject.toml."""
    root = tmp_path / "project"
    nested = root / "src" / "pkg" / "deep"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\n")

    assert find_project_root(nested) == root


def test_missing_project_root_is_a_clear_error(tmp_path: Path) -> None:
    """Without a pyproject.toml anywhere above, the error says what's wrong."""
    nested = tmp_path / "no" / "project"
    nested.mkdir(parents=True)

    # tmp_path is under /tmp, which has no pyproject.toml above it
    with pytest.raises(FileNotFoundError, match=r"no pyproject\.toml found"):
        find_project_root(nested)
