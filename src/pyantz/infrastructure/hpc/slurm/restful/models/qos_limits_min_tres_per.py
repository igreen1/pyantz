"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_limits_min_tres_per"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres


class QosLimitsMinTresPer(BaseModel):
    """v0.0.42 QOS_LIMITS_MIN_TRES_PER"""

    job: Optional[list[Tres]]
