"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_CPU_requested_frequency"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class StepCpuRequestedFrequency(BaseModel):
    """v0.0.42 STEP_CPU_REQUESTED_FREQUENCY"""

    min: Optional[Uint32NoValStruct]
    max: Optional[Uint32NoValStruct]
