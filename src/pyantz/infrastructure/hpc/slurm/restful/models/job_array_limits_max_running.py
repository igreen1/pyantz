"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_array_limits_max_running"""

from typing import Optional

from pydantic import BaseModel


class JobArrayLimitsMaxRunning(BaseModel):
    """v0.0.42 JOB_ARRAY_LIMITS_MAX_RUNNING"""

    tasks: Optional[int]
