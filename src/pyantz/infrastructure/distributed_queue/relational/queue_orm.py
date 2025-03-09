"""
The object relational mapping of the queue in the RDBMS
"""

from typing import Final

from sqlalchemy import String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

CHUNKSIZE: Final[int] = 2000


class Base(DeclarativeBase): ...


class JobQueue(Base):
    __tablename__: str = "queue"

    q_index: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str]  # the uuid
    priority: Mapped[int]


class JobConfigTable(Base):
    __tablename__: str = "queue_items"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    job_subindex: Mapped[int] = mapped_column(primary_key=True)
    job_config_content: Mapped[str] = mapped_column(String(CHUNKSIZE))


class DependencyTable(Base):
    __tablename__: str = "dependencies"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    depends_on: Mapped[str] = mapped_column(primary_key=True)


class StatusTable(Base):
    __tablename__: str = "job_status"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    job_status: Mapped[int]
