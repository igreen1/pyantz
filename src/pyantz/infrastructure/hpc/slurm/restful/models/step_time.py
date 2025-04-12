"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_time"""

from typing import Optional

from pydantic import BaseModel

from .step_time_system import StepTimeSystem
from .step_time_total import StepTimeTotal
from .step_time_user import StepTimeUser
from .uint64_no_val_struct import Uint64NoValStruct


class StepTime(BaseModel):
    """v0.0.42 STEP_TIME"""

    elapsed: Optional[int]
    end: Optional[Uint64NoValStruct]
    start: Optional[Uint64NoValStruct]
    suspend: Optional[int]
    system: Optional[StepTimeSystem]
    total: Optional[StepTimeTotal]
    user: Optional[StepTimeUser]
