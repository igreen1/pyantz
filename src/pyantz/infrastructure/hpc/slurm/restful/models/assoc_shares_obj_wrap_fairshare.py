"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_shares_obj_wrap_fairshare"""

from typing import Optional

from pydantic import BaseModel

from .float64_no_val_struct import Float64NoValStruct


class AssocSharesObjWrapFairshare(BaseModel):
    """v0.0.42 ASSOC_SHARES_OBJ_WRAP_FAIRSHARE"""

    factor: Optional[Float64NoValStruct]
    level: Optional[Float64NoValStruct]
