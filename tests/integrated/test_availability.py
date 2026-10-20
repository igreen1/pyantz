"""Test the checks which decide whether ssh and docker tests can run."""

import socket
import time
from typing import TYPE_CHECKING

import docker
import docker.errors

from .availability import docker_available, ssh_available

if TYPE_CHECKING:
    import pytest


def test_ssh_available_when_something_listens() -> None:
    """An open port counts as available."""
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]

        assert ssh_available("127.0.0.1", port) is True


def test_ssh_unavailable_when_nothing_listens() -> None:
    """A closed port is reported as unavailable, quickly."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    started = time.monotonic()

    assert ssh_available("127.0.0.1", port) is False

    assert time.monotonic() - started < 5  # noqa: PLR2004


def test_ssh_unavailable_for_unresolvable_host() -> None:
    """A host name that doesn't resolve is unavailable, not an error."""
    assert ssh_available("host.invalid") is False


def test_docker_unavailable_without_a_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failing to reach the daemon means docker tests are skipped."""

    def _no_daemon() -> None:
        raise docker.errors.DockerException

    monkeypatch.setattr(docker, "from_env", _no_daemon)

    assert docker_available() is False


def test_docker_available_when_the_daemon_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A daemon that answers ping counts as available."""

    class Daemon:
        def ping(self) -> bool:
            return True

    monkeypatch.setattr(docker, "from_env", Daemon)

    assert docker_available() is True


def test_docker_unavailable_without_the_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A daemon which does not have the requested image is not enough."""

    class Images:
        def get(self, image: str) -> object:
            raise docker.errors.ImageNotFound(image)

    class Daemon:
        images = Images()

        def ping(self) -> bool:
            return True

    monkeypatch.setattr(docker, "from_env", Daemon)

    assert docker_available() is True
    assert docker_available("some/image:1") is False
