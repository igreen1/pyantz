"""Old (misspelled) name of :mod:`pyantz.infrastructure.config.abstract_job`.

Kept so that imports of the old name keep working.
"""

from __future__ import annotations

from .abstract_job import AbstractJobConfig, str_uuid4

__all__ = ["AbstractJobConfig", "str_uuid4"]
