"""Test the command run on remote hosts."""

from typing import Any

import pytest

from pyantz import __version__
from pyantz.infrastructure.config import ContainerConfig, SshConfig
from pyantz.infrastructure.runner._remotes._transfers import get_cmd


def _cmd(
    host: SshConfig | ContainerConfig,
    addl_requirements: list[str] | None = None,
) -> list[str]:
    """Call get_cmd (which takes the working dir explicitly in newer versions)."""
    function: Any = get_cmd
    arguments = function.__code__.co_varnames[: function.__code__.co_argcount]
    if "working_dir" in arguments:
        return function(host, "/workspace", addl_requirements)
    return function(host, addl_requirements)


@pytest.mark.parametrize(
    "host",
    [SshConfig(remote_host="h"), ContainerConfig()],
    ids=["ssh", "container"],
)
def test_remote_runs_the_same_version(host: SshConfig | ContainerConfig) -> None:
    """The pyantz run remotely is pinned to the local version."""
    cmd = _cmd(host)

    assert cmd[:3] == ["uvx", "--from", f"pyantz=={__version__}"]
    assert cmd[-2:] == ["pyantz", "/workspace/config.json"]


def test_copied_project_replaces_the_pin() -> None:
    """With copy_project_dir the copied project is used instead of the release."""
    host = SshConfig(remote_host="h", copy_project_dir=True)

    cmd = _cmd(host, ["--with", "/pyantz"])

    assert "--from" not in cmd
    assert not any(arg.startswith("pyantz==") for arg in cmd)
    assert cmd == ["uvx", "--with", "/pyantz", "pyantz", "/workspace/config.json"]


def test_requirements_come_after_the_pin() -> None:
    """Extra requirements are still passed."""
    host = SshConfig(remote_host="h", requirements=["celery"])

    cmd = _cmd(host)

    assert cmd[cmd.index("--with-requirements") + 1] == "requirements.txt"
    assert cmd.index("--from") < cmd.index("--with-requirements")
