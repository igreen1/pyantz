"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_tres_group"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres


class AssocMaxTresGroup(BaseModel):
    """0.0.42 ASSOC_MAX_TRES_GROUP"""

    minutes: Optional[Tres]
    active: Optional[Tres]
