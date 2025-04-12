"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_min"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class AssocMin(BaseModel):
    """v0.0.42 ASSOC_MIN"""

    priority_threshold: Optional[Uint32NoValStruct]
