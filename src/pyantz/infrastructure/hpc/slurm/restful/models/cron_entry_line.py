"""https://slurm.schedmd.com/rest_api.html#v0_0_42_cron_entry_line"""

from typing import Optional

from pydantic import BaseModel


class CronEntryLine(BaseModel):
    """v0.0.42 CRON_ENTRY_LINE"""

    start: Optional[int]
    end: Optional[int]
