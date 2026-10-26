"""Queue running with sql.

:class:`SqliteQueue` keeps the queue in a SQLite file (see
:mod:`~pyantz.infrastructure.distributed_queue.sql.orm` for its tables), so
several worker processes can share it.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from itertools import batched
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.event
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
    JobStatusReport,
    PendingReturn,
)

from .orm import CHUNKSIZE, Base, DependencyTable, JobConfigTable, JobQueue, StatusTable

if TYPE_CHECKING:
    import uuid
    from collections.abc import Generator
    from pathlib import Path
    from typing import Self


BUSY_TIMEOUT_SECONDS = 30
"""How long a connection waits for another process to release the database
lock."""


class SqliteQueue(QueueInterface):
    """Queue of jobs stored in a SQLite database file.

    Example:
        .. testsetup:: sql-queue

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: sql-queue

            from pathlib import Path

            from pyantz.infrastructure.config import JobWithContext
            from pyantz.infrastructure.distributed_queue.common import JobStatus
            from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

            queue = SqliteQueue(Path("example.db"))
            job = JobWithContext(
                job_id="a", function="pyantz.jobs.testing.nop.do_nothing", parameters={}
            )
            queue.add_job(job, None)

            result = queue.get_job()
            print(result.payload.type_, result.payload.job.job_id)
            queue.update_job_status("a", JobStatus.SUCCESS)
            print(queue.get_job().payload.type_)

        .. testoutput:: sql-queue

            job a
            complete

        .. testcleanup:: sql-queue

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """

    __slots__ = [
        "_engine",
        "database_file",
    ]

    database_file: Path
    """The SQLite file holding the queue."""

    _engine: sa.Engine
    """Engine connecting to :attr:`database_file`."""

    def __init__(self, database_file: Path) -> None:
        """Set the sqlalchemy engine for connections.

        The queue's tables are created if they don't exist yet.

        Args:
            database_file: the SQLite file holding the queue; created if missing.

        Returns:
            None.

        Raises:
            sqlalchemy.exc.OperationalError: if the tables can't be created, e.g.,
                the directory isn't writable.

        """
        self.database_file = database_file
        self._engine = self._create_engine(self.database_file)

        try:
            Base.metadata.create_all(self._engine)
        except (sqlite3.OperationalError, sqlalchemy.exc.OperationalError) as exc:
            # several processes may create the tables at the same time, and that is
            # fine. Anything else (unwritable directory, full disk, ...) is real
            if "already exists" not in str(exc):
                raise

    def _create_engine(self, database_file: Path) -> sa.Engine:
        """Create the engine and return it.

        Connections use write-ahead logging and wait for locks rather than failing
        immediately, so many worker processes can share one queue file.
        Note that WAL needs a local filesystem (not NFS) for the queue file.

        Args:
            database_file: the SQLite file holding the queue.

        Returns:
            sa.Engine: the engine, which sets up each new connection.

        Raises:
            None.

        """
        engine = sa.create_engine(
            f"""sqlite:///{os.fspath(database_file)}""",
            connect_args={"timeout": BUSY_TIMEOUT_SECONDS},
        )

        @sqlalchemy.event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_connection: sqlite3.Connection, _record: object) -> None:
            """Set up a new connection for sharing the file between processes.

            Args:
                dbapi_connection: the new SQLite connection.
                _record: sqlalchemy's record of the connection (unused).

            Returns:
                None.

            Raises:
                sqlite3.OperationalError: if a pragma can't be set.

            """
            cursor = dbapi_connection.cursor()
            cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_SECONDS * 1000}")
            # the mode is kept in the file: only switch a new file. Switching
            # takes a lock without waiting for it, so it fails with "database is
            # locked" while another process uses the file
            (mode,) = cursor.execute("PRAGMA journal_mode").fetchone()
            if mode != "wal":
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        return engine

    def close(self) -> None:
        """Close the queue's pooled connections to :attr:`database_file`.

        The queue can still be used: it reconnects when needed. Until closed, the
        file stays open, which on Windows means it can't be deleted or replaced.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.

        Example:
            .. testsetup:: sql-queue-close

                import os, shutil, tempfile
                start_dir = os.getcwd()
                os.chdir(tempfile.mkdtemp())

            .. testcode:: sql-queue-close

                from pathlib import Path

                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                with SqliteQueue(Path("close.db")) as queue:
                    print(queue.get_jobs_report().total)
                Path("close.db").unlink()

            .. testoutput:: sql-queue-close

                0

            .. testcleanup:: sql-queue-close

                tmp = os.getcwd()
                os.chdir(start_dir)
                shutil.rmtree(tmp)

        """
        self._engine.dispose()

    def __enter__(self) -> Self:
        """Use the queue in a ``with`` block, which closes it at the end.

        Args:
            None.

        Returns:
            Self: this queue.

        Raises:
            None.

        """
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close the queue at the end of the ``with`` block.

        Args:
            *_exc_info: the exception raised in the block, if any (unused).

        Returns:
            None.

        Raises:
            None.

        """
        self.close()

    def get_job(self) -> GetJobReturn:
        """Return a job from the queue.

        The job is taken out of the queue and marked RUNNING. A job whose config
        can't be loaded is marked ERROR and skipped.

        Args:
            None.

        Returns:
            GetJobReturn: either
                - A job to run
                - Pending to indicate that nothing is ready but to keep waiting
                - Complete to tell the worker to kill itself

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("get_job.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                first = JobWithContext(job_id="first", function=nop, parameters={})
                second = JobWithContext(
                    job_id="second", depends_on={"first"}, function=nop, parameters={}
                )
                queue.add_job(first, None)
                queue.add_job(second, None)
                print(queue.get_job().payload.job.job_id)
                print(queue.get_job().payload.type_)  # second waits for first

            .. testoutput:: sql-queue

                first
                pending

        """
        self._update_job_statuses()
        while True:
            result = self._try_dequeue()
            # None means a job was dequeued but could not be loaded;
            # it has been failed, so try again with the next job
            if result is not None:
                return result

    def _try_dequeue(self) -> GetJobReturn | None:
        """Dequeue the next READY job and mark it RUNNING in one transaction.

        Args:
            None.

        Returns:
            GetJobReturn | None: the result of the dequeue, or None if the job
                dequeued had a config which could not be loaded. That job is
                marked ERROR rather than being lost.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        """
        logger = logging.getLogger(__name__)
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
            job_id: str | None = result[0].job_id if result is not None else None

            if job_id is None:
                return self._check_empty_type(sesh)

            # the job is out of the queue, so it must not stay READY: a crash
            # before the worker reports back would otherwise lose it silently
            set_status = sa.update(StatusTable).where(StatusTable.job_id == job_id)
            sesh.execute(set_status.values(job_status=JobStatus.RUNNING))
            try:
                payload = self._get_job_config(sesh, job_id)
            except Exception:
                logger.exception("Unable to load config of job %s", job_id)
                sesh.execute(set_status.values(job_status=JobStatus.ERROR))
                sesh.commit()
                return None
            sesh.commit()
            return GetJobReturn(payload=payload)

    @staticmethod
    def _get_job_config(sesh: Session, job_id: str) -> JobReturn:
        """Get the job config by piecing the various chunks together.

        Args:
            sesh: the current sqlalchemy session.
            job_id: the job to load.

        Returns:
            JobReturn: the job.

        Raises:
            RuntimeError: if the job has no stored config.
            pydantic.ValidationError: if the stored config isn't a valid job.

        """
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

        job_config = JobWithContext.model_validate_json(contents)
        return JobReturn(job=job_config)

    @staticmethod
    def _check_empty_type(sesh: Session) -> GetJobReturn:
        """Check why the queue is empty (pending? or dead/complete?).

        Args:
            sesh (Session): current sqlalchemy session

        Returns:
            GetJobReturn: pending if jobs are running, pending or ready; otherwise
            complete (every job is ERROR or SUCCESS).

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        """
        jobs_report = SqliteQueue._generate_jobs_report(sesh)

        if jobs_report.running > 0:
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        if jobs_report.pending > 0:
            # hmm, unlikely to be able to recover
            # but the worker is in charge of crashing / killing itself
            # by analyzing the jobs report
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        if jobs_report.ready > 0:
            # we shouldn't even be in this function
            # worker is supposed to crash based on this return
            return GetJobReturn(payload=PendingReturn(jobs_report=jobs_report))
        return GetJobReturn(payload=CompleteReturn(jobs_report=jobs_report))
        # all jobs are ERROR or SUCCESS

    def get_job_ids_with_status(self, status: JobStatus) -> list[str]:
        """Get the ids of the jobs which currently have the status, sorted.

        Args:
            status: the status to look for.

        Returns:
            list[str]: the ids of the jobs with the status, sorted.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.common import JobStatus
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("with_status.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                for job_id in ("b", "a"):
                    queue.add_job(
                        JobWithContext(job_id=job_id, function=nop, parameters={}),
                        None,
                    )
                print(queue.get_job_ids_with_status(JobStatus.READY))

            .. testoutput:: sql-queue

                ['a', 'b']

        """
        with Session(self._engine) as sesh:
            rows = sesh.execute(
                sa.select(StatusTable.job_id)
                .where(StatusTable.job_status == status)
                .order_by(StatusTable.job_id),
            )
            return [row[0] for row in rows]

    def get_failed_jobs(self) -> list[JobStatusReport]:
        """Get the status (with the error details) of every job which errored.

        Args:
            None.

        Returns:
            list[JobStatusReport]: the failed jobs, sorted by job id.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.common import JobStatus
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("failed.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                job_a = JobWithContext(job_id="a", function=nop, parameters={})
                queue.add_job(job_a, None)
                queue.add_job(
                    JobWithContext(
                        job_id="b", depends_on={"a"}, function=nop, parameters={}
                    ),
                    None,
                )
                queue.update_job_status("a", JobStatus.ERROR, "it broke")
                for report in queue.get_failed_jobs():
                    print(report.job_id, report.status_details)

            .. testoutput:: sql-queue

                a it broke
                b A job this job depends on failed

        """
        with Session(self._engine) as sesh:
            rows = sesh.execute(
                sa.select(StatusTable.job_id, StatusTable.details)
                .where(StatusTable.job_status == JobStatus.ERROR)
                .order_by(StatusTable.job_id),
            ).all()
        return [
            JobStatusReport(
                job_id=job_id, status=JobStatus.ERROR, status_details=details
            )
            for job_id, details in rows
        ]

    def set_job_worker(self, job_id: str | uuid.UUID, worker_id: int) -> None:
        """Record which worker is running the job.

        Args:
            job_id: the job being run.
            worker_id: the worker (its process id) running it.

        Returns:
            None.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        """
        with Session(self._engine) as sesh:
            sesh.execute(
                sa.update(StatusTable)
                .where(StatusTable.job_id == str(job_id))
                .values(worker_id=worker_id),
            )
            sesh.commit()

    def fail_jobs_of_worker(self, worker_id: int) -> list[str]:
        """Mark the RUNNING jobs of a worker which died as ERROR.

        The jobs depending on them fail too.

        Args:
            worker_id: the worker (its process id) which died.

        Returns:
            list[str]: ids of the jobs which were failed

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("worker.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                job_a = JobWithContext(job_id="a", function=nop, parameters={})
                queue.add_job(job_a, None)
                queue.get_job()  # a worker takes the job...
                queue.set_job_worker("a", 1234)
                print(queue.fail_jobs_of_worker(1234))  # ...and dies

            .. testoutput:: sql-queue

                ['a']

        """
        with Session(self._engine) as sesh:
            rows = sesh.execute(
                sa.update(StatusTable)
                .where(StatusTable.worker_id == worker_id)
                .where(StatusTable.job_status == JobStatus.RUNNING)
                .values(job_status=JobStatus.ERROR)
                .returning(StatusTable.job_id),
            )
            failed = [row[0] for row in rows]
            sesh.commit()
        self._update_job_statuses()  # their dependents fail too
        return failed

    def fail_deadlocked_jobs(self) -> list[str]:
        """Mark PENDING jobs as ERROR if nothing is READY or RUNNING.

        Callers should confirm the state persists across a few polls: a job that
        just finished may not have had its dependents promoted yet.

        Args:
            None.

        Returns:
            list[str]: ids of the jobs which were failed

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("deadlock.db"))
                stuck = JobWithContext(
                    job_id="stuck",
                    depends_on={"never_added"},
                    function="pyantz.jobs.testing.nop.do_nothing",
                    parameters={},
                )
                queue.add_job(stuck, None)
                print(queue.fail_deadlocked_jobs())

            .. testoutput:: sql-queue

                ['stuck']

        """
        self._update_job_statuses()
        with Session(self._engine) as sesh:
            active_job_exists = (
                sa.select(StatusTable.job_id)
                .where(
                    StatusTable.job_status.in_((JobStatus.READY, JobStatus.RUNNING)),
                )
                .exists()
            )
            stmt = (
                sa.update(StatusTable)
                .where(StatusTable.job_status == JobStatus.PENDING)
                .where(~active_job_exists)
                .values(job_status=JobStatus.ERROR)
                .returning(StatusTable.job_id)
            )
            failed = [row[0] for row in sesh.execute(stmt)]
            sesh.commit()
        return failed

    def get_jobs_report(self) -> JobsReport:
        """Get the jobs report.

        Useful for debugging or determining the size of the queue.

        Args:
            None.

        Returns:
            JobsReport: report of the jobs and their states.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("report.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                job_a = JobWithContext(job_id="a", function=nop, parameters={})
                queue.add_job(job_a, None)
                queue.add_job(
                    JobWithContext(
                        job_id="b", depends_on={"a"}, function=nop, parameters={}
                    ),
                    None,
                )
                report = queue.get_jobs_report()
                print(report.total, report.ready, report.pending)

            .. testoutput:: sql-queue

                2 1 1

        """
        with Session(self._engine) as sesh:
            return self._generate_jobs_report(sesh)

    @staticmethod
    def _generate_jobs_report(sesh: Session) -> JobsReport:
        """Create a report of the current jobs on the queue.

        Args:
            sesh: the current sqlalchemy session.

        Returns:
            JobsReport: the number of jobs in each status, and in total.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        """
        # calculate total separately to check for inconsistencies
        # if total is not the sum of our states, then we have something
        # deeply wrong in our queue! useful for debugging
        total_job_count = sa.select(
            sa.func.count(  # pylint: disable=not-callable
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
                sa.func.count(  # pylint: disable=not-callable
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
        """Update statuses of all the jobs in the queue.

        Propagates errors and successes down the dependency chain.

        Specifically, if a job status is ERROR, set its immediate dependents to
        ERROR; with each call, this will propagate down the dependency chain. And,
        once every job a PENDING job depends on is SUCCESS, set it to READY.

        Args:
            None.

        Returns:
            None.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        """
        with Session(self._engine) as sesh:
            # update jobs to failure if depend on failure
            failed_jobs = sa.select(StatusTable.job_id).where(
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
                .values(
                    job_status=JobStatus.ERROR,
                    details="A job this job depends on failed",
                )
            )

            sesh.execute(delete_jobs_from_queue_query)
            sesh.execute(job_statuses_that_depend_on_failed_job)

            # a PENDING job becomes READY only once *every* dependency is SUCCESS.
            # A dependency on an unknown job (NULL status) keeps the job pending.
            jobs_with_unfinished_dep = (
                sa.select(DependencyTable.job_id)
                .join(
                    StatusTable,
                    StatusTable.job_id == DependencyTable.depends_on,
                    isouter=True,
                )
                .where(
                    sa.or_(
                        StatusTable.job_status.is_(None),
                        StatusTable.job_status != JobStatus.SUCCESS,
                    ),
                )
            )
            promote_ready_jobs = (
                sa.update(StatusTable)
                .where(StatusTable.job_status == JobStatus.PENDING)
                .where(StatusTable.job_id.not_in(jobs_with_unfinished_dep))
                .values(job_status=JobStatus.READY)
            )
            sesh.execute(promote_ready_jobs)
            sesh.commit()

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

        Returns:
            None.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.common import JobStatus
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("update.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                job_a = JobWithContext(job_id="a", function=nop, parameters={})
                queue.add_job(job_a, None)
                queue.update_job_status("a", JobStatus.ERROR, "out of memory")
                report = queue.get_job_status("a")
                print(report.status.name, report.status_details)

            .. testoutput:: sql-queue

                ERROR out of memory

        """
        with Session(self._engine) as sesh:
            update_query = (
                sa.update(
                    StatusTable,
                )
                .where(StatusTable.job_id == job_id)
                .values(job_status=status, details=details)
            )
            sesh.execute(update_query)
            sesh.flush()
            sesh.commit()

        self._update_job_statuses()

    def get_job_status(self, job_id: str | uuid.UUID) -> JobStatusReport:
        """Get the current status of a job, and the details given with it.

        Args:
            job_id (str | uuid.UUID): job to look up

        Returns:
            JobStatusReport: the job's status and its details.

        Raises:
            KeyError: if there is no such job

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("status.db"))
                try:
                    queue.get_job_status("unknown")
                except KeyError:
                    print("no such job")

            .. testoutput:: sql-queue

                no such job

        """
        with Session(self._engine) as sesh:
            row = sesh.execute(
                sa.select(StatusTable.job_status, StatusTable.details).where(
                    StatusTable.job_id == str(job_id),
                ),
            ).first()
        if row is None:
            raise KeyError(job_id)
        return JobStatusReport(
            job_id=job_id,
            status=JobStatus(row[0]),
            status_details=row[1],
        )

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
                (for example, a job with the same id already exists)

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("add_job.db"))
                nop = "pyantz.jobs.testing.nop.do_nothing"
                parent = JobWithContext(job_id="parent", function=nop, parameters={})
                after = JobWithContext(
                    job_id="after", depends_on={"parent"}, function=nop, parameters={}
                )
                child = JobWithContext(job_id="child", function=nop, parameters={})
                print(queue.add_job(parent, None), queue.add_job(parent, None))
                queue.add_job(after, None)
                # "after" now waits for "child" too, as "parent" submitted it
                queue.add_job(child, parent_job_id="parent")

            .. testoutput:: sql-queue

                True False

        """
        # not required but polite to call whenever accessing
        self._update_job_statuses()

        try:
            self._insert_job(job_config, parent_job_id)
        except sqlalchemy.exc.IntegrityError:
            # the session is rolled back on exit, so the queue is unchanged
            logging.getLogger(__name__).error(  # noqa: TRY400
                "Cannot add job %s: a job with this id is already in the queue",
                job_config.job_id,
            )
            return False

        # not required but polite
        self._update_job_statuses()
        return True

    def _insert_job(
        self,
        job_config: JobWithContext,
        parent_job_id: str | uuid.UUID | None,
    ) -> None:
        """Insert all rows for a job in one transaction.

        Args:
            job_config: the job to insert, as PENDING.
            parent_job_id: the job which submitted it, whose dependents will wait
                for this job too; None for no parent.

        Returns:
            None.

        Raises:
            sqlalchemy.exc.IntegrityError: if the job id is already present

        """
        with Session(self._engine) as sesh:
            # first, chunk up the job
            jobs_json = job_config.model_dump_json()
            job_definition_chunks: Generator[str] = (
                "".join(chunk_as_tuple)
                for chunk_as_tuple in batched(jobs_json, CHUNKSIZE, strict=False)
            )

            # then, add it to the job config definition table
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
                # inherit deps!
                jobs_depending_on_parent = sa.select(
                    DependencyTable.job_id,
                    sa.literal(str(job_config.job_id), type_=sa.String).label(
                        "depends_on"
                    ),
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

        Returns:
            None.

        Raises:
            sqlalchemy.exc.OperationalError: if the database can't be used.

        Example:
            .. testcode:: sql-queue

                from pathlib import Path

                from pyantz.infrastructure.config import JobWithContext
                from pyantz.infrastructure.distributed_queue.common import JobStatus
                from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

                queue = SqliteQueue(Path("retry.db"))
                job = JobWithContext(
                    job_id="a",
                    function="pyantz.jobs.testing.nop.do_nothing",
                    parameters={},
                )
                queue.add_job(job, None)
                taken = queue.get_job().payload.job
                retry = taken.model_copy(update={"num_attempted_runs": 1})
                queue.change_config_in_place(retry)
                queue.update_job_status("a", JobStatus.PENDING)
                print(queue.get_job().payload.job.num_attempted_runs)

            .. testoutput:: sql-queue

                1

        """
        with Session(self._engine) as sesh:
            delete_query = sa.delete(JobConfigTable).where(
                JobConfigTable.job_id == job_config.job_id,
            )

            jobs_json = job_config.model_dump_json()
            job_definition_chunks: Generator[str] = (
                "".join(chunk_as_tuple)
                for chunk_as_tuple in batched(jobs_json, CHUNKSIZE, strict=False)
            )

            # then, add it to the job config definition table
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

            # a job that was already handed to a worker is no longer in the queue
            in_queue = sesh.execute(
                sa.select(JobQueue.q_index).where(JobQueue.job_id == job_config.job_id),
            ).first()
            if in_queue is None:
                sesh.add(JobQueue(job_id=job_config.job_id))
            sesh.commit()
