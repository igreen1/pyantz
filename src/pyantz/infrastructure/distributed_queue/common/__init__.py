"""Common types across queue implementations."""

from __future__ import annotations

from .interface import QueueInterface
from .return_types import (
    CompleteReturn,
    GetJobReturn,
    JobReturn,
    JobsReport,
    JobStatus,
    JobStatusReport,
    PendingReturn,
)

__all__ = [
    "CompleteReturn",
    "GetJobReturn",
    "JobReturn",
    "JobStatus",
    "JobStatusReport",
    "JobsReport",
    "PendingReturn",
    "QueueInterface",
]
