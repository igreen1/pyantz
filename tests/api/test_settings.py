"""Test the api server settings."""

import importlib
import sys
from typing import Any

import pytest

from pyantz.api import backend, dev_server
from pyantz.api.settings import get_settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without variables the server listens on localhost:8000."""
    monkeypatch.delenv("PYANTZ_HOST", raising=False)
    monkeypatch.delenv("PYANTZ_PORT", raising=False)

    settings = get_settings()

    assert (settings.host, settings.port) == ("127.0.0.1", 8000)


def test_values_are_read_when_asked_not_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A change of environment after import is seen."""
    monkeypatch.setenv("PYANTZ_HOST", "0.0.0.0")  # noqa: S104
    monkeypatch.setenv("PYANTZ_PORT", "9001")

    settings = get_settings()

    assert (settings.host, settings.port) == ("0.0.0.0", 9001)  # noqa: S104


@pytest.mark.parametrize("port", ["abc", "0", "70000", ""])
def test_invalid_port_gives_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    port: str,
) -> None:
    """The error names the variable and the value."""
    monkeypatch.setenv("PYANTZ_PORT", port)

    with pytest.raises(ValueError, match="PYANTZ_PORT") as info:
        get_settings()

    assert repr(port) in str(info.value)


def test_importing_the_server_with_a_bad_port_does_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only starting a server fails; importing it does not."""
    monkeypatch.setenv("PYANTZ_PORT", "not-a-port")
    sys.modules.pop("pyantz.api.dev_server", None)

    module = importlib.import_module("pyantz.api.dev_server")

    assert callable(module.start_dev_server)
    sys.modules["pyantz.api.dev_server"] = dev_server


@pytest.mark.parametrize(
    "starter", [backend.start_prod_server, dev_server.start_dev_server]
)
def test_both_servers_use_the_same_settings(
    monkeypatch: pytest.MonkeyPatch,
    starter: Any,  # noqa: ANN401
) -> None:
    """Prod and dev servers pass the settings to uvicorn."""
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "uvicorn.run",
        lambda *_args, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setenv("PYANTZ_HOST", "10.0.0.5")
    monkeypatch.setenv("PYANTZ_PORT", "1234")

    starter()

    assert calls[0]["host"] == "10.0.0.5"
    assert calls[0]["port"] == 1234  # noqa: PLR2004


@pytest.mark.parametrize(
    "starter", [backend.start_prod_server, dev_server.start_dev_server]
)
def test_starting_with_a_bad_port_fails_with_a_clear_message(
    monkeypatch: pytest.MonkeyPatch,
    starter: Any,  # noqa: ANN401
) -> None:
    """Starting a server with an invalid port explains the problem."""
    monkeypatch.setenv("PYANTZ_PORT", "99999")

    with pytest.raises(ValueError, match="PYANTZ_PORT"):
        starter()
