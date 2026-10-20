"""Test the container runner against a mocked docker client."""

import io
import os
import tarfile
from typing import TYPE_CHECKING, Any, Self

import docker
import docker.errors
import pytest
import requests

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner._remotes import container as container_module

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _output_archive() -> list[bytes]:
    """Make a tar like docker's get_archive: all entries are under the directory."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        directory = tarfile.TarInfo("workspace")
        directory.type = tarfile.DIRTYPE
        tf.addfile(directory)
        for name, content in (
            ("workspace/result.txt", b"42"),
            ("workspace/sub/a.txt", b"a"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return [buffer.getvalue()]


class FakeContainer:
    """Stand-in for a docker container."""

    def __init__(self, *, status_code: int, logs: bytes) -> None:
        """Set how the container will end."""
        self.status_code = status_code
        self._logs = logs
        self.removed = False
        self.started = False

    def put_archive(self, *_args: object) -> bool:
        """Accept the files."""
        return True

    def start(self) -> None:
        """Record the start."""
        self.started = True

    def wait(self) -> dict[str, int]:
        """Return the exit status."""
        return {"StatusCode": self.status_code}

    def logs(self) -> bytes:
        """Return the output of the container."""
        return self._logs

    def get_archive(self, _path: str) -> tuple[list[bytes], dict[str, Any]]:
        """Return the working directory as a tar archive."""
        return _output_archive(), {}

    def remove(self) -> None:
        """Record the removal."""
        self.removed = True


class FakeClient:
    """Stand-in for ``docker.DockerClient``."""

    def __init__(
        self,
        *,
        images_present: bool = True,
        status_code: int = 0,
        logs: bytes = b"",
        create_error: Exception | None = None,
    ) -> None:
        """Set how the daemon behaves."""
        self.pulled: list[str] = []
        self.create_kwargs: dict[str, Any] = {}
        self.container = FakeContainer(status_code=status_code, logs=logs)
        self._images_present = images_present
        self._create_error = create_error
        self.images = self
        self.containers = self

    def get(self, image: str) -> object:
        """Look up an image."""
        if not self._images_present:
            raise docker.errors.ImageNotFound(image)
        return object()

    def pull(self, image: str) -> None:
        """Record a pull."""
        self.pulled.append(image)

    def create(self, **kwargs: Any) -> FakeContainer:  # noqa: ANN401
        """Record the container settings."""
        if self._create_error is not None:
            raise self._create_error
        self.create_kwargs = kwargs
        return self.container

    def __enter__(self) -> Self:
        """Use as a context manager."""
        return self


def _config(output_dir: Path | None = None, **host: Any) -> InitialConfig:  # noqa: ANN401
    return InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {"type_": "local_proc", "working_directory": "/workspace"},
            "host": {
                "type_": "container",
                "output_dir": None if output_dir is None else os.fspath(output_dir),
                **host,
            },
        },
    )


def _use(monkeypatch: pytest.MonkeyPatch, client: FakeClient) -> None:
    monkeypatch.setattr(docker, "from_env", lambda: client)


def test_missing_image_is_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    """An image which isn't local is pulled before creating the container."""
    client = FakeClient(images_present=False)
    _use(monkeypatch, client)

    container_module.run_container(_config(image="example/image:1"))

    assert client.pulled == ["example/image:1"]
    assert client.create_kwargs["image"] == "example/image:1"


def test_present_image_is_not_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    """A local image is used as is."""
    client = FakeClient(images_present=True)
    _use(monkeypatch, client)

    container_module.run_container(_config())

    assert not client.pulled
    assert client.container.started
    assert client.container.removed


def test_nonzero_exit_raises_with_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing container fails the run, and shows what it printed."""
    client = FakeClient(status_code=3, logs=b"uvx: command not found")
    _use(monkeypatch, client)

    with pytest.raises(RuntimeError, match=r"(?s)status 3.*uvx: command not found"):
        container_module.run_container(_config())

    assert client.container.removed


def test_output_is_extracted_without_directory_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Results land directly in the output dir, not in output_dir/workspace."""
    _use(monkeypatch, FakeClient())
    out = tmp_path / "out"
    out.mkdir()

    container_module.run_container(_config(out))

    assert (out / "result.txt").read_text() == "42"
    assert (out / "sub" / "a.txt").read_text() == "a"
    assert not (out / "workspace").exists()


def test_output_is_still_copied_when_the_container_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partial results are available to debug a failed run."""
    _use(monkeypatch, FakeClient(status_code=1))
    out = tmp_path / "out"
    out.mkdir()

    with pytest.raises(RuntimeError, match="status 1"):
        container_module.run_container(_config(out))

    assert (out / "result.txt").exists()


def test_name_clash_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    """A container name which is taken gives a clear error."""
    response = requests.Response()
    response.status_code = 409
    clash = docker.errors.APIError("conflict", response=response)
    _use(monkeypatch, FakeClient(create_error=clash))

    with pytest.raises(RuntimeError, match="'taken' already exists"):
        container_module.run_container(_config(name="taken"))


def test_podman_uses_its_own_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """The podman option connects to the podman socket, not the docker daemon."""
    urls: list[str] = []

    def _client(base_url: str) -> FakeClient:
        urls.append(base_url)
        return FakeClient()

    monkeypatch.setattr(docker, "DockerClient", _client)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda: pytest.fail("podman must not use the docker environment"),
    )
    monkeypatch.setenv("CONTAINER_HOST", "unix:///custom/podman.sock")

    container_module.run_container(_config(container_service="podman"))

    assert urls == ["unix:///custom/podman.sock"]
