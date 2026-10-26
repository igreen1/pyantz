"""Return types used by queue implementations.

:class:`GetJobReturn` is the discriminated union returned by
:meth:`~pyantz.infrastructure.distributed_queue.common.interface.QueueInterface.get_job`.
It wraps one of three payload types:

* :class:`JobReturn` — a job is ready to run.
* :class:`PendingReturn` — nothing is ready now, but the queue is not empty.
* :class:`CompleteReturn` — the queue is empty; the worker should exit.

:class:`JobsReport` is a snapshot of job counts by status, used for
debugging and progress monitoring.

Example of :class:`GetJobReturn`:

    .. testcode::

        from pyantz.infrastructure.distributed_queue.common import (
            GetJobReturn,
        )

        report = {
            "total": 1, "success": 1, "error": 0, "pending": 0, "ready": 0,
            "running": 0,
        }
        result = GetJobReturn.model_validate(
            {"payload": {"type_": "complete", "jobs_report": report}}
        )
        print(result.payload.type_, result.payload.jobs_report.all_succeeded)

    .. testoutput::

        complete True
"""

from __future__ import annotations

import uuid
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field

from pyantz.infrastructure.config.job import JobWithContext


class JobStatus(IntEnum):
    """Possible statuses of a job.

    A job starts PENDING, becomes READY once every job it depends on succeeded,
    RUNNING when a worker takes it, and finally SUCCESS or ERROR. A job whose
    dependency fails becomes ERROR too.
    """

    READY = 0
    """Job can be run! Just waiting for a worker."""

    PENDING = 1
    """Job is waiting for dependencies."""

    RUNNING = 2
    """Job is running on a worker right now."""

    ERROR = 3
    """Something went wrong; this job will never be completed. Depending on the
    setup, this might cause the whole pipeline to shutdown."""

    SUCCESS = 4
    """Success! The job completed."""


class JobStatusReport(BaseModel):
    """Status of a job."""

    job_id: str | uuid.UUID
    """Identifier for the job."""

    status: JobStatus
    """Actual status of the job."""

    status_details: str | None = None
    """Additional information about the status; for example, for errors this is
    the error message."""


class JobsReport(BaseModel):
    """Debug message with counts of various jobs for runtime analysis."""

    total: int = Field(ge=0)
    """Total number of unique jobs put on the queue."""

    success: int = Field(ge=0)
    """Number of jobs which updated themselves as successful."""

    error: int = Field(ge=0)
    """Number of jobs which updated themselves as error."""

    pending: int = Field(ge=0)
    """Number of jobs waiting for dependencies before running."""

    ready: int = Field(ge=0)
    """Number of jobs that could be run RIGHT NOW."""

    running: int = Field(ge=0)
    """Number of jobs currently being run by a worker."""

    @property
    def all_succeeded(self) -> bool:
        """True if no job errored and none is left unfinished.

        Args:
            None.

        Returns:
            bool: True if every job finished successfully.

        Raises:
            None.

        Example:
            .. testcode::

                from pyantz.infrastructure.distributed_queue.common import JobsReport

                report = JobsReport(
                    total=3, success=2, error=0, pending=0, ready=0, running=1
                )
                print(report.all_succeeded)

            .. testoutput::

                False

        """
        return (
            self.error == 0
            and self.pending == 0
            and self.ready == 0
            and self.running == 0
        )


class PendingReturn(BaseModel):
    """Indicates that the queue returned nothing but may return something later."""

    type_: Literal["pending"] = "pending"
    """Tells the returns apart at runtime; faster/easier than an isinstance
    check."""

    jobs_report: JobsReport
    """The state of the queue."""


class CompleteReturn(BaseModel):
    """Indicates that the queue is empty and will not have additional jobs added."""

    type_: Literal["complete"] = "complete"
    """Tells the returns apart at runtime; faster/easier than an isinstance
    check."""

    jobs_report: JobsReport
    """The final state of the queue."""


class JobReturn(BaseModel):
    """Actual job returned to be run."""

    type_: Literal["job"] = "job"
    """Tells the returns apart at runtime; faster/easier than an isinstance
    check."""

    job: JobWithContext
    """The job to run."""


class GetJobReturn(BaseModel):
    """Return value of the `get_job` function.

    This is used like a Rust enum return to return a "union" type.

    Rather than always returning a job, `get_job` can return either

    1. Job: Successfully dequeue a job
    2. Pending: either jobs are ready and awaiting dependencies
       or a job is running and it may still submit something
    3. Complete: the queue is empty and the worker should kill itself
    """

    payload: JobReturn | CompleteReturn | PendingReturn = Field(discriminator="type_")
    """The actual return value, told apart by its ``type_``."""
