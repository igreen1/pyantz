"""Required function signatures for all our queues.

While the queues are function orientated, we want to ensure
an exact consistent interface, so a protocol is used
just to wrap the public interfaces.

Queues are expected to be stateless. The "state" should be persisted
in the storage of the queue itself, but the queue instance is merely
a convenience wrapper to access whatever persistent layer is used.

Classes may, however, store accessor details in their state.
SQLite queues, for example, store a sqlalchemy engine to access
the database file. But, after initialization this cannot be
updated or changed without a new class instance.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from pyantz.infrastructure.config.job import JobWithContext

    from .return_types import GetJobReturn, JobsReport, JobStatus, JobStatusReport


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
        details: str | None = None,
    ) -> None:
        """Update the status of the job.

        Args:
            job_id (str | uuid.UUID): job to be updated
            status (JobStatus): new state after this update
            details (str | None): additional information about status
                eg., may be the error message for debugging.

        """

    @abstractmethod
    def get_job_status(self, job_id: str | uuid.UUID) -> JobStatusReport:
        """Get the current status of a job, and the details given with it.

        Args:
            job_id (str | uuid.UUID): job to look up

        Raises:
            KeyError: if there is no such job

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
                dependency "responsibilities". So a job submitting new jobs should pass
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
        the job to be re-run (the job is put back in the queue if a worker had
        already taken it out).

        Args:
            job_config (JobWithContext): configuration to run

        """

    @abstractmethod
    def set_job_worker(self, job_id: str | uuid.UUID, worker_id: int) -> None:
        """Record which worker is running the job."""

    @abstractmethod
    def fail_jobs_of_worker(self, worker_id: int) -> list[str]:
        """Mark the RUNNING jobs of a worker which died as ERROR.

        Returns:
            list[str]: ids of the jobs which were failed

        """

    @abstractmethod
    def fail_deadlocked_jobs(self) -> list[str]:
        """Mark PENDING jobs as ERROR if nothing is READY or RUNNING.

        In that state nothing can ever change the status of a pending job (for
        example, it depends on a job id that was never added), so the pipeline
        would wait forever.

        Returns:
            list[str]: ids of the jobs which were failed

        """

    @abstractmethod
    def get_failed_jobs(self) -> list[JobStatusReport]:
        """Get the status (with the error details) of every job which errored.

        Returns (list[JobStatusReport]): the failed jobs, sorted by job id.
        """

    @abstractmethod
    def get_jobs_report(self) -> JobsReport:
        """Get the jobs report.

        Useful for debugging or determining the size of the queue.

        Returns (JobsReport): report of the jobs and their states.
        """
