"""Test copying and moving files."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.jobs.files import moving

if TYPE_CHECKING:
    from pathlib import Path


def _run(function: Any, **parameters: Any) -> bool:  # noqa: ANN401
    model = {
        "rsync": moving.RsyncParams,
        "copy": moving.CopyParams,
        "move": moving.MoveParams,
    }
    name = function.__name__
    return function(model[name](**parameters).model_dump(), lambda *_: None)


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync is not installed")
def test_rsync_of_a_file_succeeds(tmp_path: Path) -> None:
    """A successful rsync is reported as a success (was an AttributeError)."""
    source = tmp_path / "source.txt"
    source.write_text("data")
    destination = tmp_path / "dest.txt"

    assert _run(moving.rsync, source=source, destination=destination) is True

    assert destination.read_text() == "data"


def test_rsync_without_rsync_installed_fails_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing rsync binary is a failed job, not an exception."""
    source = tmp_path / "source.txt"
    source.write_text("data")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert _run(moving.rsync, source=source, destination=tmp_path / "d") is False


def test_failed_overwriting_copy_keeps_the_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the copy fails, the existing destination is untouched."""
    source = tmp_path / "source.txt"
    source.write_text("new")
    destination = tmp_path / "dest.txt"
    destination.write_text("precious")

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(shutil, "copy2", _fail)

    assert _run(moving.copy, source=source, destination=destination) is False

    assert destination.read_text() == "precious"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest.txt", "source.txt"]


def test_failed_overwriting_directory_copy_keeps_the_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same holds for directories."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("a")
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "old.txt").write_text("old")

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(shutil, "copytree", _fail)

    assert _run(moving.copy, source=source, destination=destination) is False

    assert (destination / "old.txt").read_text() == "old"


def test_overwriting_copy_replaces_the_destination(tmp_path: Path) -> None:
    """A working overwrite replaces files and directories, leaving no temp files."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "new.txt").write_text("new")
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "old.txt").write_text("old")

    assert _run(moving.copy, source=source, destination=destination) is True

    assert [p.name for p in destination.iterdir()] == ["new.txt"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest", "source"]


def test_copy_without_overwrite_refuses(tmp_path: Path) -> None:
    """With overwrite off an existing destination is left alone."""
    source = tmp_path / "source.txt"
    source.write_text("new")
    destination = tmp_path / "dest.txt"
    destination.write_text("old")

    assert (
        _run(moving.copy, source=source, destination=destination, overwrite=False)
        is False
    )

    assert destination.read_text() == "old"


def test_failed_overwriting_move_restores_the_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the move fails the old destination comes back."""
    source = tmp_path / "source.txt"
    source.write_text("new")
    destination = tmp_path / "dest.txt"
    destination.write_text("precious")

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(shutil, "move", _fail)

    assert _run(moving.move, source=source, destination=destination) is False

    assert destination.read_text() == "precious"
    assert source.read_text() == "new"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest.txt", "source.txt"]


def test_overwriting_move_replaces_the_destination(tmp_path: Path) -> None:
    """A working overwriting move replaces the destination and removes the source."""
    source = tmp_path / "source.txt"
    source.write_text("new")
    destination = tmp_path / "dest.txt"
    destination.write_text("old")

    assert _run(moving.move, source=source, destination=destination) is True

    assert destination.read_text() == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["dest.txt"]
