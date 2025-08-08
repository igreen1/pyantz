"""Primary API for a distributed queue."""

import contextlib
import json
import os
import queue
import sqlite3
from collections.abc import Generator

import sqlalchemy as sa
import sqlalchemy.exc
from pydantic import JsonValue
from sqlalchemy.orm import Session

from pyantz.infrastructure.core.status import Status

from .queue_orm import (
    CHUNKSIZE,
    Base,
    DependencyTable,
    JobConfigTable,
    JobQueue,
    StatusTable,
)


class SqliteQueue:
    """The wrapper for the queue in sqlite."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        """Create a queue based on a sqlite backend."""
        self._path = path
        self._engine = sa.create_engine(f"""sqlite:///{self._path}""")
        with contextlib.suppress(sqlite3.OperationalError, sqlalchemy.exc.OperationalError):
            Base.metadata.create_all(self._engine)

    def put(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        json_like: str | JsonValue,
        job_id: str,
        priority: int = -1,
        depends_on: list[str] | None = None,
        max_attempts: int = 10,
    ) -> bool:
        """Put the item provided into the queue.

        Args:
            json_like (str): configuration (jsonlike object) to place on the queue
            job_id (str): unique id of the job being added to the queue
            priority (int, optional): priority where bigger number means more important.
                Defaults to -1.
            depends_on (list[str] | None, optional):
                if provided, won't execute until these jobs are complete. Defaults to None.
            max_attempts (int): max times to try to put this value into the queue

        Raises:
            ValueError: if the item provided is not a valid json-like string

        """
        for _ in range(max_attempts):
            with contextlib.suppress(sqlite3.OperationalError, sqlalchemy.exc.OperationalError):
                return self._put(
                    json_like=json_like,
                    job_id=job_id,
                    priority=priority,
                    depends_on=depends_on,
                )
        return False

    def _put(
        self,
        json_like: str | JsonValue,
        job_id: str,
        priority: int = -1,
        depends_on: list[str] | None = None,
    ) -> bool:
        """Put the item provided into the queue.

        Args:
            json_like (str): configuration (jsonlike object) to place on the queue
            job_id (str): unique id of the job being added to the queue
            priority (int, optional): priority where bigger number means more important.
                Defaults to -1.
            depends_on (list[str] | None, optional):
                if provided, won't execute until these jobs are complete. Defaults to None.

        Raises:
            ValueError: if the item provided is not a valid json-like string

        """
        if not isinstance(json_like, str):
            json_like = json.dumps(json_like)

        # assert that json_like is a valid json object
        try:
            json.loads(json_like)
        except ValueError as exc:
            msg = f"Queue only accepts json-like strings, got: {json_like}"
            raise ValueError(msg) from exc

        def chunks() -> Generator[str, None, None]:
            for i in range(0, len(json_like), CHUNKSIZE):
                yield json_like[i : i + CHUNKSIZE]

        with Session(self._engine) as sesh:
            job_queue = JobQueue(job_id=job_id, priority=priority)
            sesh.add(job_queue)

            job_configs = [
                JobConfigTable(job_id=job_id, job_subindex=i, job_config_content=chunk)
                for i, chunk in enumerate(chunks())
            ]
            sesh.add_all(job_configs)

            job_status = StatusTable(job_id=job_id, job_status=Status.READY)
            sesh.add(job_status)

            if depends_on is not None:
                job_dependencies = [
                    DependencyTable(job_id=job_id, depends_on=dependency_id)
                    for dependency_id in depends_on
                ]
                sesh.add_all(job_dependencies)

            sesh.commit()
        return True

    def set_status(self, job_id: str, status: int) -> bool:
        """Set the status of the job_id to the provided status."""
        with Session(self._engine) as sesh:
            stmt = sa.select(StatusTable).where(StatusTable.job_id == job_id)
            job_orm = sesh.scalars(stmt).one()
            job_orm.job_status = status
            sesh.commit()
        return True

    def qsize(self) -> int:
        """Return the current size of the queue.

        Returns:
            int: size of the queue

        """
        # looking at the size of the queue triggers the removal job
        self.remove_dead_jobs()

        with self._engine.connect() as conn:
            return next(  # type: ignore[no-any-return]
                row[0]
                for row in conn.execute(
                    sa.select(
                        sa.func.count(JobQueue.job_id)  # pylint: disable=not-callable
                    )
                )
            )

    def remove_dead_jobs(self) -> None:
        """Dead jobs are jobs that depend on a failed job. They must be pruned from the list."""
        with Session(self._engine) as sesh:
            failed_jobs = sa.select(StatusTable.job_id).where(
                StatusTable.job_status == Status.ERROR
            )

            # remove jobs that depend on a failure
            # jobs that depend on failed jobs should have their status set to failed
            # this allows for the dependency tree to slowly resolve to completely failed
            jobs_that_depend_on_failed_job = sa.select(DependencyTable.job_id).where(
                DependencyTable.depends_on.in_(failed_jobs)
            )

            delete_jobs_from_queue_query = sa.delete(JobQueue).where(
                JobQueue.job_id.in_(jobs_that_depend_on_failed_job)
            )

            job_statuses_that_depend_on_failed_job = (
                sa.update(StatusTable)
                .where(StatusTable.job_id.in_(jobs_that_depend_on_failed_job))
                .values(job_status=Status.ERROR)
            )

            sesh.execute(delete_jobs_from_queue_query)
            sesh.execute(job_statuses_that_depend_on_failed_job)
            sesh.commit()

    def get(self) -> str:
        """If any jobs available, returns them. Else throw queue.Empty exception."""
        # first, prune the job queue
        # doing this often ensures our state is always good to go
        self.remove_dead_jobs()

        with Session(self._engine) as sesh:
            # get a list of jobs not completed
            not_ready_jobs = (
                sa.select(DependencyTable.job_id)
                .join(
                    StatusTable,
                    onclause=DependencyTable.depends_on == StatusTable.job_id,
                )
                .where(
                    sa.not_(
                        StatusTable.job_status.in_({Status.FINAL, Status.SUCCESS, Status.ERROR})
                    )
                )
            )

            # get the top of the queue
            stmt = (
                sa.delete(JobQueue)
                .where(
                    JobQueue.q_index.in_(
                        sa.select(JobQueue.q_index)
                        .where(
                            # don't include jobs with dependencies not completed
                            sa.not_(JobQueue.job_id.in_(not_ready_jobs))
                        )
                        .order_by(
                            # queues are obviously ordered!
                            JobQueue.priority,
                            JobQueue.q_index,
                        )
                        .limit(1)
                    )
                )
                .returning(JobQueue)
            )
            result = sesh.execute(stmt).fetchone()
            sesh.flush()
            if result is None:
                raise queue.Empty
            job_id = result[0].job_id

            # get the corresponding contents of that job
            contents_query = (
                sa.select(JobConfigTable.job_config_content)
                .where(JobConfigTable.job_id == job_id)
                .order_by(JobConfigTable.job_subindex)
            )
            contents_query_result = sesh.execute(contents_query)
            if contents_query_result is None:  # pyright: ignore[reportUnnecessaryComparison]
                raise queue.Empty
            content_chunks = [row[0] for row in contents_query_result if row is not None]  # pyright: ignore[reportUnnecessaryComparison]
            if len(content_chunks) == 0:
                raise queue.Empty
            contents = "".join(content_chunks)

            # not really required but for housekeeping, commit our transaction
            sesh.commit()
        return contents
