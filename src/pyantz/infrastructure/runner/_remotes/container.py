"""Run remotely in a container."""

import tarfile
import tempfile
from typing import TYPE_CHECKING, Any, cast

import docker

from ._transfers import get_cmd, get_project_dir, get_setup_tar

if TYPE_CHECKING:
    from pyantz.infrastructure.config import ContainerConfig, InitialConfig


def run_container(config: InitialConfig[Any]) -> None:
    """Copy our files to the container and run!."""
    if not config.host.type_ == "container":
        raise RuntimeError

    host_config: ContainerConfig = cast("ContainerConfig", config.host)

    client = docker.from_env()
    addl_req = []
    if host_config.copy_project_dir:
        addl_req = ["--with", "/pyantz"]
    cmd = get_cmd(host_config, addl_req)
    container = client.containers.create(
        image=host_config.image,
        name=host_config.name,
        working_dir=host_config.working_dir,
        detach=True,
        command=cmd,
    )

    try:
        _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
            f"{host_config.working_dir}/",
            get_setup_tar(config, host_config),
        )
        if host_config.copy_project_dir:
            _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
                "/",
                get_project_dir(),
            )
        container.start()
        _result = container.wait()

        if host_config.output_dir:
            bits, _stat = container.get_archive(host_config.working_dir + "/")
            with tempfile.TemporaryFile(mode="wb+") as fh:
                for chunk in bits:
                    fh.write(chunk)
                fh.seek(0)
                with tarfile.open(fileobj=fh, mode="r:*") as tf:
                    tf.extractall(host_config.output_dir)  # noqa: S202

    finally:
        container.remove()
