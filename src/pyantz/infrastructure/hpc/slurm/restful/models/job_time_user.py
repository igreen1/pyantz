"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_time_user"""

from typing import Optional

from pydantic import BaseModel


class JobTimeUser(BaseModel):
    """v0.0.42 JOB_TIME_USER"""

    seconds: Optional[int]
    microseconds: Optional[int]
