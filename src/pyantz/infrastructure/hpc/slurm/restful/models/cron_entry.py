"""https://slurm.schedmd.com/rest_api.html#v0.0.42_cron_entry"""

from typing import Optional

from pydantic import BaseModel

from .cron_entry_line import CronEntryLine


class CronEntry(BaseModel):
    """v0.0.42 CRON_ENTRY"""

    flags: Optional[list[str]]
    minute: Optional[str]
    hour: Optional[str]
    day_of_month: Optional[str]
    month: Optional[str]
    day_of_week: Optional[str]
    specification: Optional[str]
    command: Optional[str]
    line: Optional[CronEntryLine]
