"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max"""

from typing import Optional
from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct
from .qos_limits_max_jobs_active_jobs import QosLimitsMaxJobsActiveJobs
from .qos_limits_max_jobs_active_jobs_per import QosLimitsMaxJobsActiveJobsPer

class QosLimitsMaxJobs(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_JOBS"""
    count: Optional[Uint32NoValStruct]
    active_jobs: Optional[QosLimitsMaxJobsActiveJobs]
    per: Optional[QosLimitsMaxJobsActiveJobsPer]
