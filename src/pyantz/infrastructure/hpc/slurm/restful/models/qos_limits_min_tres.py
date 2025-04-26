"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_min_tres"""

from typing import Optional
from pydantic import BaseModel

from .qos_limits_min_tres_per import QosLimitsMinTresPer

class QosLimitsMinTres(BaseModel):
    """v0.0.42 QOS_LIMITS_MIN_TRES"""
    per: Optional[QosLimitsMinTresPer]
