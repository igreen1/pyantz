"""Required function signatures for all our queues.

While the queues are function orientated, we want to ensure
an exact consistent interface, so a protocol is used
just to wrap the public interfaces.

Queues are expected to be stateless. The "state" should be persisted
in the storage of the queue itself, but the queue instance is merely
a conveience wrapper to access whatever persistent layer is used.

Classes may, however, store accessor details in their state.
SQLite queues, for example, store a sqlalchemy engine to access
the database file. But, after initialization this cannot be
updated or changed without a new class instance.
"""

import uuid
from abc import abstractmethod
from typing import Protocol

from pyantz.infrastructure.config.job import JobWithContext

from .return_types import GetJobReturn, JobsReport, JobStatus


class QueueInterface(Protocol):
    """Type checking interface to ensure consistent accesses."""

    @abstractmethod
    def get_job(self) -> GetJobReturn:
        """Return a job from the queue.

        Returns:
            GetJobReturn: either
                - A job to run
                - Pending to indicate that nothing is ready but to keep waiting
                - Complete to tell the worker to kill itself

        """

    @abstractmethod
    def update_job_status(
        self,
        job_id: str | uuid.UUID,
        status: JobStatus,
    ) -> None:
        """Update the status of the job.

        Args:
            job_id (str | uuid.UUID): job to be updated
            status (JobStatus): new state after this update
            details (str | None): additional information about status
                eg., may be the error message for debugging.

        """

    @abstractmethod
    def add_job(
        self,
        job_config: JobWithContext,
        parent_job_id: str | uuid.UUID | None,
    ) -> bool:
        """Add the provided job to the queue.

        Args:
            job_config (JobWithContext): job to enqueue
            parent_job_id (str | uuid.UUID | None): jobs added inherit their parent
                dependency "responsbilities". So a job submitting new jobs should pass
                its own id to the function.
                For example if B depends on A and A adds C then B will depend on C.
                If, however, the user DOESN'T want that (B should run parallel to C),
                then they can pass "None" as the parent_job_id.


        Returns:
            bool: True if successfully added; False if unable to add

        """

    @abstractmethod
    def change_config_in_place(self, job_config: JobWithContext) -> None:
        """Change the config of a job.

        In practice, this is used to restart jobs during error recovery.
        A worker will update the `num_attempted_runs` and change the job.
        Then it will set its status to PENDING.

        The queue will then set PENDING to READY on its next check and return
        the job to be re-run.

        Args:
            job_config (JobWithContext): configuration to run

        """

    @abstractmethod
    def get_jobs_report(self) -> JobsReport:
        """Get the jobs report.

        Useful for debugging or determining the size of the queue.

        Returns (JobsReport): report of the jobs and their states.
        """
