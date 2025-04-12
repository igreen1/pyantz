"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_shares_obj_wrap_tres"""

from typing import Optional

from pydantic import BaseModel

from .shares_float128_tres import SharesFloat128Tres
from .shares_uint64_tres import SharesUint64Tres


class AssocSharesObjWrapTres(BaseModel):
    """0.0.42 ASSOC_SHARES_OBJ_WRAP_TRES"""

    run_seconds: Optional[list[SharesUint64Tres]]
    group_minutes: Optional[list[SharesUint64Tres]]
    usage: Optional[SharesFloat128Tres]
