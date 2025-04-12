"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_tres_per"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres


class AssocMaxTresPer(BaseModel):
    """v0.0.42 ASSOC_MAX_TRES_PER"""

    job: Optional[list[Tres]]
    node: Optional[list[Tres]]
