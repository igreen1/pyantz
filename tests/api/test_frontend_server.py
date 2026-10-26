"""Test `pyantz-frontend`, which serves the ui of ``pyantz[frontend]``."""

from __future__ import annotations

import sys
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from pyantz.api import frontend_server

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi import FastAPI

INDEX = "<!doctype html><title>PyAntz</title><div id='root'></div>"


@pytest.fixture
def installed_ui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make `pyantz_frontend` importable, with a built ui."""
    package = tmp_path / "pyantz_frontend"
    (package / "static").mkdir(parents=True)
    (package / "static" / "index.html").write_text(INDEX)
    (package / "__init__.py").write_text(
        "from pathlib import Path\nSTATIC_DIR = Path(__file__).parent / 'static'\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "pyantz_frontend", raising=False)
    monkeypatch.delenv("PYANTZ_FRONTEND_DIR", raising=False)
    monkeypatch.delenv("PYANTZ_API_TOKEN", raising=False)
    return package / "static"


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture what the server would run instead of listening."""
    captured: dict[str, Any] = {}

    def fake_run(application: FastAPI, **kwargs: Any) -> None:  # noqa: ANN401
        captured["app"] = application
        captured.update(kwargs)

    monkeypatch.setattr(frontend_server.uvicorn, "run", fake_run)
    return captured


def test_it_serves_the_installed_ui_and_the_api(
    installed_ui: Path,  # noqa: ARG001
    served: dict[str, Any],
) -> None:
    """The ui is at the root and the api is next to it."""
    frontend_server.start_frontend_server()
    client = TestClient(served["app"])

    assert client.get("/").text == INDEX
    assert client.get("/api/v1.0/jobs/get_all_jobs").status_code == HTTPStatus.OK
    assert served["host"] == "127.0.0.1"


def test_the_environment_can_name_another_build(
    installed_ui: Path,  # noqa: ARG001
    served: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`PYANTZ_FRONTEND_DIR` wins over the installed ui."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "index.html").write_text("other")
    monkeypatch.setenv("PYANTZ_FRONTEND_DIR", str(other))

    frontend_server.start_frontend_server()

    assert TestClient(served["app"]).get("/").text == "other"


def test_without_the_feature_it_says_how_to_install_it(
    served: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A base install names the extra to install."""
    monkeypatch.setitem(sys.modules, "pyantz_frontend", None)
    monkeypatch.delenv("PYANTZ_FRONTEND_DIR", raising=False)

    with pytest.raises(SystemExit, match=r"pyantz\[frontend\]"):
        frontend_server.start_frontend_server()

    assert not served


def test_an_unbuilt_ui_is_refused(installed_ui: Path, served: dict[str, Any]) -> None:
    """A package without the build output is reported, not served."""
    (installed_ui / "index.html").unlink()

    with pytest.raises(SystemExit, match="not built"):
        frontend_server.start_frontend_server()

    assert not served


def test_it_will_not_listen_on_the_network_without_a_token(
    installed_ui: Path,  # noqa: ARG001
    served: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same rule as the other servers applies."""
    monkeypatch.setenv("PYANTZ_HOST", "0.0.0.0")  # noqa: S104

    with pytest.raises(SystemExit, match="PYANTZ_API_TOKEN"):
        frontend_server.start_frontend_server()

    assert not served
