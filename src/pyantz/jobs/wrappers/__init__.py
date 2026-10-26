"""Jobs which wrap other PyAntz jobs."""

from __future__ import annotations

from . import local, loops, submit, variables

__all__ = [
    "local",
    "loops",
    "submit",
    "variables",
]
