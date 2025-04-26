"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_tres"""

from typing import Optional
from pydantic import BaseModel

from .tres import Tres
from .qos_limits_max_tres_minutes import QosLimitsMaxTresMinutes
from .qos_limits_max_tres_per import QosLimitsMaxTresPer

class QosLimitsMaxTres(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_TRES"""
    total: Optional[list[Tres]]
    minutes: Optional[QosLimitsMaxTresMinutes]
    per: Optional[QosLimitsMaxTresPer]
