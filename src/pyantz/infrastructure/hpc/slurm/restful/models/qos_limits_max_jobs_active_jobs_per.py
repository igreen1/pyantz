"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_jobs_active_jobs_per"""

from typing import Optional
from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct

class QosLimitsMaxJobsActiveJobsPer(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_jOBS_ACTIVE_JOBS_PER"""
    accounts: Optional[Uint32NoValStruct]
    user: Optional[Uint32NoValStruct]
