"""Test that the server can serve the built web ui next to the api."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from pyantz.api.backend import create_app

if TYPE_CHECKING:
    from pathlib import Path

INDEX = "<!doctype html><title>PyAntz</title><div id='root'></div>"


@pytest.fixture
def built_ui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a directory like the output of the frontend build."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    monkeypatch.setenv("PYANTZ_FRONTEND_DIR", str(tmp_path))
    monkeypatch.delenv("PYANTZ_API_TOKEN", raising=False)
    return tmp_path


def test_the_page_is_served_at_the_root(built_ui: Path) -> None:  # noqa: ARG001
    """With the directory set, the root is the web ui, and its files are there."""
    client = TestClient(create_app())

    root = client.get("/")
    asset = client.get("/assets/app.js")

    assert root.status_code == HTTPStatus.OK
    assert root.text == INDEX
    assert asset.text == "console.log('hi')"


def test_the_api_still_answers(built_ui: Path) -> None:  # noqa: ARG001
    """The page does not hide the api, which is mounted first."""
    client = TestClient(create_app())

    response = client.get("/api/v1.0/jobs/get_all_jobs")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/json"
    assert response.json()["jobs"]


def test_there_is_no_page_without_the_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing is served at the root unless asked for."""
    monkeypatch.delenv("PYANTZ_FRONTEND_DIR", raising=False)

    assert TestClient(create_app()).get("/").status_code == HTTPStatus.NOT_FOUND


def test_the_page_loads_without_the_token_but_the_api_wants_it(
    built_ui: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page has to load to be able to ask for the token."""
    monkeypatch.setenv("PYANTZ_API_TOKEN", "secret")
    client = TestClient(create_app())

    assert client.get("/").status_code == HTTPStatus.OK
    assert client.get("/api/v1.0/jobs/get_all_jobs").status_code == (
        HTTPStatus.UNAUTHORIZED
    )


def test_a_directory_without_the_page_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forgetting to build the ui is reported when the server starts."""
    monkeypatch.setenv("PYANTZ_FRONTEND_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="npm run build"):
        create_app()


def test_a_missing_directory_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory which isn't there is reported too."""
    monkeypatch.setenv("PYANTZ_FRONTEND_DIR", str(tmp_path / "nope"))

    with pytest.raises(ValueError, match=r"index\.html"):
        create_app()
