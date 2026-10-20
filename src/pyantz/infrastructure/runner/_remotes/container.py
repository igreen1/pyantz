"""Execute a pyantz pipeline inside a Docker/Podman container.

:func:`run_container` creates a container from the configured image,
copies the setup tarball into it, starts it, waits for completion, and
optionally copies results back to the host.
"""

import logging
import os
import tarfile
import tempfile
from typing import TYPE_CHECKING, cast

import docker
import docker.errors

from ._transfers import (
    DEFAULT_CONTAINER_WORKING_DIR,
    get_cmd,
    get_environment,
    get_project_dir,
    get_setup_tar,
)

# http status of a name clash
CONFLICT = 409

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyantz.infrastructure.config import ContainerConfig, InitialConfig


def _make_client(service: str) -> docker.DockerClient:
    """Create a client for the configured container service.

    Podman is reached through its docker compatible socket: ``CONTAINER_HOST``
    if set, otherwise the default rootless socket of the current user.
    """
    if service == "podman":
        socket = os.environ.get(
            "CONTAINER_HOST",
            f"unix:///run/user/{os.getuid()}/podman/podman.sock",
        )
        return docker.DockerClient(base_url=socket)
    return docker.from_env()


def _ensure_image(client: docker.DockerClient, image: str) -> None:
    """Pull the image if it isn't available locally."""
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        logging.getLogger(__name__).info("Pulling image %s", image)
        client.images.pull(image)


def _extract_output(bits: Iterable[bytes], output_dir: str) -> None:
    """Extract the archive of the working directory into the output directory.

    The archive has every entry under the directory's name (``workspace/...``);
    that leading component is removed so results land directly in *output_dir*.
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
    """Copy our files to the container and run!."""
    logger = logging.getLogger(__name__)
    if config.host.type_ != "container":
        msg = f"run_container needs a 'container' host, got {config.host.type_!r}"
        raise RuntimeError(msg)

    host_config: ContainerConfig = cast("ContainerConfig", config.host)

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
