"""Configuration for pipelines (ordered sets of jobs)."""

from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BeforeValidator

from .job import JobConfig, make_job
from .virtual import VirtualJobConfig


def _make_pipeline(
    pipeline: Any,  # noqa: ANN401
) -> list[JobConfig | VirtualJobConfig]:
    """Make pipeline from anything."""
    if not isinstance(pipeline, Iterable):
        raise TypeError

    return [make_job(config) for config in pipeline]  # pyright: ignore[reportUnknownVariableType]


type JobPipeline = Annotated[
    list[JobConfig | VirtualJobConfig], BeforeValidator(_make_pipeline)
]
