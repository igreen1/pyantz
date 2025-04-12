"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_time_total"""

from typing import Optional

from pydantic import BaseModel


class JobTimeTotal(BaseModel):
    """v0.0.42 JOB_TIME_TOTAL"""

    seconds: Optional[int]
    microseconds: Optional[int]
