"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_array"""

from typing import Optional

from pydantic import BaseModel

from .job_array_limits import JobArrayLimits
from .uint32_no_val_struct import Uint32NoValStruct


class JobArray(BaseModel):
    """v0.0.42 JOB_ARRAY"""

    job_id: Optional[int]
    limits: Optional[JobArrayLimits]
    task_id: Optional[Uint32NoValStruct]
    task: Optional[str]
