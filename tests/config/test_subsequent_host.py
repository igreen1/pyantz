"""Test ``subsequent_host`` is selected by its ``type_`` discriminator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import ContainerConfig, LocalConfig, SshConfig


def test_container_selected_by_type() -> None:
    """A dict with type_ container becomes a ContainerConfig."""
    ssh = SshConfig.model_validate(
        {"remote_host": "h", "subsequent_host": {"type_": "container"}},
    )
    assert isinstance(ssh.subsequent_host, ContainerConfig)


def test_nested_ssh_chain() -> None:
    """Hops can be chained through several remote hosts."""
    ssh = SshConfig.model_validate(
        {
            "remote_host": "bastion",
            "subsequent_host": {
                "type_": "ssh",
                "remote_host": "inner",
                "subsequent_host": {"type_": "container", "name": "c"},
            },
        },
    )
    inner = ssh.subsequent_host
    assert isinstance(inner, SshConfig)
    assert isinstance(inner.subsequent_host, ContainerConfig)
    assert inner.subsequent_host.name == "c"


def test_default_is_local() -> None:
    """Without a subsequent host, the work stays on the remote host itself."""
    assert isinstance(SshConfig(remote_host="h").subsequent_host, LocalConfig)


def test_invalid_type_gives_discriminator_error() -> None:
    """An unknown type_ is reported as a discriminator problem."""
    with pytest.raises(ValidationError, match="union_tag_invalid") as exc_info:
        SshConfig.model_validate(
            {"remote_host": "h", "subsequent_host": {"type_": "carrier-pigeon"}},
        )
    # one error from the discriminator, not one per union member
    assert exc_info.value.error_count() == 1


def test_errors_point_at_the_selected_host() -> None:
    """A problem inside the selected host is not mixed with other hosts' errors."""
    with pytest.raises(ValidationError) as exc_info:
        SshConfig.model_validate(
            {"remote_host": "h", "subsequent_host": {"type_": "ssh"}},
        )
    errors = exc_info.value.errors()
    assert [error["loc"] for error in errors] == [
        ("subsequent_host", "ssh", "remote_host"),
    ]
