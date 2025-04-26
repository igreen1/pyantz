"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_min"""

from typing import Optional
from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct
from .qos_limits_min_tres import QosLimitsMinTres

class QosLimitsMin(BaseModel):
    """v0.0.42 QOS_LIMITS_MIN"""
    priority_threshold: Optional[Uint32NoValStruct]
    tres: Optional[QosLimitsMinTres]
