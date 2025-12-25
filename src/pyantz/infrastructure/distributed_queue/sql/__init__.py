"""Distributed queue that supports multiple processes accessing it simultaneously.

This version relies on sqlite (mostly sqlite).
"""

from .sql_queue import SqliteQueue

__all__ = ["SqliteQueue"]
