"""Test deleting directories which have content."""

import contextlib
from typing import TYPE_CHECKING

from pyantz.jobs.files.simple import DeleteParams, delete

if TYPE_CHECKING:
    from pathlib import Path


def _delete(path: Path, *, recursive: bool) -> bool:
    return delete(
        DeleteParams(path=path, recursive=recursive).model_dump(), lambda *_: None
    )


def _make_tree(root: Path) -> None:
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "file.txt").write_text("x")


def test_recursive_delete_removes_non_empty_directory(tmp_path: Path) -> None:
    """With recursive, a directory and everything in it are deleted."""
    target = tmp_path / "target"
    _make_tree(target)

    assert _delete(target, recursive=True) is True

    assert not target.exists()


def test_non_recursive_delete_keeps_non_empty_directory(tmp_path: Path) -> None:
    """By default only empty directories can be deleted (unchanged behavior)."""
    target = tmp_path / "target"
    _make_tree(target)

    with contextlib.suppress(OSError):
        _delete(target, recursive=False)

    assert (target / "sub" / "file.txt").exists()
