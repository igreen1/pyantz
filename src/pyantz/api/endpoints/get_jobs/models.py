"""Data models for the `get_jobs` endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class JobInfo(BaseModel):
    """A job which can be used in pyantz."""

    # import path of the function, which is how configs refer to the job
    name: str
    """Import path of the function, which is how configs refer to the job."""

    # first paragraph of the job's docstring
    description: str
    """First paragraph of the job's docstring."""


class GetJobResponse(BaseModel):
    """Response returned by the get_job request."""

    jobs: list[JobInfo]
    """Every registered job."""
