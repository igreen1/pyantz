"""https://slurm.schedmd.com/rest_api.html#v0.0.42_uint16_no_val_struct"""

from typing import Optional

from pydantic import BaseModel


class Uint16NoValStruct(BaseModel):
    """v0.0.42 UINT16_NO_VAL_STRUCT"""

    set: Optional[bool]
    infinite: Optional[bool]
    number: Optional[int]
