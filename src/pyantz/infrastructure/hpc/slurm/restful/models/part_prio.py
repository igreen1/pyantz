"""https://slurm.schedmd.com/rest_api.html#v0.0.42_part_prio"""

from typing import Optional

from pydantic import BaseModel


class PartPrio(BaseModel):
    """v0.0.42 PART_PRIO"""

    partition: Optional[str]
    priority: Optional[int]
