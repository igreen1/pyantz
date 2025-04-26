"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_wall_clock_per"""

from typing import Optional
from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct

class QosLimitsMaxWallClockPer(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_WALL_CLOCK_PER"""

    qos: Optional[Uint32NoValStruct]
    job: Optional[Uint32NoValStruct]
