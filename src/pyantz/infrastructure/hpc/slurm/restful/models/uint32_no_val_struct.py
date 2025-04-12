"""https://slurm.schedmd.com/rest_api.html#v0.0.42_uint32_no_val_struct"""

from typing import Optional

from pydantic import BaseModel


class Uint32NoValStruct(BaseModel):
    """v0.0.42 UINT32_NO_VAL_STRUCT"""

    set: Optional[bool] = None
    infinite: Optional[bool] = None
    number: Optional[int] = None
