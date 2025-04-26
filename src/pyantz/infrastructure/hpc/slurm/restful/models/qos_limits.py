"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits"""

from typing import Optional
from pydantic import BaseModel, Field

from .qos_limits_max import QosLimitsMax
from .float64_no_val_struct import Float64NoValStruct
from .qos_limits_min import QosLimitsMin

class QosLimits(BaseModel):
    """v0.0.42 QOS_LIMITS"""

    grace_time: Optional[int]
    max_: Optional[QosLimitsMax] = Field(alias="max")
    factor: Optional[Float64NoValStruct]
    min: Optional[QosLimitsMin]
