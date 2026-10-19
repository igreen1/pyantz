"""Test results copied out of a container can't escape the output directory."""

import contextlib
import io
import tarfile
from typing import TYPE_CHECKING, Any

import docker
import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner._remotes import container as container_module

if TYPE_CHECKING:
    from pathlib import Path


def _archive(names: list[str]) -> list[bytes]:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = 4
            tf.addfile(info, io.BytesIO(b"data"))
    return [buffer.getvalue()]


class _Container:
    def __init__(self, names: list[str]) -> None:
        self._names = names
        self.removed = False

    def put_archive(self, *_args: object) -> bool:
        return True

    def start(self) -> None:
        return None

    def wait(self) -> dict[str, int]:
        return {"StatusCode": 0}

    def get_archive(self, _path: str) -> tuple[list[bytes], dict[str, Any]]:
        return _archive(self._names), {}

    def remove(self) -> None:
        self.removed = True


class _Docker:
    def __init__(self, container: _Container) -> None:
        self.containers = self
        self.images = self
        self._container = container

    def get(self, _image: str) -> object:
        return object()

    def create(self, **_kwargs: Any) -> _Container:  # noqa: ANN401
        return self._container


def _run(names: list[str], output: Path, monkeypatch: pytest.MonkeyPatch) -> _Container:
    container = _Container(names)
    monkeypatch.setattr(docker, "from_env", lambda: _Docker(container))
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}
            ],
            "submitter": {"type_": "local_proc", "working_directory": "/workspace"},
            "host": {"type_": "container", "output_dir": str(output)},
        },
    )
    container_module.run_container(config)
    return container


def test_path_traversal_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An archive entry that climbs out of the output directory is refused."""
    output = tmp_path / "out"
    output.mkdir()

    with pytest.raises(tarfile.FilterError):
        _run(["workspace/ok.txt", "../evil"], output, monkeypatch)

    assert not (tmp_path / "evil").exists()


def test_absolute_paths_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absolute paths in the archive can't be written elsewhere."""
    output = tmp_path / "out"
    output.mkdir()
    target = tmp_path / "absolute_evil"

    with contextlib.suppress(tarfile.FilterError):
        _run([str(target)], output, monkeypatch)

    assert not target.exists()


def test_container_is_removed_even_if_extraction_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The container is cleaned up when the results are refused."""
    output = tmp_path / "out"
    output.mkdir()
    container = _Container(["../evil"])
    monkeypatch.setattr(docker, "from_env", lambda: _Docker(container))
    config = InitialConfig.model_validate(
        {
            "jobs": [
                {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}
            ],
            "submitter": {"type_": "local_proc", "working_directory": "/workspace"},
            "host": {"type_": "container", "output_dir": str(output)},
        },
    )

    with pytest.raises(tarfile.FilterError):
        container_module.run_container(config)

    assert container.removed


def test_normal_results_are_extracted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Well formed archives still work."""
    output = tmp_path / "out"
    output.mkdir()

    _run(["workspace/ok.txt"], output, monkeypatch)

    assert (output / "workspace" / "ok.txt").read_text() == "data"
