"""Code to tar up files we wish to transfer."""

import io
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyantz.infrastructure.config import ContainerConfig, SshConfig


def add_to_tar_file(contents: str, name: str, tar: tarfile.TarFile) -> None:
    """Add our in-memory contents to the tarball."""
    content_encoded = contents.encode("utf-8")
    content_info = tarfile.TarInfo(name=name)
    content_info.size = len(content_encoded)
    tar.addfile(content_info, io.BytesIO(content_encoded))


def get_project_dir() -> io.BytesIO:
    """Copy the project directory in its entirety."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tf:
        tf.add(
            Path(__file__).parent.parent.parent.parent.parent.parent, arcname="pyantz"
        )
    out.seek(0)
    return out


def get_setup_tar(host_config: ContainerConfig | SshConfig) -> io.BytesIO:
    """Get a byte stream of a tar-file with the config.json and re2quirements file."""
    local_conf = host_config.subsequent_config
    requirements = host_config.requirements

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        add_to_tar_file(local_conf.model_dump_json(), "config.json", tar)

        # save our requirements
        if requirements:
            add_to_tar_file("\n".join(requirements), "requirements.txt", tar)

    out.seek(0)
    return out


def get_cmd(host_config: ContainerConfig | SshConfig) -> list[str]:
    """Get the command to run on the remote."""
    cmd = [
        "uvx",
    ]
    if host_config.requirements:
        cmd.extend(["--with-requirements", "requirements.txt"])
    if host_config.copy_project_dir:
        cmd.extend(["--with", "/pyantz"])
    cmd.extend(["pyantz", f"{host_config.working_dir}/config.json"])

    return cmd
