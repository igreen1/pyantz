"""https://slurm.schedmd.com/rest_api.html#v0_0_42_qos_preempt"""

from typing import Optional
from pydantic import BaseModel, Field
from .uint32_no_val_struct import Uint32NoValStruct

class QosPreempt(BaseModel):
    """v0.0.42 QOS_PREEMPT"""

    list_: Optional[list[str]] = Field(..., alias="list")
    mode: Optional[list[str]]
    exempt_time: Optional[Uint32NoValStruct]
