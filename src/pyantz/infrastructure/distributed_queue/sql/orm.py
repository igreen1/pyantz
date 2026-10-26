"""SQLAlchemy ORM models for the pyantz SQLite job queue.

The queue is backed by four tables:

* **job_queue** — ordered list of job IDs waiting to be dequeued.
* **queue_items** — chunked JSON representations of each job config.
* **dependencies** — directed edges of the job dependency graph.
* **job_status** — current lifecycle state of every known job.

Large job configs are split into ``CHUNKSIZE``-character chunks so that
SQLite's per-column string limit is not exceeded.
"""

from __future__ import annotations

from typing import Final

from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CHUNKSIZE: Final[int] = 2000
"""Number of characters of a job's config stored per row; multiple rows might
make up one job."""

# pylint: disable=too-few-public-methods


class Base(DeclarativeBase):
    """The base class for our ORM."""


class JobQueue(Base):
    """Actual queue, holds jobs as they're added."""

    __tablename__: str = "job_queue"

    q_index: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    """Position in the queue; jobs are dequeued in increasing order."""

    job_id: Mapped[str] = mapped_column(index=True)  # uuid of the job
    """Id of the queued job."""


class JobConfigTable(Base):
    """The job config table holds the configurations for the jobs in the queue.

    Note that a job may span multiple tuples (rows) if the config is very large.
    In that case, it will have multiple sub-indices.
    """

    __tablename__: str = "queue_items"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    """Id of the job."""

    job_subindex: Mapped[int] = mapped_column(primary_key=True)
    """Position of this chunk in the job's config."""

    job_config_content: Mapped[str] = mapped_column(String(CHUNKSIZE))
    """A chunk of the job's config, as JSON, of at most :data:`CHUNKSIZE`
    characters."""


class DependencyTable(Base):
    """The dependency table holds the dependency graph of the jobs."""

    __tablename__: str = "dependencies"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    """Id of the job which waits."""

    # indexed to find the dependents of a job without scanning the whole table
    depends_on: Mapped[str] = mapped_column(primary_key=True, index=True)
    """Id of the job it waits for."""


class StatusTable(Base):
    """The status table holds the current status of each job."""

    __tablename__: str = "job_status"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    """Id of the job."""

    # indexed because statuses are polled constantly
    job_status: Mapped[int] = mapped_column(index=True)
    """The job's :class:`~pyantz.infrastructure.distributed_queue.common.JobStatus`."""

    worker_id: Mapped[int | None] = mapped_column(default=None)
    """The worker (its process id) which is running the job, while it is
    RUNNING."""

    details: Mapped[str | None] = mapped_column(Text, default=None)
    """Why the job is in this status, for example the error message for
    failures."""


# pylint: enable=too-few-public-methods
