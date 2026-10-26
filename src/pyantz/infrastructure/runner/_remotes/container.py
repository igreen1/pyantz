"""Execute a pyantz pipeline inside a Docker/Podman container.

:func:`run_container` creates a container from the configured image,
copies the setup tarball into it, starts it, waits for completion, and
optionally copies results back to the host.
"""

from __future__ import annotations

import logging
import os
import sys
import tarfile
import tempfile
from typing import TYPE_CHECKING

import docker
import docker.errors

from ._transfers import (
    DEFAULT_CONTAINER_WORKING_DIR,
    get_cmd,
    get_environment,
    get_project_dir,
    get_setup_tar,
)

CONFLICT = 409
"""HTTP status of a name clash."""

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyantz.infrastructure.config import ContainerConfig, InitialConfig


def _make_client(service: str) -> docker.DockerClient:
    """Create a client for the configured container service.

    Podman is reached through its docker compatible socket: ``CONTAINER_HOST``
    if set, otherwise the default rootless socket of the current user (on
    Windows, the pipe of the default podman machine).

    Args:
        service: ``docker`` or ``podman``.

    Returns:
        docker.DockerClient: the client.

    Raises:
        docker.errors.DockerException: if the service can't be reached.

    """
    if service == "podman":
        socket = os.environ.get("CONTAINER_HOST")
        if socket is None:
            socket = (
                "npipe:////./pipe/podman-machine-default"
                if sys.platform == "win32"
                else f"unix:///run/user/{os.getuid()}/podman/podman.sock"
            )
        return docker.DockerClient(base_url=socket)
    return docker.from_env()


def _ensure_image(client: docker.DockerClient, image: str) -> None:
    """Pull the image if it isn't available locally.

    Args:
        client: the container service's client.
        image: the image's name.

    Returns:
        None.

    Raises:
        docker.errors.APIError: if the image can't be pulled.

    """
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        logging.getLogger(__name__).info("Pulling image %s", image)
        client.images.pull(image)


def _extract_output(bits: Iterable[bytes], output_dir: str) -> None:
    """Extract the archive of the working directory into the output directory.

    The archive has every entry under the directory's name (``workspace/...``);
    that leading component is removed so results land directly in *output_dir*.

    Args:
        bits: the archive, in chunks, as returned by the container service.
        output_dir: the directory to extract into.

    Returns:
        None.

    Raises:
        tarfile.TarError: if the archive is invalid or has unsafe entries.

    Example:
        .. testsetup:: remotes-extract

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: remotes-extract

            import io
            import tarfile
            from pathlib import Path

            from pyantz.infrastructure.runner._remotes._transfers import add_to_tar_file
            from pyantz.infrastructure.runner._remotes.container import _extract_output

            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w") as tar:
                add_to_tar_file("done", "workspace/result.txt", tar)
            _extract_output([buffer.getvalue()], "results")
            print(Path("results/result.txt").read_text())

        .. testoutput:: remotes-extract

            done

        .. testcleanup:: remotes-extract

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    with tempfile.TemporaryFile(mode="wb+") as fh:
        for chunk in bits:
            fh.write(chunk)
        fh.seek(0)
        with tarfile.open(fileobj=fh, mode="r:*") as tf:
            members: list[tarfile.TarInfo] = []
            for member in tf.getmembers():
                _, _, relative = member.name.partition("/")
                if not relative:
                    continue  # the directory itself
                member.name = relative
                members.append(member)
            tf.extractall(output_dir, members=members, filter="data")


def run_container(config: InitialConfig) -> None:
    """Copy our files to the container and run!.

    A container is created from the configured image (with the configured name,
    if any), the configuration (and, if asked, the project) is copied into it,
    and it runs pyantz until done. The working directory is copied to
    ``output_dir`` if set, and the container is removed.

    Args:
        config: the pipeline's configuration, with a ``container`` host.

    Returns:
        None.

    Raises:
        RuntimeError: if the host isn't a container, a container with the name
            already exists, or the container exits with a non-zero status.
        docker.errors.DockerException: if the container service fails.

    """
    logger = logging.getLogger(__name__)
    if config.host.type_ != "container":
        msg = f"run_container needs a 'container' host, got {config.host.type_!r}"
        raise RuntimeError(msg)

    host_config: ContainerConfig = config.host

    working_dir = host_config.working_dir or DEFAULT_CONTAINER_WORKING_DIR

    client = _make_client(host_config.container_service)
    _ensure_image(client, host_config.image)
    addl_req = []
    if host_config.copy_project_dir:
        addl_req = ["--with", "/pyantz"]
    cmd = get_cmd(host_config, working_dir, addl_req)
    try:
        container = client.containers.create(
            image=host_config.image,
            name=host_config.name,
            working_dir=working_dir,
            detach=True,
            command=cmd,
            environment=get_environment(host_config),
        )
    except docker.errors.APIError as exc:
        if exc.status_code == CONFLICT:
            msg = f"A container named {host_config.name!r} already exists"
            raise RuntimeError(msg) from exc
        raise

    try:
        _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
            f"{working_dir}/",
            get_setup_tar(config, host_config),
        )
        if host_config.copy_project_dir:
            _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
                "/",
                get_project_dir(),
            )
        container.start()
        status_code = container.wait()["StatusCode"]
        logs = container.logs().decode(errors="replace")
        logger.info("Container output:\n%s", logs)

        if host_config.output_dir:
            bits, _stat = container.get_archive(working_dir + "/")
            _extract_output(bits, host_config.output_dir)

        if status_code != 0:
            msg = f"Container exited with status {status_code}. Output:\n{logs}"
            raise RuntimeError(msg)
    finally:
        container.remove()
