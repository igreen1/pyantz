"""Test the endpoint returning the parameter schema of a job."""

from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from pyantz.api.backend import app
from pyantz.api.endpoints.get_parameters import endpoints

if TYPE_CHECKING:
    import pytest

client = TestClient(app)


def test_job_without_a_parameter_model_names_the_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The error says which job lacks a model (the placeholder was not filled in)."""

    def _no_model() -> None:
        return None

    monkeypatch.setattr(
        endpoints,
        "get_registered_functions",
        lambda _name=None: [_no_model],
    )

    response = client.get("/api/v1.0/jobs/schema/some.job")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "No parameter model for: some.job"


def test_unknown_job_is_not_found() -> None:
    """A job which isn't registered is a 404 naming it."""
    response = client.get("/api/v1.0/jobs/schema/no.such.job")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "no.such.job" in response.json()["detail"]


def test_known_job_returns_its_schema() -> None:
    """A registered job returns its path and json schema."""
    response = client.get(
        "/api/v1.0/jobs/schema/pyantz.jobs.subproc.dispatch.dispatch",
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["fn_path"] == "pyantz.jobs.subproc.dispatch.dispatch"
    assert "cmd" in body["json_schema"]["properties"]
