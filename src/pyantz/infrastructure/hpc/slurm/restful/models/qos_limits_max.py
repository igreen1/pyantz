"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max"""

from typing import Optional
from pydantic import BaseModel

from .qos_limits_max_active_jobs import QosLimitsMaxActiveJobs
from .qos_limits_max_jobs import QosLimitsMaxJobs
from .qos_limits_max_tres import QosLimitsMaxTres
from .qos_limits_max_wall_clock import QosLimitsMaxWallClock
from .qos_limits_max_jobs_active_jobs import QosLimitsMaxJobsActiveJobs

class QosLimitsMax(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX"""
    active_jobs: Optional[QosLimitsMaxActiveJobs]
    jobs: Optional[QosLimitsMaxJobs]
    tres: Optional[QosLimitsMaxTres]
    wall_clock: Optional[QosLimitsMaxWallClock]
    accruing: Optional[QosLimitsMaxJobsActiveJobs]
