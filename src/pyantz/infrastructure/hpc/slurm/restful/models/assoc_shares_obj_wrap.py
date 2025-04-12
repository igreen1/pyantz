"""https://slurm.schedmd.com/rest_api.html#v0.0.42_assoc_shares_obj_wrap"""

from typing import Optional

from pydantic import BaseModel

from .assoc_shares_obj_wrap_fairshare import AssocSharesObjWrapFairshare
from .assoc_shares_obj_wrap_tres import AssocSharesObjWrapTres
from .float64_no_val_struct import Float64NoValStruct
from .uint32_no_val_struct import Uint32NoValStruct


class AssocSharesObjWrap(BaseModel):
    """0.0.42 ASSOC_SHARES_OBJ_WRAP"""

    id: Optional[int]
    cluster: Optional[str]
    name: Optional[str]
    parent: Optional[str]
    partition: Optional[str]
    shares_normalized: Optional[Float64NoValStruct]
    shares: Optional[Uint32NoValStruct]
    tres: Optional[AssocSharesObjWrapTres]
    effective_usage: Optional[Float64NoValStruct]
    usage_normalized: Optional[Float64NoValStruct]
    usage: Optional[int]
    fairshare: Optional[AssocSharesObjWrapFairshare]
    type: Optional[list[str]]
