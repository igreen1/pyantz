"""Check whether the services needed by some integration tests are available."""

from __future__ import annotations

import socket

import docker


def docker_available(image: str | None = None) -> bool:
    """Check that a docker daemon answers (and has the image, if one is given)."""
    try:
        client = docker.from_env()
        if not client.ping():
            return False
        if image is not None:
            client.images.get(image)
    except Exception:  # noqa: BLE001  (any failure means it can't be used)
        return False
    return True


def ssh_available(host: str, port: int = 22, timeout: float = 1.0) -> bool:
    """Check that something accepts connections on the ssh port of the host."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
