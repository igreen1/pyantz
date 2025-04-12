"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_task"""

from typing import Optional

from pydantic import BaseModel


class StepTask(BaseModel):
    """v0.0.42 STEP_TASK"""

    distribution: Optional[str]
