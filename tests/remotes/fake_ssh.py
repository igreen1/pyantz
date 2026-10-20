"""A fake paramiko SSH client, to test the ssh runner without a server."""

import io
import posixpath
from typing import TYPE_CHECKING, Any, Self

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner._remotes import ssh as ssh_module

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOP = "pyantz.jobs.testing.nop.do_nothing"


class FakeChannel:
    """The part of a paramiko channel which gives the exit status."""

    def __init__(self, exit_code: int) -> None:
        """Set the exit status to report."""
        self._exit_code = exit_code

    def recv_exit_status(self) -> int:
        """Return the exit status of the command."""
        return self._exit_code


class FakeStream:
    """Stand-in for the stdout/stderr file objects of ``exec_command``."""

    def __init__(self, output: str, exit_code: int) -> None:
        """Set what the command wrote and its exit status."""
        self._output = output.encode()
        self.channel = FakeChannel(exit_code)

    def read(self) -> bytes:
        """Return everything the command wrote."""
        return self._output


class FakeSftp:
    """Stand-in for a paramiko SFTP client with a tiny in-memory file system."""

    def __init__(self, client: type[FakeSshClient]) -> None:
        """Share the recorded state of the client."""
        self._client = client

    def mkdir(self, path: str) -> None:
        """Create a directory like sftp does: no parents, and it must not exist."""
        self._client.calls.append(("mkdir", path))
        if path in self._client.existing_dirs:
            msg = "Failure"
            raise OSError(msg)
        if posixpath.dirname(path) not in self._client.existing_dirs:
            msg = "No such file"
            raise OSError(msg)
        self._client.existing_dirs.add(path)

    def put(self, _local: str, remote: str) -> None:
        """Record an upload."""
        self._client.calls.append(("put", remote))

    def close(self) -> None:
        """Record that the sftp session was closed."""
        self._client.calls.append(("sftp_close", ""))


class FakeSshClient:
    """Stand-in for ``paramiko.SSHClient`` which records what it was asked to do.

    ``responses`` maps a text to look for in a command to the
    ``(exit code, stdout, stderr)`` the fake returns for it.
    """

    calls: list[tuple[str, Any]]
    responses: dict[str, tuple[int, str, str]]
    existing_dirs: set[str]

    def load_system_host_keys(self) -> None:
        """Accept the call."""

    def set_missing_host_key_policy(self, _policy: object) -> None:
        """Accept the call."""

    def load_host_keys(self, _filename: str) -> None:
        """Accept the call."""

    def connect(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Record the connection settings."""
        type(self).calls.append(("connect", kwargs))

    def open_sftp(self) -> FakeSftp:
        """Return a fake sftp session."""
        return FakeSftp(type(self))

    def exec_command(
        self,
        cmd: str,
        **_kwargs: Any,  # noqa: ANN401
    ) -> tuple[io.BytesIO, FakeStream, FakeStream]:
        """Record the command and answer with the configured response."""
        type(self).calls.append(("exec", cmd))
        exit_code, stdout, stderr = 0, "", ""
        for text, response in type(self).responses.items():
            if text in cmd:
                exit_code, stdout, stderr = response
                break
        return (
            io.BytesIO(),
            FakeStream(stdout, exit_code),
            FakeStream(stderr, exit_code),
        )

    def close(self) -> None:
        """Record that the connection was closed."""
        type(self).calls.append(("close", ""))

    def __enter__(self) -> Self:
        """Use as a context manager."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Close when leaving the context."""
        self.close()


def install(monkeypatch: pytest.MonkeyPatch) -> type[FakeSshClient]:
    """Replace paramiko's client in the ssh runner with a fresh fake."""
    fake = type(
        "FakeSshClient",
        (FakeSshClient,),
        {"calls": [], "responses": {}, "existing_dirs": {"/", "/srv"}},
    )
    monkeypatch.setattr(ssh_module.paramiko, "SSHClient", fake)
    return fake


def ssh_config(tmp_path: Path, **host: Any) -> InitialConfig[Any]:  # noqa: ANN401
    """Make a config which runs one job on an ssh host."""
    return InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {
                "type_": "local_proc",
                "working_directory": str(tmp_path),
            },
            "host": {
                "type_": "ssh",
                "remote_host": "remote.example",
                "remote_user": "me",
                "run_async": False,
                **host,
            },
        },
    )


def commands(fake: type[FakeSshClient]) -> list[str]:
    """Get every command run through ``exec_command``."""
    return [arg for kind, arg in fake.calls if kind == "exec"]
