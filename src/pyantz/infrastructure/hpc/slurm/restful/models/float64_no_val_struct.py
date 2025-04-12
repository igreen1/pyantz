"""https://slurm.schedmd.com/rest_api.html#v0.0.42_float64_no_val_struct"""

from typing import Optional

from pydantic import BaseModel


class Float64NoValStruct(BaseModel):
    """0.0.42 FLOAT64_NO_VAL_STRUCT"""

    set: Optional[bool]
    infinite: Optional[bool]
    number: Optional[float]
