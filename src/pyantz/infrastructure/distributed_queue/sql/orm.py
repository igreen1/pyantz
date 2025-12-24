"""Object relational mapping for the queue database."""

from typing import Final

from sqlalchemy import String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

# our jobs are chunked when stored
# number of characters to store per a row
# multiple rows might make up one job
CHUNKSIZE: Final[int] = 2000

# pylint: disable=too-few-public-methods


class Base(DeclarativeBase):
    """The base class for our ORM."""


class JobQueue(Base):
    """Actual queue, holds jobs as they're added."""

    __tablename__: str = "job_queue"

    q_index: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str]  # uuid of the job


class JobConfigTable(Base):
    """The job config table holds the configurations for the jobs in the queue.

    Note that a job may span multiple tuples (rows) if the config is very large.
    In that case, it will have mutliple sub-indices.
    """

    __tablename__: str = "queue_items"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    job_subindex: Mapped[int] = mapped_column(primary_key=True)
    job_config_content: Mapped[str] = mapped_column(String(CHUNKSIZE))


class DependencyTable(Base):
    """The dependency table holds the dependency graph of the jobs."""

    __tablename__: str = "dependencies"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    depends_on: Mapped[str] = mapped_column(primary_key=True)


class StatusTable(Base):
    """The status table holds the current status of each job."""

    __tablename__: str = "job_status"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    job_status: Mapped[int]


# pylint: enable=too-few-public-methods
