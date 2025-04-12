"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_array_limits"""

from typing import Optional

from pydantic import BaseModel

from .job_array_limits_max import JobArrayLimitsMax


class JobArrayLimits(BaseModel):
    """v0.0.42 JOB_ARRAY_LIMITS"""

    max: Optional[JobArrayLimitsMax]
