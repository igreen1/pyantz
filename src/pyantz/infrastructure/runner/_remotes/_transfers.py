"""Code to tar up files we wish to transfer."""

import io
import tarfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pyantz.infrastructure.config import InitialConfig

if TYPE_CHECKING:
    from typing import Any

    from pyantz.infrastructure.config import ContainerConfig, SshConfig


def add_to_tar_file(contents: str, name: str, tar: tarfile.TarFile) -> None:
    """Add our in-memory contents to the tarball."""
    content_encoded = contents.encode("utf-8")
    content_info = tarfile.TarInfo(name=name)
    content_info.size = len(content_encoded)
    content_info.mode = 0o644
    content_info.mtime = time.time()
    tar.addfile(content_info, io.BytesIO(content_encoded))


def get_project_dir() -> io.BytesIO:
    """Copy the project directory in its entirety."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tf:
        tf.add(
            Path(__file__).parent.parent.parent.parent.parent.parent, arcname="pyantz"
        )
    out.seek(0)
    return out


def get_setup_tar(
    config: InitialConfig[Any], host_config: ContainerConfig | SshConfig
) -> io.BytesIO:
    """Get a byte stream of a tar-file with the config.json and re2quirements file."""
    next_conf = config.with_new_host(host_config.subsequent_host)
    requirements = host_config.requirements

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        add_to_tar_file(next_conf.model_dump_json(), "config.json", tar)

        # save our requirements
        if requirements:
            add_to_tar_file("\n".join(requirements), "requirements.txt", tar)

    out.seek(0)
    return out


def get_cmd(
    host_config: ContainerConfig | SshConfig, addl_requirements: list[str] | None = None
) -> list[str]:
    """Get the command to run on the remote."""
    if addl_requirements is None:
        addl_requirements = []
    cmd = [
        "uvx",
    ]
    if host_config.requirements:
        cmd.extend(["--with-requirements", "requirements.txt"])
    cmd.extend(addl_requirements)
    cmd.extend(["pyantz", f"{host_config.working_dir}/config.json"])

    return cmd
