"""Configuration for pipelines (ordered sets of jobs)."""

from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BeforeValidator

from .job import JobConfig, make_job


def _make_pipeline(
    pipeline: Any,
) -> list[JobConfig]:
    """Make pipeline from anything."""
    if not isinstance(pipeline, Iterable):
        raise TypeError

    return [make_job(config) for config in pipeline] # pyright: ignore[reportUnknownVariableType]


type JobPipeline = Annotated[list[JobConfig], BeforeValidator(_make_pipeline)]
