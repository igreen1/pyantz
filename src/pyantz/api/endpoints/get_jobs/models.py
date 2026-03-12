"""Data models for the `get_jobs` endpoint."""

from pydantic import BaseModel, model_validator


class GetJobReponse(BaseModel):
    """Response returned by the get_job request."""

    # functions that can be used in pyantz.
    pyantz_jobs: list[str]

    # description of the job
    pyantz_job_descriptions: list[str]

    @model_validator(mode="after")
    def check_lengths(self) -> GetJobReponse:
        """Ensure that the lengths of the two lists are the same."""
        if len(self.pyantz_jobs) != len(self.pyantz_job_descriptions):
            msg = "The lengths of pyantz_jobs and pyantz_job_descriptions must be same."
            raise ValueError(msg)
        return self
