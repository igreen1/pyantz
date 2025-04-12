"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_time_system"""

from typing import Optional

from pydantic import BaseModel


class StepTimeSystem(BaseModel):
    """v0.0.42 STEP_TIME_SYSTEM"""

    seconds: Optional[int]
    microseconds: Optional[int]
