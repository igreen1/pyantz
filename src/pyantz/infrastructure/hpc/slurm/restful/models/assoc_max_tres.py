"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_tres"""

from typing import Optional

from pydantic import BaseModel

from .assoc_max_tres_group import AssocMaxTresGroup
from .assoc_max_tres_minutes import AssocMaxTresMinutes
from .assoc_max_tres_per import AssocMaxTresPer
from .tres import Tres


class AssocMaxTres(BaseModel):
    """0.0.42 ASSOC_MAX_TRES"""

    total: Optional[list[Tres]]
    group: Optional[AssocMaxTresGroup]
    minutes: Optional[AssocMaxTresMinutes]
    per: Optional[AssocMaxTresPer]
