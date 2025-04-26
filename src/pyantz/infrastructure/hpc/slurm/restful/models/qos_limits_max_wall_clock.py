"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_wall_clock"""

from typing import Optional
from pydantic import BaseModel

from .qos_limits_max_wall_clock_per import QosLimitsMaxWallClockPer

class QosLimitsMaxWallClock(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_WALL_CLOCK"""
    per: Optional[QosLimitsMaxWallClockPer]
