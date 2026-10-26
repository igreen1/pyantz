"""Distributed queue that supports multiple processes accessing it simultaneously.

This version relies on sqlite (mostly sqlite).
"""

from __future__ import annotations

from .sql_queue import SqliteQueue

__all__ = ["SqliteQueue"]
