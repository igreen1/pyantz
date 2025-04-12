"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_time_total"""

from typing import Optional

from pydantic import BaseModel


class StepTimeTotal(BaseModel):
    """v0.0.42 STEP_TIME_TOTAL"""

    seconds: Optional[int]
    microseconds: Optional[int]
