"""Test the endpoint returning the parameter schema of a job."""

from __future__ import annotations

import subprocess
import sys
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

import pyantz.jobs  # noqa: F401  # registers the jobs
from pyantz.api.backend import app
from pyantz.api.endpoints.get_parameters import endpoints
from pyantz.infrastructure.config.fn_utils import serialize_function
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

if TYPE_CHECKING:
    from collections.abc import Callable

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


# The jobs of pyantz only: other tests register jobs of their own in this process,
# which differ between the workers of pytest-xdist, which need to collect the same
# tests. Sorted, since the order of registration is not always the same either.
PYANTZ_JOBS = sorted(
    (
        fn
        for fn in get_registered_functions()
        if fn.__module__.startswith("pyantz.jobs.")
    ),
    key=serialize_function,
)


@pytest.mark.parametrize("fn", PYANTZ_JOBS, ids=serialize_function)
def test_every_registered_job_has_a_schema(fn: Callable[..., Any]) -> None:
    """The frontend fetches the schema of every job, so none may be an error."""
    response = client.get(f"/api/v1.0/jobs/schema/{serialize_function(fn)}")

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()["json_schema"], dict)


def test_schema_dump_matches_the_fixture_of_the_frontend_tests() -> None:
    """The frontend tests read a dump of the schemas; regenerate it if this fails.

    Run ``uv run python -m pyantz.api.dump_schemas
    frontend/pyantz/src/__fixtures__/job-schemas.json``.
    """
    fixture = (
        Path(__file__).parents[2] / "frontend/pyantz/src/__fixtures__/job-schemas.json"
    )
    # in a new interpreter: the jobs which other tests register are not in it
    dumped = subprocess.run(
        [sys.executable, "-m", "pyantz.api.dump_schemas"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert fixture.read_text(encoding="utf-8") == dumped
