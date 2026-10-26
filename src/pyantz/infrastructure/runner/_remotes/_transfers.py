"""Utilities for packaging and transferring files to remote execution environments.

:func:`get_setup_tar` bundles the resolved pipeline config and any extra
Python requirements into an in-memory tar archive.  :func:`get_cmd` builds
the ``uvx pyantz …`` invocation that the remote side runs after extracting
the archive.
"""

from __future__ import annotations

import io
import tarfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyantz.infrastructure.config import ContainerConfig, InitialConfig, SshConfig


# where containers run when the user doesn't choose a working directory
DEFAULT_CONTAINER_WORKING_DIR = "/workspace"


def add_to_tar_file(contents: str, name: str, tar: tarfile.TarFile) -> None:
    """Add our in-memory contents to the tarball."""
    content_encoded = contents.encode("utf-8")
    content_info = tarfile.TarInfo(name=name)
    content_info.size = len(content_encoded)
    content_info.mode = 0o644
    content_info.mtime = time.time()
    tar.addfile(content_info, io.BytesIO(content_encoded))


# directories (at any depth) and file patterns which are never copied
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
    },
)
EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm", ".pyc")


def find_project_root(start: Path) -> Path:
    """Find the project root: the closest parent of *start* with a pyproject.toml.

    Raises:
        FileNotFoundError: if there is none (for example, when pyantz was installed
            as a package rather than run from a source checkout)

    """
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    msg = (
        f"Cannot copy the project directory: no pyproject.toml found in {start} "
        "or its parents (copy_project_dir needs a source checkout of pyantz)"
    )
    raise FileNotFoundError(msg)


def _exclude_unneeded(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    """Skip version control, environments, caches, databases and build outputs."""
    parts = info.name.split("/")
    if EXCLUDED_DIRECTORIES.intersection(parts) or info.name.endswith(
        EXCLUDED_SUFFIXES,
    ):
        return None
    return info


def get_project_dir() -> io.BytesIO:
    """Copy the project directory, without environments, caches and VCS files."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tf:
        tf.add(
            find_project_root(Path(__file__).resolve().parent),
            arcname="pyantz",
            filter=_exclude_unneeded,
        )
    out.seek(0)
    return out


def get_setup_tar(
    config: InitialConfig, host_config: ContainerConfig | SshConfig
) -> io.BytesIO:
    """Get a byte stream of a tar-file with the config.json and requirements file."""
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


def get_environment(host_config: ContainerConfig | SshConfig) -> dict[str, str]:
    """Collect the environment variables for the remote command.

    Variables from ``environment_variables_file`` (``KEY=VALUE`` lines, read from
    this machine) are overridden by ``environment_variables``.
    """
    environment: dict[str, str] = {}
    if host_config.environment_variables_file:
        file_text = Path(host_config.environment_variables_file).read_text(
            encoding="utf-8",
        )
        for raw_line in file_text.splitlines():
            line = raw_line.strip().removeprefix("export ").strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if not separator or not name.strip():
                msg = f"Invalid line in environment variables file: {raw_line!r}"
                raise ValueError(msg)
            environment[name.strip()] = value.strip().strip("\"'")
    environment.update(host_config.environment_variables)
    return environment


def get_cmd(
    host_config: ContainerConfig | SshConfig,
    working_dir: str,
    addl_requirements: list[str] | None = None,
) -> list[str]:
    """Get the command to run on the remote.

    Unless the project directory is copied (and added through
    ``addl_requirements``), the remote runs the same version of pyantz as the
    local machine, and has *working_dir* as its cwd, so that the configuration
    means the same thing on both.
    """
    from pyantz import __version__  # noqa: PLC0415  (circular import at module level)

    if addl_requirements is None:
        addl_requirements = []
    cmd = [
        "uvx",
    ]
    if not host_config.copy_project_dir:
        cmd.extend(["--from", f"pyantz=={__version__}"])
    if host_config.requirements:
        cmd.extend(["--with-requirements", "requirements.txt"])
    cmd.extend(addl_requirements)
    cmd.extend(["pyantz", f"{working_dir}/config.json"])

    return cmd
