"""Test the declared attributes of the queue match what it really has."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path


def _annotated_attributes() -> set[str]:
    """Names annotated on the class (without evaluating type-checking-only types)."""
    return set(
        # the module uses `from __future__ import annotations`, so these are the
        # unevaluated strings
        inspect.get_annotations(SqliteQueue),
    )


def test_annotations_match_slots() -> None:
    """Every annotated attribute is a slot, and vice versa."""
    assert _annotated_attributes() == set(SqliteQueue.__slots__)


def test_declared_attributes_exist(tmp_path: Path) -> None:
    """A queue really has the attributes the class declares."""
    queue = SqliteQueue(tmp_path / "queue.db")
    for name in _annotated_attributes():
        assert hasattr(queue, name)
