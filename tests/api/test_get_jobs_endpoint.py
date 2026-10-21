"""Test the endpoint listing the available jobs."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from pyantz.api.backend import app
from pyantz.api.endpoints.get_jobs import endpoint

client = TestClient(app)


def test_jobs_have_a_name_and_description() -> None:
    """Each job is one object, and the descriptions are not mangled."""
    response = client.get("/api/v1.0/jobs/get_all_jobs")

    assert response.status_code == HTTPStatus.OK
    jobs = {job["name"]: job["description"] for job in response.json()["jobs"]}
    assert "pyantz.jobs.files.simple.mkdir" in jobs
    assert jobs["pyantz.jobs.files.simple.mkdir"].startswith("Create the directory")
    assert all(jobs.values())


def test_description_is_the_first_paragraph() -> None:
    """A docstring is cut after its first paragraph, with dots kept as written."""

    def job() -> None:
        """...and so it begins.

        More detail which is not wanted.
        """

    assert endpoint.describe_job(job) == "...and so it begins."


def test_missing_docstring_has_a_placeholder() -> None:
    """A job without a docstring still gets a description."""

    def job() -> None:
        return None

    assert endpoint.describe_job(job) == endpoint.NO_DESCRIPTION
