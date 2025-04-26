"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_tres_minutes"""


from typing import Optional
from pydantic import BaseModel

from .tres import Tres
from .qos_limits_max_tres_minutes_per import QosLimitsMaxTresMinutesPer

class QosLimitsMaxTresMinutes(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_TRES_MINUTES"""

    total: Optional[list[Tres]]
    per: Optional[QosLimitsMaxTresMinutesPer]
