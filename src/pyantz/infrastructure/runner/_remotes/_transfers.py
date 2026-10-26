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


DEFAULT_CONTAINER_WORKING_DIR = "/workspace"
"""Where containers run when the user doesn't choose a working directory."""


def add_to_tar_file(contents: str, name: str, tar: tarfile.TarFile) -> None:
    """Add our in-memory contents to the tarball.

    Args:
        contents: the text of the file, written as UTF-8.
        name: the file's name in the archive.
        tar: the archive, open for writing.

    Returns:
        None.

    Raises:
        tarfile.TarError: if the file can't be added.

    Example:
        .. testcode::

            import io
            import tarfile

            from pyantz.infrastructure.runner._remotes._transfers import add_to_tar_file

            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w") as tar:
                add_to_tar_file("hello", "greeting.txt", tar)
            buffer.seek(0)
            with tarfile.open(fileobj=buffer) as tar:
                print(tar.extractfile("greeting.txt").read())

        .. testoutput::

            b'hello'

    """
    content_encoded = contents.encode("utf-8")
    content_info = tarfile.TarInfo(name=name)
    content_info.size = len(content_encoded)
    content_info.mode = 0o644
    content_info.mtime = time.time()
    tar.addfile(content_info, io.BytesIO(content_encoded))


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
"""Directories (at any depth) which are never copied with the project."""

EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm", ".pyc")
"""Endings of files which are never copied with the project."""


def find_project_root(start: Path) -> Path:
    """Find the project root: the closest parent of *start* with a pyproject.toml.

    Args:
        start: the directory to start looking from (included).

    Returns:
        Path: the closest directory holding a ``pyproject.toml``.

    Raises:
        FileNotFoundError: if there is none (for example, when pyantz was installed
            as a package rather than run from a source checkout)

    Example:
        .. testsetup:: remotes-project-root

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: remotes-project-root

            from pathlib import Path

            from pyantz.infrastructure.runner._remotes._transfers import (
                find_project_root,
            )

            Path("project/src/pkg").mkdir(parents=True)
            Path("project/pyproject.toml").touch()
            print(find_project_root(Path("project/src/pkg")))

        .. testoutput:: remotes-project-root

            project

        .. testcleanup:: remotes-project-root

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

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
    """Skip version control, environments, caches, databases and build outputs.

    Used as the ``filter`` when adding the project to an archive.

    Args:
        info: an entry about to be added to the archive.

    Returns:
        tarfile.TarInfo | None: the entry, or None to leave it out.

    Raises:
        None.

    Example:
        .. testcode::

            import tarfile

            from pyantz.infrastructure.runner._remotes._transfers import (
                _exclude_unneeded,
            )

            for name in ("pyantz/src/a.py", "pyantz/.git/HEAD", "pyantz/queue.db"):
                print(name, _exclude_unneeded(tarfile.TarInfo(name)) is not None)

        .. testoutput::

            pyantz/src/a.py True
            pyantz/.git/HEAD False
            pyantz/queue.db False

    """
    parts = info.name.split("/")
    if EXCLUDED_DIRECTORIES.intersection(parts) or info.name.endswith(
        EXCLUDED_SUFFIXES,
    ):
        return None
    return info


def get_project_dir() -> io.BytesIO:
    """Copy the project directory, without environments, caches and VCS files.

    Args:
        None.

    Returns:
        io.BytesIO: a gzipped tar archive of the project, under ``pyantz/``.

    Raises:
        FileNotFoundError: if pyantz isn't run from a source checkout.

    """
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
    """Get a byte stream of a tar-file with the config.json and requirements file.

    The configuration in ``config.json`` runs on the host's ``subsequent_host``;
    ``requirements.txt`` is only added if the host has requirements.

    Args:
        config: the pipeline's configuration.
        host_config: the remote host the archive is for.

    Returns:
        io.BytesIO: a gzipped tar archive, positioned at its start.

    Raises:
        None.

    Example:
        .. testcode::

            import tarfile

            from pyantz.infrastructure.config import ContainerConfig, InitialConfig
            from pyantz.infrastructure.runner._remotes._transfers import get_setup_tar

            host = ContainerConfig(requirements=["polars"])
            config = InitialConfig(
                jobs=[],
                submitter={"type_": "local_proc", "working_directory": "."},
                host=host,
            )
            with tarfile.open(fileobj=get_setup_tar(config, host)) as tar:
                print(sorted(tar.getnames()))

        .. testoutput::

            ['config.json', 'requirements.txt']

    """
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
    r"""Collect the environment variables for the remote command.

    Variables from ``environment_variables_file`` (``KEY=VALUE`` lines, read from
    this machine) are overridden by ``environment_variables``. In the file, blank
    lines and ``#`` comments are ignored, a leading ``export`` is allowed and
    quotes around values are removed.

    Args:
        host_config: the remote host's configuration.

    Returns:
        dict[str, str]: the environment variables.

    Raises:
        OSError: if the file can't be read.
        ValueError: if a line of the file isn't ``KEY=VALUE``.

    Example:
        .. testsetup:: remotes-environment

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: remotes-environment

            from pathlib import Path

            from pyantz.infrastructure.config import ContainerConfig
            from pyantz.infrastructure.runner._remotes._transfers import get_environment

            Path("vars.env").write_text("# settings\nexport A='1'\nB=2\n")
            host = ContainerConfig(
                environment_variables_file="vars.env",
                environment_variables={"B": "override"},
            )
            print(get_environment(host))

        .. testoutput:: remotes-environment

            {'A': '1', 'B': 'override'}

        .. testcleanup:: remotes-environment

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

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

    Args:
        host_config: the remote host's configuration.
        working_dir: the directory on the remote holding ``config.json``.
        addl_requirements: more arguments for ``uvx``, e.g., ``["--with", path]``.

    Returns:
        list[str]: the command.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz import __version__
            from pyantz.infrastructure.config import ContainerConfig
            from pyantz.infrastructure.runner._remotes._transfers import get_cmd

            cmd = get_cmd(ContainerConfig(), "/workspace")
            print(cmd[2] == f"pyantz=={__version__}", cmd[3:])

        .. testoutput::

            True ['pyantz', '/workspace/config.json']

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
