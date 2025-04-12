"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_jobs"""

from typing import Optional

from pydantic import BaseModel

from .assoc_max_jobs_per import AssocMaxJobsPer
from .uint32_no_val_struct import Uint32NoValStruct


class AssocMaxJobs(BaseModel):
    """v0.0.42 ASSOC_MAX_JOBS"""

    per: Optional[AssocMaxJobsPer]
    active: Optional[Uint32NoValStruct]
    accruing: Optional[Uint32NoValStruct]
    total: Optional[Uint32NoValStruct]
