"""https://slurm.schedmd.com/rest_api.html#v0.0.42_shares_uint64_tres"""

from typing import Optional

from pydantic import BaseModel

from .uint64_no_val_struct import Uint64NoValStruct


class SharesUint64Tres(BaseModel):
    """0.0.42 SHARES_UINT64_TRES"""

    name: Optional[str]
    value: Optional[Uint64NoValStruct]
