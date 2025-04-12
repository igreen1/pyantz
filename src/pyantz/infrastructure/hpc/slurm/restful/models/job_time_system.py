"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_time_system"""

from typing import Optional

from pydantic import BaseModel


class JobTimeSystem(BaseModel):
    """v0.0.42 JOB_TIME_SYSTEM"""

    seconds: Optional[int]
    microseconds: Optional[int]
