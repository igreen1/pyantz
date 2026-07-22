"""Configuration for pipelines — ordered sequences of jobs.

A ``JobPipeline`` is the type alias used wherever a list of jobs can appear
in parameters.  At parse time Pydantic calls :func:`_make_pipeline` to
convert a raw list of dicts into typed job config objects.
"""

from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BeforeValidator

from .job import JobConfig, make_job
from .virtual import VirtualJobConfig


def _make_pipeline(
    pipeline: Any,  # noqa: ANN401
) -> list[JobConfig | VirtualJobConfig]:
    """Convert a raw iterable into a validated list of job configs.

    Called automatically by Pydantic's BeforeValidator when a ``JobPipeline``
    field is populated.  Each element is passed to :func:`~pyantz.infrastructure.config.job.make_job`,
    which selects :class:`~pyantz.infrastructure.config.job.JobConfig` vs
    :class:`~pyantz.infrastructure.config.virtual.VirtualJobConfig` based on
    the ``virtual`` flag or the type of the ``function`` value.

    Args:
        pipeline: Any iterable of raw job-config dicts or pre-validated job
            config objects.

    Returns:
        A list of validated job config objects ready for compilation or
        execution.

    Raises:
        TypeError: If ``pipeline`` is not iterable.
    """
    if not isinstance(pipeline, Iterable):
        raise TypeError

    return [make_job(config) for config in pipeline]  # pyright: ignore[reportUnknownVariableType]


type JobPipeline = Annotated[
    list[JobConfig | VirtualJobConfig], BeforeValidator(_make_pipeline)
]
