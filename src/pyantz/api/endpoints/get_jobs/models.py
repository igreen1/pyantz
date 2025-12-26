"""Data models for the `get_jobs` endpoint."""

from pydantic import BaseModel


class GetJobReponse(BaseModel):
    """Response returned by the get_job request."""

    # functions that can be used in pyantz.
    pyantz_jobs: list[str]
