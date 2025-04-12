"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_time"""

from typing import Optional

from pydantic import BaseModel

from .job_time_system import JobTimeSystem
from .job_time_total import JobTimeTotal
from .job_time_user import JobTimeUser
from .uint32_no_val_struct import Uint32NoValStruct
from .uint64_no_val_struct import Uint64NoValStruct


class JobTime(BaseModel):
    """0.0.42 JOB_TIME"""

    elapsed: Optional[int]
    eligible: Optional[int]
    end: Optional[int]
    planned: Optional[Uint64NoValStruct]
    start: Optional[int]
    submission: Optional[int]
    suspended: Optional[int]
    system: Optional[JobTimeSystem]
    limit: Optional[Uint32NoValStruct]
    total: Optional[JobTimeTotal]
    user: Optional[JobTimeUser]
