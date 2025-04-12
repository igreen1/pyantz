"""https://slurm.schedmd.com/rest_api.html#v0.0.42_uint64_no_val_struct"""

from typing import Optional

from pydantic import BaseModel


class Uint64NoValStruct(BaseModel):
    """0.0.42 UINT64_NO_VAL_STRUCT"""

    set: Optional[bool]
    infinite: Optional[bool]
    number: Optional[int]
