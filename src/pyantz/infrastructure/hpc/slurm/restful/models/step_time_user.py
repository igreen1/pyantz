"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_time_user"""

from typing import Optional

from pydantic import BaseModel


class StepTimeUser(BaseModel):
    """v0.0.42 STEP_TIME_USER"""

    seconds: Optional[int]
    microseconds: Optional[int]
