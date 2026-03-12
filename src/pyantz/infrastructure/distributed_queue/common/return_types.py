"""Objects shared between different types of queues."""

import uuid
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field

from pyantz.infrastructure.config.job import JobWithContext


class JobStatus(IntEnum):
    """POssible statuses of a job."""

    # job can be run! just waiting for a worker
    READY = 0
    # job is waiting for dependencies
    PENDING = 1
    # job is running on a worker right now
    RUNNING = 2
    # something went wrong; this job will never be completed
    # depending on the setup, this might cause the whole pipeline to shutdown
    ERROR = 3
    # success! The job completed
    SUCCESS = 4


class JobStatusReport(BaseModel):
    """Status of a job."""

    # identifier for the job
    job_id: str | uuid.UUID

    # actual status of the job
    status: JobStatus

    # additional information about the status
    # for example, for errors this is the error message
    status_details: str | None = None


class JobsReport(BaseModel):
    """Debug message with counts of various jobs for runtime analysis."""

    # total number of unique jobs put on the queue
    total: int = Field(ge=0)

    # num jobs which updated themselves as successful
    success: int = Field(ge=0)

    # num jobs which updated themselves as error
    error: int = Field(ge=0)

    # num jobs waiting for dependnecies before running
    pending: int = Field(ge=0)

    # num jobs that could be run RIGHT NOW
    ready: int = Field(ge=0)

    # num jobs currently being run by a worker
    running: int = Field(ge=0)


class PendingReturn(BaseModel):
    """Indicates that the queue returned nothing but may return something later."""

    # used at runtime to indicate that the return was "pending"
    # faster/easier than an isinstance check
    type_: Literal["pending"] = "pending"

    jobs_report: JobsReport


class CompleteReturn(BaseModel):
    """Indicates that the queue is empty and will not have additional jobs added."""

    # used at runtime to indicate that the return was "complete"
    # faster/easier than an isinstance check
    type_: Literal["complete"] = "complete"

    jobs_report: JobsReport


class JobReturn(BaseModel):
    """Actual job returned to be run."""

    # used at runtime to indicate that the return was returned
    # faster/easier than an isinstance check
    type_: Literal["job"] = "job"

    job: JobWithContext


class GetJobReturn(BaseModel):
    """Return value of the `get_job` function.

    This is used like a Rust enum return to return a "union" type.

    Rather than always returning a job, `get_job` can return either
    1. Job: Successfully dequeue a job
    2. Pending: either jobs are ready and awaiting dependencies
        or a job is running and it may still submit something
    3. Complete: the queue is empty and the worker should kill itself
    """

    # the actual return value
    # probably could've used rootmodel to avoid this wrapper
    # but this is easier to understand in my opinion
    payload: JobReturn | CompleteReturn | PendingReturn = Field(discriminator="type_")
