"""https://slurm.schedmd.com/rest_api.html#v0_0_42_instance_time"""

from typing import Optional

from pydantic import BaseModel


class InstanceTime(BaseModel):
    """0.0.42 INSTANCE_TIME"""

    time_end: Optional[int]
    time_start: Optional[int]
