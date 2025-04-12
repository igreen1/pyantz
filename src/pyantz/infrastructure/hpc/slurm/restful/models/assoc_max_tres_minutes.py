"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_tres_minutes"""

from typing import Optional

from pydantic import BaseModel

from .qos_limits_min_tres_per import QosLimitsMinTresPer
from .tres import Tres


class AssocMaxTresMinutes(BaseModel):
    """0.0.42 ASSOC_MAX_TRES_MINUTES"""

    total: Optional[list[Tres]]
    per: Optional[QosLimitsMinTresPer]
