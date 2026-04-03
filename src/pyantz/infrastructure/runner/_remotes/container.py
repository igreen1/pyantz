"""Run remotely in a container."""

import io
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import docker

from pyantz.infrastructure.config import ContainerConfig, InitialConfig, LocalConfig


def run_container(config: InitialConfig[Any]) -> None:
    """Copy our files to the container and run!."""
    if not config.host.type_ == "container":
        raise RuntimeError

    host_config: ContainerConfig = config.host

    client = docker.from_env()

    cmd = [
        "uvx",
    ]
    if host_config.requirements:
        cmd.extend(["--with-requirements", "requirements.txt"])

    if host_config.copy_project_dir:
        cmd.extend(["--with", "/pyantz"])
    cmd.extend(["pyantz", f"{host_config.working_dir}/config.json"])

    container = client.containers.create(
        image=host_config.image,
        name=host_config.name,
        working_dir=host_config.working_dir,
        detach=True,
        command=cmd,
        # command=["/bin/sh", "-c", "sleep 120"],
    )

    try:
        _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
            f"{host_config.working_dir}/",
            _get_setup_tar(config, host_config),
        )
        if host_config.copy_project_dir:
            _copy_success = container.put_archive(  # pyright: ignore[reportUnknownMemberType]
                "/",
                _get_project_dir(),
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
                    tf.extractall(host_config.output_dir)

    finally:
        container.remove()


def _add_to_tar_file(contents: str, name: str, tar: tarfile.TarFile) -> None:
    """Add our in-memory contents to the tarball."""
    content_encoded = contents.encode("utf-8")
    content_info = tarfile.TarInfo(name=name)
    content_info.size = len(content_encoded)
    tar.addfile(content_info, io.BytesIO(content_encoded))


def _get_project_dir() -> io.BytesIO:
    """Copy the project directory in its entirety."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tf:
        tf.add(Path(__file__).parent.parent.parent.parent.parent.parent, arcname="pyantz")
    out.seek(0)
    return out


def _get_setup_tar(
    config: InitialConfig[Any], host_config: ContainerConfig
) -> io.BytesIO:
    """Get a byte stream of a tar-file with the config.json and re2quirements file."""
    local_conf = _get_local_config(config)
    requirements = host_config.requirements

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        _add_to_tar_file(local_conf.model_dump_json(), "config.json", tar)

        # save our requirements
        if requirements:
            _add_to_tar_file("\n".join(requirements), "requirements.txt", tar)

    out.seek(0)
    return out


def _get_local_config(config: InitialConfig[Any]) -> InitialConfig[Any]:
    """Run locally on the container."""
    return config.model_copy(
        update={
            "host": LocalConfig(),
        },
    )
