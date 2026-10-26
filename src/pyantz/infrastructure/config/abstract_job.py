"""Shared base class for all job configuration types.

:class:`AbstractJobConfig` is inherited by both
:class:`~pyantz.infrastructure.config.job.JobConfig` (concrete jobs) and
:class:`~pyantz.infrastructure.config.virtual.VirtualJobConfig` (compile-time
jobs).  It provides the common ``job_id``, ``depends_on``, ``parameters``,
and ``strict`` fields.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema


def str_uuid4() -> str:
    """Return uuid4 as a string.

    Used as the default factory of :attr:`AbstractJobConfig.job_id`.

    Args:
        None.

    Returns:
        str: a new random uuid, such as ``"6f1c...-..."``.

    Raises:
        None.

    Example:
        .. testcode::

            import uuid

            from pyantz.infrastructure.config.abstract_job import str_uuid4

            print(uuid.UUID(str_uuid4()).version)

        .. testoutput::

            4

    """
    return str(uuid.uuid4())


class AbstractJobConfig(BaseModel):
    """Shared between virtual and real jobs."""

    job_id: str = Field(default_factory=str_uuid4)
    """Unique identifier for this job; generated if the user doesn't give one."""

    model_config = ConfigDict(frozen=True)

    depends_on: Annotated[
        set[str] | None,
        WithJsonSchema(
            {
                "type": "array",
                "items": {"type": "string"},
            },
        ),
    ] = None
    """Ids of the jobs which must finish before this one can run."""

    parameters: Mapping[str, Any]
    """Parameters to pass to the job while it's running; strings may hold
    ``%{variable}`` references."""

    strict: bool = False
    """If true, the parameters are validated when the configuration is loaded, so
    they can't depend on variables set while the pipeline runs, and the function
    must be registered with
    :func:`~pyantz.infrastructure.config.add_parameters`."""
