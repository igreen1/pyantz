"""Test the endpoints to validate, preview and run configurations."""

import time
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from pyantz.api.backend import create_app
from pyantz.api.settings import check_safe_to_bind, get_settings

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _config(**changes: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "jobs": [
            {"job_id": "a", "function": NOP, "parameters": {}},
            {"job_id": "b", "function": NOP, "parameters": {}, "depends_on": ["a"]},
        ],
        "submitter": {"type_": "local_proc", "working_directory": "unused"},
        **changes,
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Make a client of a fresh app, with runs kept in a temporary directory."""
    monkeypatch.delenv("PYANTZ_API_TOKEN", raising=False)
    monkeypatch.delenv("PYANTZ_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("PYANTZ_ALLOWED_MODULES", raising=False)
    monkeypatch.setenv("PYANTZ_RUNS_DIR", str(tmp_path / "runs"))
    return TestClient(create_app())


def test_validate_accepts_a_good_config(client: TestClient) -> None:
    """A good configuration is valid, with no errors."""
    response = client.post("/api/v1.0/config/validate", json=_config())

    assert response.json() == {"valid": True, "errors": []}


def test_validate_lists_the_problems(client: TestClient) -> None:
    """A bad configuration is not an http error; it lists what is wrong."""
    bad = _config(
        jobs=[
            {"job_id": "a", "function": NOP, "parameters": {}, "depends_on": ["nope"]}
        ]
    )

    response = client.post("/api/v1.0/config/validate", json=bad)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["valid"] is False
    assert "nope" in "".join(response.json()["errors"])


def test_compile_returns_jobs_and_edges(client: TestClient) -> None:
    """The compiled jobs come with the edges of the graph."""
    response = client.post("/api/v1.0/config/compile", json=_config())

    body = response.json()
    assert [job["job_id"] for job in body["jobs"]] == ["a", "b"]
    assert body["jobs"][1]["depends_on"] == ["a"]
    assert body["edges"] == [["a", "b"]]


def test_compile_rejects_a_bad_config(client: TestClient) -> None:
    """A configuration which doesn't compile is an unprocessable request."""
    response = client.post("/api/v1.0/config/compile", json={"jobs": 1})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_runs_are_disabled_without_allowed_modules(client: TestClient) -> None:
    """Nobody can run arbitrary code through the api by default."""
    response = client.post("/api/v1.0/runs", json=_config())

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_run_and_report_progress(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run is started in its own directory and its progress can be read."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")

    started = client.post("/api/v1.0/runs", json=_config())
    assert started.status_code == HTTPStatus.OK
    run_id = started.json()["run_id"]

    deadline = time.monotonic() + 60
    body: dict[str, Any] = {}
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1.0/runs/{run_id}").json()
        if body["state"] != "running":
            break
        time.sleep(0.2)

    assert body["state"] == "succeeded"
    assert body["report"]["success"] == body["report"]["total"] == 2  # noqa: PLR2004
    assert {job["job_id"]: job["status"] for job in body["jobs"]} == {
        "a": "success",
        "b": "success",
    }


def test_runs_only_accept_local_submitters(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Other hosts are refused."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")
    config = _config(host={"type_": "ssh", "hostname": "h", "username": "u"})

    response = client.post("/api/v1.0/runs", json=config)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("run_id", ["nope", "../../etc", "0" * 32])
def test_unknown_runs_are_not_found(client: TestClient, run_id: str) -> None:
    """Ids which are not runs, or try to leave the runs directory, are not found."""
    response = client.get(f"/api/v1.0/runs/{run_id}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_cors_header_for_configured_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured origin is allowed to call the api; others are not."""
    monkeypatch.setenv("PYANTZ_CORS_ORIGINS", "http://localhost:5173")
    client = TestClient(create_app())

    allowed = client.get(
        "/api/v1.0/jobs/get_all_jobs", headers={"Origin": "http://localhost:5173"}
    )
    other = client.get(
        "/api/v1.0/jobs/get_all_jobs", headers={"Origin": "http://evil.example"}
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in other.headers


def test_token_is_required_when_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a token set, requests without it are refused."""
    monkeypatch.setenv("PYANTZ_API_TOKEN", "secret")
    url = "/api/v1.0/jobs/get_all_jobs"

    assert client.get(url).status_code == HTTPStatus.UNAUTHORIZED
    wrong = client.get(url, headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == HTTPStatus.UNAUTHORIZED
    right = client.get(url, headers={"Authorization": "Bearer secret"})
    assert right.status_code == HTTPStatus.OK


def test_remote_bind_needs_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server won't listen on other machines' behalf without authentication."""
    monkeypatch.setenv("PYANTZ_HOST", "0.0.0.0")  # noqa: S104
    monkeypatch.delenv("PYANTZ_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="PYANTZ_API_TOKEN"):
        check_safe_to_bind(get_settings())

    monkeypatch.setenv("PYANTZ_API_TOKEN", "secret")
    check_safe_to_bind(get_settings())


def _start_run(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")
    run_id: str = client.post("/api/v1.0/runs", json=_config()).json()["run_id"]
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if client.get(f"/api/v1.0/runs/{run_id}").json()["state"] != "running":
            break
        time.sleep(0.2)
    return run_id


def test_run_log_is_the_end_of_the_output(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The log can be read, and a limit keeps the end of it."""
    run_id = _start_run(client, monkeypatch)
    (tmp_path / "runs" / run_id / "run.log").write_text("first\nsecond\nthird\n")

    whole = client.get(f"/api/v1.0/runs/{run_id}/log").json()
    tail = client.get(f"/api/v1.0/runs/{run_id}/log", params={"max_bytes": 6}).json()

    assert whole == {
        "run_id": run_id,
        "log": "first\nsecond\nthird\n",
        "truncated": False,
    }
    assert tail["log"] == "third\n"
    assert tail["truncated"] is True


@pytest.mark.parametrize("max_bytes", [0, 1_000_001])
def test_run_log_limits_the_size(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, max_bytes: int
) -> None:
    """A request can't ask for more than the limit, or for nothing."""
    run_id = _start_run(client, monkeypatch)

    response = client.get(
        f"/api/v1.0/runs/{run_id}/log", params={"max_bytes": max_bytes}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("run_id", ["nope", "../../etc", "0" * 32])
def test_run_log_of_unknown_runs_is_not_found(client: TestClient, run_id: str) -> None:
    """Ids which are not runs, or try to leave the runs directory, are not found."""
    response = client.get(f"/api/v1.0/runs/{run_id}/log")

    assert response.status_code == HTTPStatus.NOT_FOUND
