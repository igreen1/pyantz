"""Test checking if a file contains some text."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pyantz.jobs.files.check import FileContentsParams, file_contains

if TYPE_CHECKING:
    from pathlib import Path


def _contains(path: Path, substring: str) -> bool:
    params = FileContentsParams(file=path, substring=substring).model_dump()
    return file_contains(params, lambda *_: None)


def test_empty_file_does_not_contain_text(tmp_path: Path) -> None:
    """An empty file contains nothing, and doesn't make the job error."""
    empty = tmp_path / "empty.txt"
    empty.touch()

    assert _contains(empty, "x") is False


def test_empty_file_contains_the_empty_string(tmp_path: Path) -> None:
    """The empty substring is in every file."""
    empty = tmp_path / "empty.txt"
    empty.touch()

    assert _contains(empty, "") is True


@pytest.mark.parametrize(
    ("text", "substring", "expected"),
    [("hello\nworld", "lo\nwo", True), ("hello", "bye", False), ("héllo", "é", True)],
)
def test_non_empty_files_are_unchanged(
    tmp_path: Path,
    text: str,
    substring: str,
    expected: bool,  # noqa: FBT001
) -> None:
    """Searching real content works as before, including across lines."""
    path = tmp_path / "f.txt"
    path.write_text(text, encoding="utf-8")

    assert _contains(path, substring) is expected


def test_missing_file_is_false(tmp_path: Path) -> None:
    """A file which doesn't exist doesn't contain anything."""
    assert _contains(tmp_path / "nope", "x") is False
