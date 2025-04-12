"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_tasks"""

from typing import Optional

from pydantic import BaseModel


class StepTasks(BaseModel):
    """v0.0.42 STEP_TASKS"""

    count: Optional[int]
