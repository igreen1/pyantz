"""Configuration for the overall pipeline to be run."""

from pydantic import BaseModel

from .job import JobConfig


class PipelineConfig(BaseModel):
    """Configuration of the pipeline of jobs to be run."""

    jobs: JobConfig

