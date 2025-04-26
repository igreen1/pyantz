"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_active_jobs"""

from typing import Optional
from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct

class QosLimitsMaxActiveJobs(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_ACTIVE_JOBS"""
    accruing: Optional[Uint32NoValStruct]
    count: Optional[Uint32NoValStruct]
