"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_max_tres_per"""

from typing import Optional
from pydantic import BaseModel

from .tres import Tres

class QosLimitsMaxTresPer(BaseModel):
    """v0.0.42 QOS_LIMITS_MAX_TRES_PER"""
    account: Optional[list[Tres]]
    job: Optional[list[Tres]]
    node: Optional[list[Tres]]
    user: Optional[list[Tres]]
