"""Test errors creating the queue tables are not hidden."""

import os
import sqlite3
from typing import TYPE_CHECKING

import pytest
import sqlalchemy.exc

from pyantz.infrastructure.distributed_queue.sql import SqliteQueue, sql_queue

if TYPE_CHECKING:
    from pathlib import Path


def test_missing_directory_raises_immediately(tmp_path: Path) -> None:
    """A queue file in a directory that doesn't exist fails when opened."""
    with pytest.raises(sqlalchemy.exc.OperationalError, match="unable to open"):
        SqliteQueue(tmp_path / "no_such_dir" / "queue.db")


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can write to read-only directories",
)
def test_unwritable_directory_raises_immediately(tmp_path: Path) -> None:
    """A queue file in a read-only directory fails when opened."""
    read_only = tmp_path / "ro"
    read_only.mkdir()
    read_only.chmod(0o500)
    try:
        with pytest.raises(sqlalchemy.exc.OperationalError):
            SqliteQueue(read_only / "queue.db")
    finally:
        read_only.chmod(0o700)


def test_concurrent_table_creation_is_tolerated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing the race to create the tables to another process is fine."""

    def _lost_race(*_args: object, **_kwargs: object) -> None:
        msg = "table job_queue already exists"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(sql_queue.Base.metadata, "create_all", _lost_race)

    SqliteQueue(tmp_path / "queue.db")  # does not raise


def test_other_operational_errors_propagate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors other than 'already exists' are not swallowed."""

    def _disk_full(*_args: object, **_kwargs: object) -> None:
        msg = "database or disk is full"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(sql_queue.Base.metadata, "create_all", _disk_full)

    with pytest.raises(sqlite3.OperationalError, match="disk is full"):
        SqliteQueue(tmp_path / "queue.db")
