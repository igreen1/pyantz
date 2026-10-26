"""Test looking up registered jobs by name."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

import pyantz.jobs  # noqa: F401  (registers the jobs)
from pyantz.api.backend import app
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

client = TestClient(app)

SIMPLE_COPY = "pyantz.jobs.files.simple.copy"
MOVING_COPY = "pyantz.jobs.files.moving.copy"


def _names(query: str) -> list[str]:
    return sorted(fn.PYANTZ_NAME for fn in get_registered_functions(query))  # ty: ignore[unresolved-attribute]


def test_short_name_returns_every_match() -> None:
    """`copy` is both copy jobs."""
    assert _names("copy") == [MOVING_COPY, SIMPLE_COPY]


def test_full_name_returns_one() -> None:
    """The full dotted name is exact."""
    assert _names(SIMPLE_COPY) == [SIMPLE_COPY]


def test_partial_words_do_not_match() -> None:
    """A fragment which is not split on a dot matches nothing."""
    assert _names("py") == []
    assert _names("opy") == []
    assert _names("simple.cop") == []


def test_trailing_module_path_matches() -> None:
    """A suffix on a dot boundary is fine."""
    assert _names("simple.copy") == [SIMPLE_COPY]


def test_endpoint_lists_the_candidates_for_an_ambiguous_name() -> None:
    """The api answers with a conflict naming both jobs."""
    response = client.get("/api/v1.0/jobs/schema/copy")

    assert response.status_code == HTTPStatus.CONFLICT
    detail = response.json()["detail"]
    assert SIMPLE_COPY in detail
    assert MOVING_COPY in detail


def test_endpoint_accepts_the_full_name() -> None:
    """Using the full name resolves the ambiguity."""
    response = client.get(f"/api/v1.0/jobs/schema/{MOVING_COPY}")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["fn_path"] == MOVING_COPY


def test_endpoint_unknown_fragment_is_not_found() -> None:
    """`py` no longer matches `...copy`."""
    assert client.get("/api/v1.0/jobs/schema/py").status_code == HTTPStatus.NOT_FOUND
