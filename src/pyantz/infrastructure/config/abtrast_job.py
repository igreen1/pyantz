"""Code shared by virtual and `real` jobs."""

import uuid
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema


def str_uuid4() -> str:
    """Return uuid4 as a string."""
    return str(uuid.uuid4())


class AbstractJobConfig(BaseModel):
    """Shared between virtual and real jobs."""

    # unique identifier for this job
    # auto generated if the user doesn't specify
    job_id: str = Field(default_factory=str_uuid4)

    model_config = ConfigDict(frozen=True)

    # the jobs upon which this one depends before it can be run
    depends_on: Annotated[
        set[str] | None,
        WithJsonSchema(
            {
                "type": "array",
                "items": {"type": "string"},
            },
        ),
    ] = None

    # parameters to pass to the job while it's running
    parameters: Mapping[str, Any]

    # strict means no variables allowed, must use typed functions
    strict: bool = False
