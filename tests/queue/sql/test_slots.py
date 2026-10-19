"""Test the declared attributes of the queue match what it really has."""

from typing import TYPE_CHECKING

from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def test_annotations_match_slots() -> None:
    """Every annotated attribute is a slot, and vice versa."""
    assert set(SqliteQueue.__annotations__) == set(SqliteQueue.__slots__)


def test_declared_attributes_exist(tmp_path: Path) -> None:
    """A queue really has the attributes the class declares."""
    queue = SqliteQueue(tmp_path / "queue.db")
    for name in SqliteQueue.__annotations__:
        assert hasattr(queue, name)
