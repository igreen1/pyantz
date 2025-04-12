"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_per_account"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class AssocMaxPerAccount(BaseModel):
    """v0.0.42 ASSOC_MAX_PER_ACCOUNT"""

    wall_clock: Optional[Uint32NoValStruct]
