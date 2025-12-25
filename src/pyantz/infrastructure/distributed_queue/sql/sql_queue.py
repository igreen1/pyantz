"""Queue running with sql."""

import contextlib
import os
import sqlite3
import uuid
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
import sqlalchemy.exc
from sqlalchemy.orm import Session

from pyantz.infrastructure.config.job import JobWithContext
from pyantz.infrastructure.distributed_queue.common.interface import QueueInterface
from pyantz.infrastructure.distributed_queue.common.return_types import (
    CompleteReturn,
    GetJobReturn,
    JobReturn,
    JobsReport,
    JobStatus,
    PendingReturn,
)

from .orm import (
    CHUNKSIZE,
    Base,
    DependencyTable,
    JobConfigTable,
    JobQueue,
    StatusTable,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class SqliteQueue(QueueInterface):
    """Type checking interface to ensure consistent accesses."""

    __slots__ = [
        "_engine",
        "database_file",
    ]

    database_file: Path
    engine: sa.Engine

    def __init__(self, database_file: Path) -> None:
        """Set the sqlalchemy engine for connections."""
        self.database_file = database_file
        self._engine = self._create_engine(self.database_file)

        with contextlib.suppress(
            sqlite3.OperationalError,
            sqlalchemy.exc.OperationalError,
        ):
            Base.metadata.create_all(self._engine)

    def _create_engine(self, database_file: Path) -> sa.Engine:
        """Create the engine and return it."""
        return sa.create_engine(
            f"""sqlite:///{os.fspath(database_file)}""",
        )

    def get_job(self) -> GetJobReturn:
        """Return a job from the queue.

        Returns:
            GetJobReturn: either
                - A job to run
                - Pending to indicate that nothing is ready but to keep waiting
                - Complete to tell the worker to kill itself

        """
        self._update_job_statuses()
        with Session(self._engine) as sesh:
            # get READY jobs
            ready_jobs_query = sa.select(StatusTable.job_id).where(
                StatusTable.job_status == JobStatus.READY,
            )

            # get the first job and delete it from the queue in one statement
            # but skip jobs which aren't ready for running
            stmt = (
                sa.delete(JobQueue)
                .where(
                    JobQueue.q_index.in_(
                        sa.select(JobQueue.q_index)
                        .where(
                            # only look at jobs which are READY
                            JobQueue.job_id.in_(ready_jobs_query),
                        )
                        .order_by(
                            # queues are obviously ordered!
                            JobQueue.q_index,
                        )
                        # only grab the top element
                        .limit(1),
                    ),
                )
                # delete and return in one statement for acid/atomic operations
                .returning(JobQueue)
            )
            result = sesh.execute(stmt).first()
            sesh.flush()
            job_id: str | None = result[0].job_id if result is not None else None

            if job_id is None:
                return self._check_empty_type(sesh)
            return GetJobReturn(
                payload=self._get_job_config(sesh, job_id),
            )

    @staticmethod
    def _get_job_config(sesh: Session, job_id: str) -> JobReturn:
        """Get the job config by piecing the various chunks together."""
        query = (
            sa.select(
                JobConfigTable.job_config_content,
            )
            .where(
                JobConfigTable.job_id == job_id,
            )
            .order_by(
                JobConfigTable.job_subindex,
            )
        )
        result = sesh.execute(query).fetchall()
        content_row = [row[0] for row in result]
        if len(content_row) == 0:
            msg = f"Cannot get chunks for config {job_id}"
            raise RuntimeError(msg)
        contents = "".join(content_row)
        sesh.commit()

        job_config = JobWithContext.model_validate_json(contents)
        return JobReturn(job=job_config)

    @staticmethod
    def _check_empty_type(sesh: Session) -> GetJobReturn:
        """Check why the queue is empty (pending? or dead/complete?).

        Args:
            sesh (Session): current sqlalchemy session

        """
        jobs_report = SqliteQueue._generate_jobs_report(sesh)

        if jobs_report.running > 0:
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        if jobs_report.pending > 0:
            # hmm, unlikley to be able to recover
            # but the worker is in charge of crashing / killing itself
            # by analyzing the jobs report
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        if jobs_report.ready > 0:
            # we shouldn't even be in this function
            # worker is supposed to crash based on this return
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        return GetJobReturn(payload=CompleteReturn(jobs_report=jobs_report))
        # all jobs are ERROR or SUCCESS

    def get_jobs_report(self) -> JobsReport:
        """Get the jobs report.

        Useful for debugging or determining the size of the queue.

        Returns (JobsReport): report of the jobs and their states.
        """
        with Session(self._engine) as sesh:
            return self._generate_jobs_report(sesh)

    @staticmethod
    def _generate_jobs_report(sesh: Session) -> JobsReport:
        """Create a report of the current jobs on the queue."""
        # calculate total separately to check for inconsistencies
        # if total is not the sum of our states, then we have something
        # deeply wrong in our queue! useful for debugging
        total_job_count = sa.select(
            sa.func.count(
                sa.func.distinct(
                    JobConfigTable.job_id,
                ),
            ),
        )
        result = sesh.execute(total_job_count).first()
        total = result[0] if result is not None else 0

        # state rollups
        status_queries = {
            status: sa.select(
                sa.func.count(
                    sa.func.distinct(StatusTable.job_id),
                ),
            ).where(StatusTable.job_status == status)
            for status in (
                JobStatus.READY,
                JobStatus.RUNNING,
                JobStatus.ERROR,
                JobStatus.PENDING,
                JobStatus.SUCCESS,
            )
        }
        status_results = {
            status: sesh.execute(query).first()
            for status, query in status_queries.items()
        }
        # fix "none" returns
        status_counts: dict[JobStatus, int] = {
            status: result[0] if result is not None else 0
            for status, result in status_results.items()
        }

        return JobsReport(
            total=total,
            success=status_counts[JobStatus.SUCCESS],
            error=status_counts[JobStatus.ERROR],
            pending=status_counts[JobStatus.PENDING],
            ready=status_counts[JobStatus.READY],
            running=status_counts[JobStatus.RUNNING],
        )

    def _update_job_statuses(self) -> None:
        """Update statuses of all the josb in the queue.

        Propagates errors and successes down the dependency chain.

        Specifically, if a job status is ERROR, set its immediate dependents to ERROR
            with each call, this will propagate down the dependency chain
        And, if a job status is SUCCESS, immediate dependents from "PENDING" to "READY"
        """
        with Session(self._engine) as sesh:
            # update jobs to failure if depend on failure
            failed_jobs: sa.Select[Any] = sa.Select(StatusTable.job_id).where(  # pyright: ignore[reportUnknownVariableType]
                StatusTable.job_status == JobStatus.ERROR,
            )

            jobs_that_depend_on_failed_job = sa.select(DependencyTable.job_id).where(
                DependencyTable.depends_on.in_(failed_jobs),
            )

            delete_jobs_from_queue_query = sa.delete(JobQueue).where(
                JobQueue.job_id.in_(jobs_that_depend_on_failed_job),
            )

            job_statuses_that_depend_on_failed_job = (
                sa.update(StatusTable)
                .where(StatusTable.job_id.in_(jobs_that_depend_on_failed_job))
                .values(job_status=JobStatus.ERROR)
            )

            sesh.execute(delete_jobs_from_queue_query)
            sesh.execute(job_statuses_that_depend_on_failed_job)

            # update jobs to ready if depends on jobs with success
            success_jobs: sa.Select[Any] = sa.Select(StatusTable.job_id).where(  # pyright: ignore[reportUnknownVariableType]
                StatusTable.job_status == JobStatus.SUCCESS,
            )
            jobs_depending_on_success = sa.select(DependencyTable.job_id).where(
                DependencyTable.depends_on.in_(success_jobs),
            )

            update_pending_jobs_depending_on_success = (
                sa.update(StatusTable)
                .where(StatusTable.job_id.in_(jobs_depending_on_success))
                .where(StatusTable.job_status == JobStatus.PENDING)
                .values(job_status=JobStatus.READY)
            )
            sesh.execute(update_pending_jobs_depending_on_success)

            # update jobs with no dependency
            jobs_with_deps = sa.select(sa.func.distinct(DependencyTable.job_id))
            update_query = (
                sa.update(StatusTable)
                .where(StatusTable.job_status == JobStatus.PENDING)
                .where(StatusTable.job_id.not_in(jobs_with_deps))
                .values(job_status=JobStatus.READY)
            )
            sesh.execute(update_query)
            sesh.commit()

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
        # not required but polite
        self._update_job_statuses()

        with Session(self._engine) as sesh:
            update_query = (
                sa.update(
                    StatusTable,
                )
                .where(StatusTable.job_id == job_id)
                .values(job_status=status)
            )
            sesh.execute(update_query)
            sesh.flush()
            sesh.commit()

        # not required but polite
        self._update_job_statuses()

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
        # not required but polite to call whenever accessing
        self._update_job_statuses()

        with Session(self._engine) as sesh:
            # first, chunk up the job
            jobs_json = job_config.model_dump_json()
            job_definition_chunks: Generator[str] = (
                "".join(chunk_as_tuple)
                for chunk_as_tuple in batched(jobs_json, CHUNKSIZE)
            )

            # then, add it to the job config defintion table
            job_configs = [
                JobConfigTable(
                    job_id=job_config.job_id,
                    job_subindex=idx,
                    job_config_content=content,
                )
                for idx, content in enumerate(job_definition_chunks)
            ]
            sesh.add_all(job_configs)
            sesh.flush()

            # then add it to the dependency table
            # make sure to inherit parent dependencies!
            if job_config.depends_on:
                dependencies = [
                    DependencyTable(job_id=job_config.job_id, depends_on=dep)
                    for dep in job_config.depends_on
                ]
                sesh.add_all(dependencies)
            if parent_job_id is not None:
                jobs_depending_on_parent = sa.select(
                    DependencyTable.job_id,
                    sa.literal_column(f"{job_config.job_id}").alias("depends_on"),
                ).where(DependencyTable.depends_on == parent_job_id)
                query = sa.insert(DependencyTable).from_select(
                    ["job_id", "depends_on"],
                    jobs_depending_on_parent,
                )
                sesh.execute(query)
                sesh.flush()

            # add its status
            status = StatusTable(
                job_id=job_config.job_id,
                job_status=JobStatus.PENDING,
            )
            sesh.add(status)

            # then add it to the overall queue
            queue_item = JobQueue(job_id=job_config.job_id)
            sesh.add(queue_item)

            sesh.commit()

        # not required but polite
        self._update_job_statuses()
        return True

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
        with Session(self._engine) as sesh:
            delete_query = sa.delete(JobConfigTable).where(
                JobConfigTable.job_id == job_config.job_id,
            )

            jobs_json = job_config.model_dump_json()
            job_definition_chunks: Generator[str] = (
                "".join(chunk_as_tuple)
                for chunk_as_tuple in batched(jobs_json, CHUNKSIZE)
            )

            # then, add it to the job config defintion table
            job_configs = [
                JobConfigTable(
                    job_id=job_config.job_id,
                    job_subindex=idx,
                    job_config_content=content,
                )
                for idx, content in enumerate(job_definition_chunks)
            ]
            sesh.execute(delete_query)
            sesh.add_all(job_configs)
            sesh.flush()
            sesh.commit()
