"""https://slurm.schedmd.com/rest_api.html#v0.0.42_qos"""

from typing import Optional
from pydantic import BaseModel

from .qos_limits import QosLimits
from .qos_preempt import QosPreempt
from .uint32_no_val_struct import Uint32NoValStruct
from .float64_no_val_struct import Float64NoValStruct

class Qos(BaseModel):
    """v0.0.42 QOS"""

    description: Optional[str]
    flags: Optional[list[str]]
    id: Optional[int]
    limits: Optional[QosLimits]
    name: Optional[str]
    preempt: Optional[QosPreempt]
    priority: Optional[Uint32NoValStruct]
    usage_factor: Optional[Float64NoValStruct]
    usage_threshold: Optional[Float64NoValStruct]
