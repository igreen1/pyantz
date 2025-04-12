"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_jobs_per"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class AssocMaxJobsPer(BaseModel):
    """v0.0.42 ASSOC_MAX_JOBS_PER"""

    count: Optional[Uint32NoValStruct]
    accruing: Optional[Uint32NoValStruct]
    submitted: Optional[Uint32NoValStruct]
    wall_clock: Optional[Uint32NoValStruct]
