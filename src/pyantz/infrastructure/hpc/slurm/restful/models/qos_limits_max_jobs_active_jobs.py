"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_jobs_active_jobs"""

from typing import Optional
from pydantic import BaseModel

from .qos_limits_max_jobs_active_jobs_per import QosLimitsMaxJobsActiveJobsPer

class QosLimitsMaxJobsActiveJobs(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_JOBS_ACTIVE_JOBS"""
    per: Optional[QosLimitsMaxJobsActiveJobsPer]