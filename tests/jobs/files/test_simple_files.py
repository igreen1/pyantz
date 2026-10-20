"""Test the basic file operations."""

from typing import TYPE_CHECKING, Any

from pyantz.jobs.files import simple

if TYPE_CHECKING:
    from pathlib import Path


def _call(function: Any, model: Any, **parameters: Any) -> bool:  # noqa: ANN401
    return function(model(**parameters).model_dump(), lambda *_: None)


def _create(path: Path, **parameters: Any) -> bool:  # noqa: ANN401
    return _call(simple.create, simple.CreateFileParams, path=path, **parameters)


def _delete(path: Path, **parameters: Any) -> bool:  # noqa: ANN401
    return _call(simple.delete, simple.DeleteParams, path=path, **parameters)


def test_create_without_overwrite_keeps_existing_contents(tmp_path: Path) -> None:
    """Writing contents to an existing file with overwrite off fails, unchanged."""
    path = tmp_path / "f.txt"
    path.write_text("original")

    assert _create(path, contents="new", overwrite=False) is False

    assert path.read_text() == "original"


def test_create_without_overwrite_still_touches(tmp_path: Path) -> None:
    """Without contents, an existing file is just left as it is."""
    path = tmp_path / "f.txt"
    path.write_text("original")

    assert _create(path, overwrite=False) is True

    assert path.read_text() == "original"


def test_create_writes_contents_to_new_file(tmp_path: Path) -> None:
    """New files get their contents, with or without overwrite."""
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"

    assert _create(first, contents="hello", overwrite=False) is True
    assert _create(second, contents="hello") is True

    assert first.read_text() == second.read_text() == "hello"


def test_create_with_overwrite_replaces_contents(tmp_path: Path) -> None:
    """The default replaces what was there."""
    path = tmp_path / "f.txt"
    path.write_text("original")

    assert _create(path, contents="new") is True

    assert path.read_text() == "new"


def test_delete_recursive_removes_non_empty_directory(tmp_path: Path) -> None:
    """With recursive, a directory and its content are deleted."""
    target = tmp_path / "target"
    (target / "sub").mkdir(parents=True)
    (target / "sub" / "file.txt").write_text("x")

    assert _delete(target, recursive=True) is True

    assert not target.exists()


def test_delete_non_empty_directory_without_recursive_fails_cleanly(
    tmp_path: Path,
) -> None:
    """Without recursive, a non-empty directory is kept and the job fails (no raise)."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("x")

    assert _delete(target) is False

    assert (target / "file.txt").exists()


def test_delete_empty_directory_and_missing_path(tmp_path: Path) -> None:
    """Empty directories are deleted, and a missing path honours missing_ok."""
    empty = tmp_path / "empty"
    empty.mkdir()

    assert _delete(empty) is True
    assert not empty.exists()
    assert _delete(tmp_path / "nope") is True
    assert _delete(tmp_path / "nope", missing_ok=False) is False
